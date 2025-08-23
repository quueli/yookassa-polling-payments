import os
import pathlib
import tempfile
from types import SimpleNamespace

import pytest

# has to happen before config is imported anywhere
_tmp = tempfile.mkdtemp(prefix="yookassa-polling-")
os.environ["DATABASE_URL"] = "sqlite:///" + (pathlib.Path(_tmp) / "test.db").as_posix()
os.environ["ADMIN_CHAT_ID"] = "-1001234567890"
os.environ["USE_PAYMENT_POLLING"] = "false"


class FakeBot:
    def __init__(self):
        self.messages = []
        self.edits = []
        self._next_id = 100

    async def send_message(self, chat_id, text, reply_markup=None, **kwargs):
        self._next_id += 1
        message = SimpleNamespace(chat_id=str(chat_id), message_id=self._next_id, text=text, reply_markup=reply_markup)
        self.messages.append(message)
        return message

    async def edit_message_text(self, chat_id, message_id, text, reply_markup=None, **kwargs):
        self.edits.append(SimpleNamespace(chat_id=str(chat_id), message_id=message_id,
                                          text=text, reply_markup=reply_markup))
        return True

    def messages_to(self, chat_id):
        return [m for m in self.messages if m.chat_id == str(chat_id)]


@pytest.fixture(scope="session")
def db():
    from database import db_manager

    db_manager.create_tables()
    return db_manager


@pytest.fixture
def bot():
    return FakeBot()
