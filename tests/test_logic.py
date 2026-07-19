import pytest

from notifier.logic import CooldownGate, should_process_message


class TestCooldownGate:
    def test_allows_first_notification(self):
        gate = CooldownGate(cooldown_seconds=30)
        assert gate.should_notify(now=100.0) is True

    def test_blocks_within_cooldown_window(self):
        gate = CooldownGate(cooldown_seconds=30, last_sent=100.0)
        assert gate.should_notify(now=110.0) is False

    def test_allows_exactly_at_cooldown_boundary(self):
        gate = CooldownGate(cooldown_seconds=30, last_sent=100.0)
        assert gate.should_notify(now=130.0) is True

    def test_allows_after_cooldown_window(self):
        gate = CooldownGate(cooldown_seconds=30, last_sent=100.0)
        assert gate.should_notify(now=200.0) is True

    def test_mark_sent_updates_last_sent(self):
        gate = CooldownGate(cooldown_seconds=30)
        gate.mark_sent(now=50.0)
        assert gate.last_sent == 50.0
        assert gate.should_notify(now=60.0) is False

    def test_zero_cooldown_always_allows(self):
        gate = CooldownGate(cooldown_seconds=0, last_sent=100.0)
        assert gate.should_notify(now=100.0) is True


class TestShouldProcessMessage:
    def test_private_incoming_message_is_processed(self):
        assert should_process_message(is_private=True, is_outgoing=False) is True

    def test_group_message_is_ignored(self):
        assert should_process_message(is_private=False, is_outgoing=False) is False

    def test_outgoing_private_message_is_ignored(self):
        assert should_process_message(is_private=True, is_outgoing=True) is False

    def test_outgoing_group_message_is_ignored(self):
        assert should_process_message(is_private=False, is_outgoing=True) is False
