import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


module_path = Path(__file__).with_name("main.py")
spec = importlib.util.spec_from_file_location("catsbot_main", module_path)
main_module = importlib.util.module_from_spec(spec)

sys.modules["requests"] = types.SimpleNamespace(get=lambda *args, **kwargs: None)
class DummyBot:
    def __init__(self, *args, **kwargs):
        pass


class DummyDispatcher:
    def __init__(self, *args, **kwargs):
        pass

    def message(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

    def callback_query(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator


aiogram_module = types.ModuleType("aiogram")
aiogram_module.Bot = DummyBot
aiogram_module.Dispatcher = DummyDispatcher
sys.modules["aiogram"] = aiogram_module
class DummyCommand:
    def __init__(self, *args, **kwargs):
        pass


filters_module = types.ModuleType("aiogram.filters")
filters_module.Command = DummyCommand
filters_module.CommandStart = DummyCommand
sys.modules["aiogram.filters"] = filters_module
fsm_module = types.ModuleType("aiogram.fsm")
fsm_context_module = types.ModuleType("aiogram.fsm.context")
fsm_context_module.FSMContext = object
fsm_state_module = types.ModuleType("aiogram.fsm.state")
fsm_state_module.State = object
fsm_state_module.StatesGroup = object
sys.modules["aiogram.fsm"] = fsm_module
sys.modules["aiogram.fsm.context"] = fsm_context_module
sys.modules["aiogram.fsm.state"] = fsm_state_module
types_module = types.ModuleType("aiogram.types")
types_module.CallbackQuery = object
types_module.InlineKeyboardButton = object
types_module.InlineKeyboardMarkup = object
types_module.Message = object
sys.modules["aiogram.types"] = types_module

spec.loader.exec_module(main_module)


class PersistenceTests(unittest.TestCase):
    def test_load_and_save_users_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            main_module.STORAGE_FILE = os.path.join(tmpdir, "users.json")
            main_module.users = {}
            main_module.save_users()
            self.assertEqual(main_module.load_users(), {})

            main_module.users = {
                1: {"subscribed": True, "interval": 3600, "last_sent": 12345}
            }
            main_module.save_users()

            reloaded = main_module.load_users()
            self.assertEqual(reloaded[1]["interval"], 3600)
            self.assertTrue(reloaded[1]["subscribed"])
            self.assertEqual(reloaded[1]["last_sent"], 12345)


if __name__ == "__main__":
    unittest.main()
