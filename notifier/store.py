"""
Supabase-backed persistence for the notifier's runtime-controllable state
(cooldown, global mute, VIP list). Keeps the two tables in sync:

    notifier_state (single row, id=1)
        cooldown_seconds   int
        global_mute_until  bigint (unix timestamp)

    notifier_vips
        user_id       bigint primary key
        muted_until   bigint (unix timestamp; 0 = not muted)

All calls are synchronous (supabase-py is a blocking client); callers
should run them via asyncio.to_thread() from async code so the event
loop is never blocked.
"""

from supabase import create_client, Client


def get_client(url: str, key: str) -> Client:
    return create_client(url, key)


def load_state(client: Client) -> dict:
    """Returns {'cooldown_seconds': int, 'global_mute_until': int}."""
    res = client.table("notifier_state").select("*").eq("id", 1).single().execute()
    row = res.data
    return {
        "cooldown_seconds": row["cooldown_seconds"],
        "global_mute_until": row["global_mute_until"],
    }


def save_cooldown(client: Client, seconds: int) -> None:
    client.table("notifier_state").update({"cooldown_seconds": seconds}).eq("id", 1).execute()


def save_global_mute(client: Client, until_ts: int) -> None:
    client.table("notifier_state").update({"global_mute_until": until_ts}).eq("id", 1).execute()


def load_vips(client: Client) -> dict:
    """Returns {user_id: muted_until} for every VIP row."""
    res = client.table("notifier_vips").select("*").execute()
    return {row["user_id"]: row["muted_until"] for row in res.data}


def add_vip(client: Client, user_id: int) -> None:
    client.table("notifier_vips").upsert({"user_id": user_id, "muted_until": 0}).execute()


def remove_vip(client: Client, user_id: int) -> None:
    client.table("notifier_vips").delete().eq("user_id", user_id).execute()


def set_vip_mute(client: Client, user_id: int, until_ts: int) -> None:
    client.table("notifier_vips").update({"muted_until": until_ts}).eq("user_id", user_id).execute()
