"""
Supabase-backed persistence for the notifier's runtime-controllable
state. Split into one file per concern:

    client.py       -> Supabase client factory
    state_store.py  -> notifier_state (cooldown, mute, groups, reveal, quiet hours)
    vip_store.py    -> notifier_vips (mute, cooldown, label)
    chat_store.py   -> notifier_allowed_chats (per-group/channel allow-list)

All calls are synchronous (supabase-py is a blocking client); callers
should run them via asyncio.to_thread() from async code so the event
loop is never blocked.

This __init__ re-exports everything so the rest of the codebase can
keep doing `from notifier import store; store.load_state(client)`
without needing to know about the internal file split.
"""

from notifier.store.client import get_client
from notifier.store.state_store import (
    load_state,
    save_cooldown,
    save_global_mute,
    save_allow_groups,
    save_reveal_sender,
    save_quiet_hours,
)
from notifier.store.vip_store import (
    load_vips,
    add_vip,
    remove_vip,
    set_vip_mute,
    set_vip_cooldown,
    set_vip_label,
)
from notifier.store.chat_store import (
    load_allowed_chats,
    add_allowed_chat,
    remove_allowed_chat,
)

__all__ = [
    "get_client",
    "load_state", "save_cooldown", "save_global_mute", "save_allow_groups",
    "save_reveal_sender", "save_quiet_hours",
    "load_vips", "add_vip", "remove_vip", "set_vip_mute", "set_vip_cooldown", "set_vip_label",
    "load_allowed_chats", "add_allowed_chat", "remove_allowed_chat",
]
