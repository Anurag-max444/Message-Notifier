"""
Pure, side-effect-free logic used by the notifier.
Separated out so it can be unit tested without a real Telegram connection.
"""


def should_process_message(is_private: bool, is_outgoing: bool, allow_groups: bool = False) -> bool:
    """
    Returns True for incoming private messages (users AND bots that DM
    you) always. Groups/channels are included only when allow_groups is
    True (toggled at runtime via /groups). Anything you send yourself
    (outgoing) is always ignored.
    """
    if is_outgoing:
        return False
    if not is_private and not allow_groups:
        return False
    return True
