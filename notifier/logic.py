"""
Pure, side-effect-free logic used by bot.py.
Separated out so it can be unit tested without a real Telegram connection.
"""

from dataclasses import dataclass


@dataclass
class CooldownGate:
    """
    Tracks the last time a notification was sent and decides whether
    a new one is allowed to fire, given a cooldown window in seconds.
    """
    cooldown_seconds: int
    last_sent: float = 0.0

    def should_notify(self, now: float) -> bool:
        return (now - self.last_sent) >= self.cooldown_seconds

    def mark_sent(self, now: float) -> None:
        self.last_sent = now


def should_process_message(is_private: bool, is_outgoing: bool) -> bool:
    """
    Returns True only for incoming private messages.
    Groups, channels, and outgoing messages are ignored.
    """
    if not is_private:
        return False
    if is_outgoing:
        return False
    return True
