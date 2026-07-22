"""Small helpers shared across every command module."""

import asyncio


def is_owner(event, cfg) -> bool:
    return event.sender_id in cfg.control_owner_ids


def fmt_seconds(total: float) -> str:
    total = max(0, int(total))
    m, s = divmod(total, 60)
    return f"{m}m {s}s" if m else f"{s}s"


async def to_thread(func, *args):
    """Runs a blocking (Supabase) call off the event loop."""
    return await asyncio.to_thread(func, *args)
