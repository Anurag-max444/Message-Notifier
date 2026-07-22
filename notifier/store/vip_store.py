"""
Persistence for notifier_vips:
    user_id           bigint primary key
    muted_until       bigint (unix timestamp; 0 = not muted)
    cooldown_seconds  int or null (null = fully bypasses cooldown)
    label             text or null (for grouping in /vips)
"""

from supabase import Client


def load_vips(client: Client) -> dict:
    """Returns {user_id: {"muted_until": int, "cooldown_seconds": int|None, "label": str|None}}."""
    res = client.table("notifier_vips").select("*").execute()
    return {
        row["user_id"]: {
            "muted_until": row["muted_until"],
            "cooldown_seconds": row.get("cooldown_seconds"),
            "label": row.get("label"),
        }
        for row in res.data
    }


def add_vip(client: Client, user_id: int, label: str = None) -> None:
    client.table("notifier_vips").upsert(
        {"user_id": user_id, "muted_until": 0, "cooldown_seconds": None, "label": label}
    ).execute()


def remove_vip(client: Client, user_id: int) -> None:
    client.table("notifier_vips").delete().eq("user_id", user_id).execute()


def set_vip_mute(client: Client, user_id: int, until_ts: int) -> None:
    client.table("notifier_vips").update({"muted_until": until_ts}).eq("user_id", user_id).execute()


def set_vip_cooldown(client: Client, user_id: int, seconds) -> None:
    """seconds=None fully bypasses cooldown (the original VIP behavior)."""
    client.table("notifier_vips").update({"cooldown_seconds": seconds}).eq("user_id", user_id).execute()


def set_vip_label(client: Client, user_id: int, label) -> None:
    """label=None clears the label (VIP shows as "Unlabeled" in /vips)."""
    client.table("notifier_vips").update({"label": label}).eq("user_id", user_id).execute()
