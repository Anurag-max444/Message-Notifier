import pytest

from notifier.logic import should_process_message


class TestShouldProcessMessage:
    def test_private_incoming_message_is_processed(self):
        assert should_process_message(is_private=True, is_outgoing=False) is True

    def test_group_message_is_ignored(self):
        assert should_process_message(is_private=False, is_outgoing=False) is False

    def test_channel_message_is_ignored(self):
        # Channels also report is_private=False in Telethon.
        assert should_process_message(is_private=False, is_outgoing=False) is False

    def test_outgoing_private_message_is_ignored(self):
        assert should_process_message(is_private=True, is_outgoing=True) is False

    def test_outgoing_group_message_is_ignored(self):
        assert should_process_message(is_private=False, is_outgoing=True) is False

    def test_bot_dm_is_processed(self):
        # A bot messaging you privately should still count — only
        # groups/channels and your own outgoing messages are excluded.
        assert should_process_message(is_private=True, is_outgoing=False) is True
