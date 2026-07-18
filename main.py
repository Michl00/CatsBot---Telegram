import asyncio
import json
import logging
import os
import time
from random import randint

import requests
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import BOT_TOKEN

LOG_FILE = os.path.join(os.path.dirname(__file__), 'bot.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='[{asctime}] #{levelname:8} {filename}:{lineno} - {name} - {message}',
    style='{',
    filename=LOG_FILE,
    filemode='w'
)
logger = logging.getLogger(__name__)

API_URL = [
    'https://cataas.com/cat/small?json=true',
    'https://cataas.com/cat/kitten?json=true',
    'https://cataas.com/cat/little?json=true'
]
ERROR_TEXT = "Извини, не удалось получить котенка."

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
users = {}
STORAGE_FILE = os.path.join(os.path.dirname(__file__), "users.json")


class Form(StatesGroup):
    waiting_for_hours = State()


def save_users():
    serializable_users = {str(chat_id): data for chat_id, data in users.items()}
    with open(STORAGE_FILE, "w", encoding="utf-8") as file:
        json.dump(serializable_users, file, ensure_ascii=False, indent=2)


def load_users():
    if not os.path.exists(STORAGE_FILE):
        return {}
    with open(STORAGE_FILE, "r", encoding="utf-8") as file:
        raw_users = json.load(file)
    return {int(chat_id): data for chat_id, data in raw_users.items()}


async def send_cat_to_chat(chat_id: int):
    response = requests.get(API_URL[randint(0, len(API_URL) - 1)])
    logging.debug("Received cat image URL")
    if response.status_code == 200:
        await bot.send_photo(chat_id=chat_id, photo=response.json()['url'], caption="Вот твой котенок! 😽😽")
    else:
        await bot.send_message(chat_id=chat_id, text=ERROR_TEXT)


async def subscribe_user(chat_id: int, interval_seconds: int, message: Message):
    if chat_id not in users:
        users[chat_id] = {'subscribed': False, 'interval': None, 'last_sent': None}

    users[chat_id]['subscribed'] = True
    users[chat_id]['interval'] = interval_seconds
    users[chat_id]['last_sent'] = time.time()
    save_users()

    try:
        await send_cat_to_chat(chat_id)
    except Exception as exc:
        logging.exception("Failed to send initial cat to %s: %s", chat_id, exc)

    hours = interval_seconds // 3600
    minutes = (interval_seconds % 3600) // 60
    if hours and minutes:
        label = f"{hours} час(а/ов) и {minutes} минут(ы)"
    elif hours:
        label = f"{hours} час(а/ов)"
    else:
        label = f"{minutes} минут(ы)"

    await message.answer(f"Отлично! Я буду присылать котенка каждые {label}.")


async def periodic_cat_sender():
    while True:
        await asyncio.sleep(60)
        now = time.time()
        for user_id, data in list(users.items()):
            if not data.get('subscribed'):
                continue
            interval = data.get('interval')
            if not interval:
                continue
            last_sent = data.get('last_sent')
            if last_sent is None or (now - last_sent) >= interval:
                try:
                    await send_cat_to_chat(user_id)
                    data['last_sent'] = now
                    save_users()
                except Exception as exc:
                    logging.exception("Failed to send cat to %s: %s", user_id, exc)


async def show_help(message: Message):
    await message.answer(
        "Привет, я котенок-бурмалденок! 😺😺 \n" \
        "Напиши /cat, чтобы я отправил котенка,\n" \
        "или /time, чтобы выбрать расписание. \n\n" \
        "Если котятки перестанут тебе нравиться, то можешь написать /stop, " \
        "и я больше не буду отправлять тебе котят."
    )


@dp.message(CommandStart())
async def start(message: Message):
    await show_help(message)


@dp.message(Command("help"))
async def help_command(message: Message):
    await show_help(message)


@dp.message(Command("cat"))
async def send_cat(message: Message):
    await send_cat_to_chat(message.chat.id)


@dp.message(Command("time"))
async def choose_time(message: Message):
    if message.chat.id not in users:
        users[message.chat.id] = {'subscribed': False, 'interval': None, 'last_sent': None}
    save_users()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="30 минут", callback_data="30m")],
        [InlineKeyboardButton(text="1 час", callback_data="1h")],
        [InlineKeyboardButton(text="2 часа", callback_data="2h")],
        [InlineKeyboardButton(text="другое время", callback_data="custom")],
    ])
    await message.answer("Выбери интервал между котятами:", reply_markup=keyboard)


@dp.callback_query(lambda callback: callback.data in {"30m", "1h", "2h", "custom"})
async def handle_interval_choice(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    if callback.data == "custom":
        await callback.message.answer("Введите количество часов:")
        await state.set_state(Form.waiting_for_hours)
        return

    interval_map = {"30m": 1800, "1h": 3600, "2h": 7200}
    await subscribe_user(callback.message.chat.id, interval_map[callback.data], callback.message)


@dp.message(Form.waiting_for_hours)
async def handle_custom_hours(message: Message, state: FSMContext):
    try:
        hours = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, отправь число часов.")
        return

    if hours <= 0:
        await message.answer("Число часов должно быть положительным.")
        return

    await subscribe_user(message.chat.id, hours * 3600, message)
    await state.clear()

@dp.message(Command("stop"))
async def unsubscribe(message: Message):
    if message.chat.id in users and users[message.chat.id]['subscribed']:
        del users[message.chat.id]
        save_users()
        await message.answer('Ты больне будешь получать котят 😿😿')


async def main():
    global users
    users = load_users()
    asyncio.create_task(periodic_cat_sender())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())