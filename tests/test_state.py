import pytest

from notifier.state import NotifyState


class FakeSupabase:
    """No-op stand-in — NotifyState tests only care about in-memory behavior."""
    def __getattr__(self, name):
        raise AssertionError(f"Unexpected Supabase call in a pure-logic test: {name}")


def make_state(cooldown_seconds=30, global_mute_until=0, vip_mute_until=None):
    return NotifyState(
        FakeSupabase(),
        cooldown_seconds=cooldown_seconds,
        global_mute_until=global_mute_until,
        vip_mute_until=vip_mute_until or {},
    )


class TestNormalUserCooldown:
    def test_allows_first_notification(self):
        state = make_state(cooldown_seconds=30)
        assert state.should_notify(sender_id=1, now=100.0) is True

    def test_blocks_within_cooldown_window(self):
        state = make_state(cooldown_seconds=30)
        state.mark_notified(sender_id=1, now=100.0)
        assert state.should_notify(sender_id=1, now=110.0) is False

    def test_allows_after_cooldown_window(self):
        state = make_state(cooldown_seconds=30)
        state.mark_notified(sender_id=1, now=100.0)
        assert state.should_notify(sender_id=1, now=200.0) is True

    def test_cooldown_is_global_across_different_senders(self):
        # Cooldown gates ALL normal notifications together, not per-sender.
        state = make_state(cooldown_seconds=30)
        state.mark_notified(sender_id=1, now=100.0)
        assert state.should_notify(sender_id=2, now=110.0) is False


class TestGlobalMute:
    def test_blocks_while_muted(self):
        state = make_state(global_mute_until=1000.0)
        assert state.should_notify(sender_id=1, now=500.0) is False

    def test_allows_after_mute_expires(self):
        state = make_state(global_mute_until=1000.0)
        assert state.should_notify(sender_id=1, now=1500.0) is True

    def test_resume_clears_mute_immediately(self):
        state = make_state(global_mute_until=99999.0)
        state.global_mute_until = 0  # resume() would call this + Supabase
        assert state.should_notify(sender_id=1, now=500.0) is True


class TestVipBypass:
    def test_vip_bypasses_global_mute(self):
        state = make_state(global_mute_until=99999.0, vip_mute_until={42: 0})
        assert state.should_notify(sender_id=42, now=500.0) is True

    def test_vip_bypasses_cooldown_every_message(self):
        state = make_state(cooldown_seconds=30, vip_mute_until={42: 0})
        assert state.should_notify(sender_id=42, now=1.0) is True
        state.mark_notified(sender_id=42, now=1.0)
        # Immediately again, no gap at all — still notifies.
        assert state.should_notify(sender_id=42, now=1.01) is True

    def test_individually_muted_vip_is_blocked(self):
        state = make_state(vip_mute_until={42: 1000.0})
        assert state.should_notify(sender_id=42, now=500.0) is False

    def test_individually_muted_vip_resumes_after_expiry(self):
        state = make_state(vip_mute_until={42: 1000.0})
        assert state.should_notify(sender_id=42, now=1500.0) is True

    def test_non_vip_unaffected_by_vip_mute(self):
        state = make_state(cooldown_seconds=30, vip_mute_until={42: 99999999999.0})
        assert state.should_notify(sender_id=99, now=1_000_000.0) is True


class TestVipUserSetHelpers:
    def test_vip_users_property(self):
        state = make_state(vip_mute_until={1: 0, 2: 0})
        assert state.vip_users == {1, 2}

    def test_is_vip(self):
        state = make_state(vip_mute_until={1: 0})
        assert state.is_vip(1) is True
        assert state.is_vip(2) is False
