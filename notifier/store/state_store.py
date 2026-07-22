"""
Persistence for notifier_state (single row, id=1):
    cooldown_seconds   int
    global_mute_until  bigint (unix timestamp)
    allow_groups       boolean
    reveal_sender      boolean
    quiet_start        text ("HH:MM" or null)
    quiet_end          text ("HH:MM" or null)
"""

from supabase import Client


def load_state(client: Client) -> dict:
    res = client.table("notifier_state").select("*").eq("id", 1).single().execute()
    row = res.data
    return {
        "cooldown_seconds": row["cooldown_seconds"],
        "global_mute_until": row["global_mute_until"],
        "allow_groups": row.get("allow_groups", False),
        "reveal_sender": row.get("reveal_sender", False),
        "quiet_start": row.get("quiet_start"),
        "quiet_end": row.get("quiet_end"),
    }


def save_cooldown(client: Client, seconds: int) -> None:
    client.table("notifier_state").update({"cooldown_seconds": seconds}).eq("id", 1).execute()


def save_global_mute(client: Client, until_ts: int) -> None:
    client.table("notifier_state").update({"global_mute_until": until_ts}).eq("id", 1).execute()


def save_allow_groups(client: Client, allow: bool) -> None:
    client.table("notifier_state").update({"allow_groups": allow}).eq("id", 1).execute()


def save_reveal_sender(client: Client, reveal: bool) -> None:
    client.table("notifier_state").update({"reveal_sender": reveal}).eq("id", 1).execute()


def save_quiet_hours(client: Client, start: str, end: str) -> None:
    """Pass start=None, end=None to clear quiet hours."""
    client.table("notifier_state").update({"quiet_start": start, "quiet_end": end}).eq("id", 1).execute()
