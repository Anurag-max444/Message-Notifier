import logging

import pytest
from telethon import TelegramClient
from telethon.sessions import StringSession

from notifier.commands import register_commands, COMMAND_LIST, help_text
from notifier.commands.common import is_owner, fmt_seconds
from notifier.state import NotifyState


class FakeCfg:
    owner_id = 987654321
    control_owner_ids = (987654321,)


class FakeMultiOwnerCfg:
    owner_id = 987654321
    control_owner_ids = (111, 987654321)


class FakeSupabase:
    def __getattr__(self, name):
        raise AssertionError("NotifyState should not hit Supabase in these tests")


class FakeEvent:
    def __init__(self, sender_id):
        self.sender_id = sender_id


@pytest.fixture
def state():
    return NotifyState(FakeSupabase(), cooldown_seconds=30, global_mute_until=0, vips={})


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
    text = help_text()
    for cmd, desc in COMMAND_LIST:
        assert f"/{cmd} - {desc}" in text


def test_register_commands_attaches_handlers(bot_client, state):
    log = logging.getLogger("test")
    register_commands(bot_client, FakeCfg(), state, log)
    handlers = bot_client.list_event_handlers()
    assert len(handlers) > 0
    # Every command in COMMAND_LIST should be reachable via at least
    # one NewMessage handler pattern (a loose sanity check, not exact
    # count, since a couple of commands split into 2 patterns each).
    assert len(handlers) >= len(COMMAND_LIST)


class TestIsOwner:
    def test_single_owner_allowed(self):
        assert is_owner(FakeEvent(987654321), FakeCfg()) is True

    def test_non_owner_blocked(self):
        assert is_owner(FakeEvent(123), FakeCfg()) is False

    def test_multi_owner_all_allowed(self):
        assert is_owner(FakeEvent(111), FakeMultiOwnerCfg()) is True
        assert is_owner(FakeEvent(987654321), FakeMultiOwnerCfg()) is True

    def test_multi_owner_stranger_blocked(self):
        assert is_owner(FakeEvent(999), FakeMultiOwnerCfg()) is False


class TestFmtSeconds:
    def test_under_a_minute(self):
        assert fmt_seconds(45) == "45s"

    def test_over_a_minute(self):
        assert fmt_seconds(125) == "2m 5s"

    def test_negative_clamped_to_zero(self):
        assert fmt_seconds(-10) == "0s"
