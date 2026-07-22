"""
Runtime-controllable notification state: cooldown, global mute, VIP
list (with optional per-VIP custom cooldown and label), group/channel
toggle with an optional per-chat allow-list, sender-reveal toggle, and
scheduled quiet hours.

Kept in memory for fast per-message checks; every mutation is written
through to Supabase immediately (see notifier/store/) so state
survives bot restarts/redeploys.
"""

import time

from notifier import store


def _minutes_of_day(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _in_time_window(now_minutes: int, start_minutes: int, end_minutes: int) -> bool:
    """Handles windows that wrap past midnight (e.g. 23:00 -> 07:00)."""
    if start_minutes <= end_minutes:
        return start_minutes <= now_minutes < end_minutes
    return now_minutes >= start_minutes or now_minutes < end_minutes


class NotifyState:
    def __init__(self, supabase_client, *, cooldown_seconds: int, global_mute_until: int,
                 vips: dict, allow_groups: bool = False, reveal_sender: bool = False,
                 quiet_start=None, quiet_end=None, allowed_chats: dict = None):
        self.client = supabase_client
        self.cooldown_seconds = cooldown_seconds
        self.global_mute_until = global_mute_until
        self.last_notify_time = 0.0
        self.allow_groups = allow_groups
        self.reveal_sender = reveal_sender
        self.quiet_start = quiet_start  # "HH:MM" or None
        self.quiet_end = quiet_end      # "HH:MM" or None

        # vips: {user_id: {"muted_until": ts, "cooldown_seconds": int|None, "label": str|None}}
        self.vips = {int(uid): dict(v) for uid, v in vips.items()}
        for v in self.vips.values():
            v.setdefault("label", None)
        self.vip_last_notify = {}  # user_id -> timestamp, only used when a VIP has a custom cooldown

        # allowed_chats: {chat_id: label|None} — empty means "no restriction"
        self.allowed_chats = {int(cid): label for cid, label in (allowed_chats or {}).items()}

    @classmethod
    def load(cls, supabase_client) -> "NotifyState":
        s = store.load_state(supabase_client)
        vips = store.load_vips(supabase_client)
        allowed_chats = store.load_allowed_chats(supabase_client)
        return cls(
            supabase_client,
            cooldown_seconds=s["cooldown_seconds"],
            global_mute_until=s["global_mute_until"],
            vips=vips,
            allow_groups=s["allow_groups"],
            reveal_sender=s["reveal_sender"],
            quiet_start=s["quiet_start"],
            quiet_end=s["quiet_end"],
            allowed_chats=allowed_chats,
        )

    @property
    def vip_users(self) -> set:
        return set(self.vips.keys())

    @property
    def vip_mute_until(self) -> dict:
        """Back-compat convenience: {user_id: muted_until}."""
        return {uid: v["muted_until"] for uid, v in self.vips.items()}

    def is_vip(self, user_id: int) -> bool:
        return user_id in self.vips

    def has_quiet_hours(self) -> bool:
        return bool(self.quiet_start and self.quiet_end)

    def is_quiet_now(self, now: float = None) -> bool:
        if not self.has_quiet_hours():
            return False
        now = time.time() if now is None else now
        now_minutes = time.localtime(now).tm_hour * 60 + time.localtime(now).tm_min
        return _in_time_window(
            now_minutes, _minutes_of_day(self.quiet_start), _minutes_of_day(self.quiet_end)
        )

    # --- Notification decision ---

    def should_notify(self, sender_id: int, now: float = None) -> bool:
        now = time.time() if now is None else now

        if sender_id in self.vips:
            vip = self.vips[sender_id]
            if vip["muted_until"] > now:
                return False
            cooldown = vip["cooldown_seconds"]
            if cooldown is None:
                return True  # full bypass — every message notifies
            last = self.vip_last_notify.get(sender_id, 0.0)
            return (now - last) >= cooldown

        if self.is_quiet_now(now):
            return False
        if now < self.global_mute_until:
            return False
        if now - self.last_notify_time < self.cooldown_seconds:
            return False
        return True

    def mark_notified(self, sender_id: int, now: float = None) -> None:
        now = time.time() if now is None else now
        if sender_id in self.vips:
            if self.vips[sender_id]["cooldown_seconds"] is not None:
                self.vip_last_notify[sender_id] = now
        else:
            self.last_notify_time = now

    # --- Mutations (each persists to Supabase; call via asyncio.to_thread) ---

    def set_cooldown_minutes(self, minutes: int) -> None:
        self.cooldown_seconds = minutes * 60
        store.save_cooldown(self.client, self.cooldown_seconds)

    def mute_all_minutes(self, minutes: int) -> None:
        self.global_mute_until = time.time() + minutes * 60
        store.save_global_mute(self.client, int(self.global_mute_until))

    def resume(self) -> None:
        self.global_mute_until = 0
        store.save_global_mute(self.client, 0)

    def set_allow_groups(self, allow: bool) -> None:
        self.allow_groups = allow
        store.save_allow_groups(self.client, allow)

    def set_reveal_sender(self, reveal: bool) -> None:
        self.reveal_sender = reveal
        store.save_reveal_sender(self.client, reveal)

    def set_quiet_hours(self, start: str, end: str) -> None:
        self.quiet_start = start
        self.quiet_end = end
        store.save_quiet_hours(self.client, start, end)

    def clear_quiet_hours(self) -> None:
        self.quiet_start = None
        self.quiet_end = None
        store.save_quiet_hours(self.client, None, None)

    def add_vip(self, user_id: int, label: str = None) -> None:
        self.vips[user_id] = {"muted_until": 0, "cooldown_seconds": None, "label": label}
        store.add_vip(self.client, user_id, label)

    def remove_vip(self, user_id: int) -> None:
        self.vips.pop(user_id, None)
        self.vip_last_notify.pop(user_id, None)
        store.remove_vip(self.client, user_id)

    def mute_vip_minutes(self, user_id: int, minutes: int) -> int:
        until_ts = int(time.time() + minutes * 60)
        self.vips.setdefault(user_id, {"muted_until": 0, "cooldown_seconds": None, "label": None})
        self.vips[user_id]["muted_until"] = until_ts
        store.set_vip_mute(self.client, user_id, until_ts)
        return until_ts

    def set_vip_cooldown_seconds(self, user_id: int, seconds) -> None:
        """seconds=None restores full bypass (instant, every message)."""
        self.vips.setdefault(user_id, {"muted_until": 0, "cooldown_seconds": None, "label": None})
        self.vips[user_id]["cooldown_seconds"] = seconds
        store.set_vip_cooldown(self.client, user_id, seconds)

    def set_vip_label(self, user_id: int, label) -> None:
        """label=None clears it — VIP shows under "Unlabeled" in /vips."""
        self.vips.setdefault(user_id, {"muted_until": 0, "cooldown_seconds": None, "label": None})
        self.vips[user_id]["label"] = label
        store.set_vip_label(self.client, user_id, label)

    # --- Per-group/channel allow-list ---

    def add_allowed_chat(self, chat_id: int, label: str = None) -> None:
        self.allowed_chats[chat_id] = label
        store.add_allowed_chat(self.client, chat_id, label)

    def remove_allowed_chat(self, chat_id: int) -> None:
        self.allowed_chats.pop(chat_id, None)
        store.remove_allowed_chat(self.client, chat_id)
