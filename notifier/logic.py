"""
Pure, side-effect-free logic used by the notifier.
Separated out so it can be unit tested without a real Telegram connection.
"""


def should_process_message(is_private: bool, is_outgoing: bool) -> bool:
    """
    Returns True only for incoming private messages — this includes
    normal users AND bots that DM you privately. Groups, channels, and
    anything you send yourself (outgoing) are ignored.
    """
    if not is_private:
        return False
    if is_outgoing:
        return False
    return True
