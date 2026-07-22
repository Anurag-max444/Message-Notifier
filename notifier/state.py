"""
Runtime-controllable notification state: cooldown, global mute, and the
VIP list. Kept in memory for fast per-message checks; every mutation is
written through to Supabase immediately (see notifier/store.py) so state
survives bot restarts/redeploys.
"""

import time

from notifier import store


class NotifyState:
    def __init__(self, supabase_client, cooldown_seconds: int, global_mute_until: int,
                 vip_mute_until: dict):
        self.client = supabase_client
        self.cooldown_seconds = cooldown_seconds
        self.global_mute_until = global_mute_until
        self.last_notify_time = 0.0
        self.vip_mute_until = dict(vip_mute_until)  # user_id -> muted_until timestamp

    @classmethod
    def load(cls, supabase_client) -> "NotifyState":
        state = store.load_state(supabase_client)
        vips = store.load_vips(supabase_client)
        return cls(
            supabase_client,
            cooldown_seconds=state["cooldown_seconds"],
            global_mute_until=state["global_mute_until"],
            vip_mute_until=vips,
        )

    @property
    def vip_users(self) -> set:
        return set(self.vip_mute_until.keys())

    def is_vip(self, user_id: int) -> bool:
        return user_id in self.vip_mute_until

    # --- Notification decision ---

    def should_notify(self, sender_id: int, now: float = None) -> bool:
        now = time.time() if now is None else now

        if sender_id in self.vip_mute_until:
            # VIPs bypass global mute and cooldown entirely — every
            # single message notifies, unless that specific VIP is
            # individually muted via /vipmute.
            return self.vip_mute_until[sender_id] <= now

        if now < self.global_mute_until:
            return False
        if now - self.last_notify_time < self.cooldown_seconds:
            return False
        return True

    def mark_notified(self, sender_id: int, now: float = None) -> None:
        now = time.time() if now is None else now
        if sender_id not in self.vip_mute_until:
            self.last_notify_time = now

    # --- Mutations (each persists to Supabase; call via asyncio.to_thread) ---

    def set_cooldown_minutes(self, minutes: int) -> None:
        self.cooldown_seconds = minutes * 60
        store.save_cooldown(self.client, self.cooldown_seconds)

    def mute_all_minutes(self, minutes: int) -> None:
        self.global_mute_until = time.time() + minutes * 60
        store.save_global_mute(self.client, int(self.global_mute_until))

    def resume(self) -> None:
        """Immediately clears any active global mute."""
        self.global_mute_until = 0
        store.save_global_mute(self.client, 0)

    def add_vip(self, user_id: int) -> None:
        self.vip_mute_until[user_id] = 0
        store.add_vip(self.client, user_id)

    def remove_vip(self, user_id: int) -> None:
        self.vip_mute_until.pop(user_id, None)
        store.remove_vip(self.client, user_id)

    def mute_vip_minutes(self, user_id: int, minutes: int) -> int:
        until_ts = int(time.time() + minutes * 60)
        self.vip_mute_until[user_id] = until_ts
        store.set_vip_mute(self.client, user_id, until_ts)
        return until_ts
