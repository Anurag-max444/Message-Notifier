import logging

import pytest
from telethon import TelegramClient
from telethon.sessions import StringSession

from notifier.commands import register_commands, COMMAND_LIST, _help_text
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
def bot_client():
    # Never connects — just used as an event-handler registry here.
    return TelegramClient(StringSession(), 123456, "abcdef123456")


def test_command_list_names_are_unique():
    names = [cmd for cmd, _ in COMMAND_LIST]
    assert len(names) == len(set(names))


def test_command_list_has_no_slash_prefix():
    # BotFather's /setcommands expects bare command names, no leading "/".
    for cmd, _ in COMMAND_LIST:
        assert not cmd.startswith("/")


def test_help_text_lists_every_command_with_dash_format():
    text = _help_text()
    for cmd, desc in COMMAND_LIST:
        assert f"/{cmd} - {desc}" in text


def test_register_commands_attaches_handler_for_each_command_plus_callbacks(bot_client, state):
    log = logging.getLogger("test")
    register_commands(bot_client, FakeCfg(), state, log)
    handlers = bot_client.list_event_handlers()
    # 9 commands + 3 callback-query handlers (skip, vipmute, vip-remove)
    assert len(handlers) == len(COMMAND_LIST) + 3
