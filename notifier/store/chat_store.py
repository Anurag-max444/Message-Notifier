"""
Persistence for notifier_allowed_chats:
    chat_id    bigint primary key
    label      text or null (e.g. a friendly group name)

An empty table means "no restriction — every group/channel is allowed
when /groups is on". Adding rows here narrows that down to only the
listed chats.
"""

from supabase import Client


def load_allowed_chats(client: Client) -> dict:
    """Returns {chat_id: label|None}."""
    res = client.table("notifier_allowed_chats").select("*").execute()
    return {row["chat_id"]: row.get("label") for row in res.data}


def add_allowed_chat(client: Client, chat_id: int, label: str = None) -> None:
    client.table("notifier_allowed_chats").upsert({"chat_id": chat_id, "label": label}).execute()


def remove_allowed_chat(client: Client, chat_id: int) -> None:
    client.table("notifier_allowed_chats").delete().eq("chat_id", chat_id).execute()
