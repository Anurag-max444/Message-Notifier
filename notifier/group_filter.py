"""
Pure logic for the per-group/channel allow-list. Separate from
notifier/logic.py because it's a distinct concern: logic.py decides
"is this message type eligible at all" (private vs group, outgoing),
while this decides "given that groups are eligible, is THIS specific
chat one we actually want" — a finer-grained, independently testable
rule.
"""


def is_chat_in_allowlist(chat_id: int, allowed_chat_ids) -> bool:
    """
    If the allow-list is empty, every group/channel is allowed (as long
    as /groups is on) — this preserves the simple "all or nothing"
    behavior by default. Once at least one chat is explicitly added via
    /allowchat, only listed chats notify.
    """
    if not allowed_chat_ids:
        return True
    return chat_id in allowed_chat_ids
