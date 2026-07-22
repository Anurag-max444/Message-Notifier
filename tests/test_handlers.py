import logging

import pytest
from telethon import TelegramClient
from telethon.sessions import StringSession

from notifier.handlers import register_notify_handler
from notifier.state import NotifyState


class FakeCfg:
    owner_id = 987654321


class FakeSupabase:
    def __getattr__(self, name):
        raise AssertionError("NotifyState should not hit Supabase in these tests")


@pytest.fixture
def state():
    return NotifyState(FakeSupabase(), cooldown_seconds=30, global_mute_until=0, vip_mute_until={})


@pytest.fixture
def clients():
    user_client = TelegramClient(StringSession(), 123456, "abcdef123456")
    bot_client = TelegramClient(StringSession(), 123456, "abcdef123456")
    return user_client, bot_client


def test_register_notify_handler_attaches_exactly_one_handler(clients, state):
    user_client, bot_client = clients
    log = logging.getLogger("test")
    register_notify_handler(user_client, bot_client, FakeCfg(), state, log, {"id": None})
    assert len(user_client.list_event_handlers()) == 1
    assert len(bot_client.list_event_handlers()) == 0


def test_bot_identity_dict_is_shared_by_reference(clients, state):
    # bot_identity must be a mutable container so bot.py can populate
    # the bot's own id *after* registration (bot logs in later than
    # handlers are registered) and have the handler see the update.
    user_client, bot_client = clients
    log = logging.getLogger("test")
    bot_identity = {"id": None}
    register_notify_handler(user_client, bot_client, FakeCfg(), state, log, bot_identity)
    bot_identity["id"] = 555
    assert bot_identity["id"] == 555
