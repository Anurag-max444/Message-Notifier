import pytest

from notifier.state import NotifyState, _in_time_window, _minutes_of_day


class FakeSupabase:
    """No-op stand-in — NotifyState tests only care about in-memory behavior."""
    def __getattr__(self, name):
        raise AssertionError(f"Unexpected Supabase call in a pure-logic test: {name}")


class FakeSupabaseAllowingWrites:
    """Accepts .table(...).update/upsert/delete(...).eq(...).execute() chains as no-ops."""
    def table(self, name):
        return self

    def update(self, *a, **k):
        return self

    def upsert(self, *a, **k):
        return self

    def delete(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def execute(self):
        return None


def make_state(cooldown_seconds=30, global_mute_until=0, vips=None,
               allow_groups=False, reveal_sender=False, quiet_start=None, quiet_end=None):
    return NotifyState(
        FakeSupabase(),
        cooldown_seconds=cooldown_seconds,
        global_mute_until=global_mute_until,
        vips=vips or {},
        allow_groups=allow_groups,
        reveal_sender=reveal_sender,
        quiet_start=quiet_start,
        quiet_end=quiet_end,
    )


def vip(muted_until=0, cooldown_seconds=None, label=None):
    return {"muted_until": muted_until, "cooldown_seconds": cooldown_seconds, "label": label}


class TestNormalUserCooldown:
    def test_allows_first_notification(self):
        state = make_state(cooldown_seconds=30)
        assert state.should_notify(sender_id=1, now=1_000_000.0) is True

    def test_blocks_within_cooldown_window(self):
        state = make_state(cooldown_seconds=30)
        state.mark_notified(sender_id=1, now=1_000_000.0)
        assert state.should_notify(sender_id=1, now=1_000_010.0) is False

    def test_allows_after_cooldown_window(self):
        state = make_state(cooldown_seconds=30)
        state.mark_notified(sender_id=1, now=1_000_000.0)
        assert state.should_notify(sender_id=1, now=1_000_100.0) is True

    def test_cooldown_is_global_across_different_senders(self):
        state = make_state(cooldown_seconds=30)
        state.mark_notified(sender_id=1, now=1_000_000.0)
        assert state.should_notify(sender_id=2, now=1_000_010.0) is False


class TestGlobalMute:
    def test_blocks_while_muted(self):
        state = make_state(global_mute_until=1_000_500.0)
        assert state.should_notify(sender_id=1, now=1_000_000.0) is False

    def test_allows_after_mute_expires(self):
        state = make_state(global_mute_until=1_000_000.0)
        assert state.should_notify(sender_id=1, now=1_000_500.0) is True

    def test_resume_clears_mute_immediately(self):
        state = make_state(global_mute_until=99_999_999_999.0)
        state.client = FakeSupabaseAllowingWrites()
        state.resume()
        assert state.global_mute_until == 0


class TestVipFullBypass:
    def test_vip_bypasses_global_mute(self):
        state = make_state(global_mute_until=99_999_999_999.0, vips={42: vip()})
        assert state.should_notify(sender_id=42, now=1_000_000.0) is True

    def test_vip_bypasses_cooldown_every_message(self):
        state = make_state(cooldown_seconds=30, vips={42: vip()})
        assert state.should_notify(sender_id=42, now=1_000_000.0) is True
        state.mark_notified(sender_id=42, now=1_000_000.0)
        assert state.should_notify(sender_id=42, now=1_000_000.01) is True

    def test_individually_muted_vip_is_blocked(self):
        state = make_state(vips={42: vip(muted_until=1_000_500.0)})
        assert state.should_notify(sender_id=42, now=1_000_000.0) is False

    def test_individually_muted_vip_resumes_after_expiry(self):
        state = make_state(vips={42: vip(muted_until=1_000_000.0)})
        assert state.should_notify(sender_id=42, now=1_000_500.0) is True

    def test_non_vip_unaffected_by_vip_mute(self):
        state = make_state(cooldown_seconds=30, vips={42: vip(muted_until=99_999_999_999.0)})
        assert state.should_notify(sender_id=99, now=1_000_000.0) is True


class TestVipCustomCooldown:
    def test_vip_with_cooldown_blocks_within_window(self):
        state = make_state(vips={42: vip(cooldown_seconds=10)})
        state.mark_notified(sender_id=42, now=1_000_000.0)
        assert state.should_notify(sender_id=42, now=1_000_005.0) is False

    def test_vip_with_cooldown_allows_after_window(self):
        state = make_state(vips={42: vip(cooldown_seconds=10)})
        state.mark_notified(sender_id=42, now=1_000_000.0)
        assert state.should_notify(sender_id=42, now=1_000_015.0) is True

    def test_vip_cooldown_is_independent_of_global_cooldown(self):
        state = make_state(cooldown_seconds=9999, vips={42: vip(cooldown_seconds=5)})
        state.mark_notified(sender_id=1, now=1_000_000.0)
        assert state.should_notify(sender_id=42, now=1_000_001.0) is True

    def test_set_vip_cooldown_seconds_updates_state(self):
        state = make_state(vips={42: vip()})
        state.client = FakeSupabaseAllowingWrites()
        state.set_vip_cooldown_seconds(42, 5)
        assert state.vips[42]["cooldown_seconds"] == 5


class TestQuietHours:
    def test_no_quiet_hours_set_never_blocks(self):
        state = make_state()
        assert state.has_quiet_hours() is False
        assert state.is_quiet_now(now=1_000_000.0) is False

    def test_simple_window_blocks_inside(self):
        assert _in_time_window(_minutes_of_day("12:00"), 9 * 60, 17 * 60) is True

    def test_simple_window_allows_outside(self):
        assert _in_time_window(_minutes_of_day("20:00"), 9 * 60, 17 * 60) is False

    def test_overnight_window_wraps_midnight(self):
        start, end = _minutes_of_day("23:00"), _minutes_of_day("07:00")
        assert _in_time_window(_minutes_of_day("23:30"), start, end) is True
        assert _in_time_window(_minutes_of_day("03:00"), start, end) is True
        assert _in_time_window(_minutes_of_day("12:00"), start, end) is False

    def test_clear_quiet_hours_removes_window(self):
        state = make_state(quiet_start="23:00", quiet_end="07:00")
        state.client = FakeSupabaseAllowingWrites()
        state.clear_quiet_hours()
        assert state.has_quiet_hours() is False


class TestVipUserSetHelpers:
    def test_vip_users_property(self):
        state = make_state(vips={1: vip(), 2: vip()})
        assert state.vip_users == {1, 2}

    def test_is_vip(self):
        state = make_state(vips={1: vip()})
        assert state.is_vip(1) is True
        assert state.is_vip(2) is False

    def test_vip_mute_until_backcompat_property(self):
        state = make_state(vips={1: vip(muted_until=123)})
        assert state.vip_mute_until == {1: 123}


class TestVipLabels:
    def test_add_vip_with_label(self):
        state = make_state()
        state.client = FakeSupabaseAllowingWrites()
        state.add_vip(42, "College Group")
        assert state.vips[42]["label"] == "College Group"

    def test_add_vip_without_label_defaults_to_none(self):
        state = make_state()
        state.client = FakeSupabaseAllowingWrites()
        state.add_vip(42)
        assert state.vips[42]["label"] is None

    def test_set_vip_label_updates_existing_vip(self):
        state = make_state(vips={42: vip()})
        state.client = FakeSupabaseAllowingWrites()
        state.set_vip_label(42, "Family")
        assert state.vips[42]["label"] == "Family"

    def test_set_vip_label_none_clears_it(self):
        state = make_state(vips={42: vip(label="Family")})
        state.client = FakeSupabaseAllowingWrites()
        state.set_vip_label(42, None)
        assert state.vips[42]["label"] is None

    def test_loaded_vips_missing_label_key_default_to_none(self):
        # Simulates older rows loaded before the label column existed.
        state = NotifyState(
            FakeSupabase(), cooldown_seconds=30, global_mute_until=0,
            vips={1: {"muted_until": 0, "cooldown_seconds": None}},
        )
        assert state.vips[1]["label"] is None


class TestAllowedChats:
    def test_empty_by_default(self):
        state = make_state()
        assert state.allowed_chats == {}

    def test_constructor_accepts_allowed_chats(self):
        state = NotifyState(
            FakeSupabase(), cooldown_seconds=30, global_mute_until=0, vips={},
            allowed_chats={-100123: "My Group"},
        )
        assert state.allowed_chats == {-100123: "My Group"}

    def test_add_allowed_chat(self):
        state = make_state()
        state.client = FakeSupabaseAllowingWrites()
        state.add_allowed_chat(-100123, "My Group")
        assert state.allowed_chats[-100123] == "My Group"

    def test_remove_allowed_chat(self):
        state = NotifyState(
            FakeSupabase(), cooldown_seconds=30, global_mute_until=0, vips={},
            allowed_chats={-100123: "My Group"},
        )
        state.client = FakeSupabaseAllowingWrites()
        state.remove_allowed_chat(-100123)
        assert -100123 not in state.allowed_chats
