"""
The user_client side: watches the monitored personal account for new
incoming messages (private always; groups/channels only if enabled via
/groups, optionally narrowed to specific chats via /allowchat) and asks
bot_client to notify the owner.
"""

from telethon import events

from notifier.config import NOTIFICATION_TEXT
from notifier.logic import should_process_message
from notifier.group_filter import is_chat_in_allowlist


async def _build_notification_text(state, event) -> str:
    if not state.reveal_sender:
        return NOTIFICATION_TEXT
    sender_name = "someone"
    try:
        sender = await event.get_sender()
        if sender is not None:
            sender_name = getattr(sender, "first_name", None) or getattr(sender, "title", None) or "someone"
    except Exception:
        pass  # never let a name lookup failure block the notification
    return f"{NOTIFICATION_TEXT} (from {sender_name})"


def register_notify_handler(user_client, bot_client, cfg, state, log, bot_identity):
    """
    bot_identity: a dict with key "id", populated once bot_client logs in
    (see notifier.commands / bot.py). Used to ignore the bot's own
    notification messages so they don't re-trigger themselves — without
    this, sending a notification would count as a new incoming private
    message and loop forever.
    """

    @user_client.on(events.NewMessage())
    async def on_new_message(event):
        if not should_process_message(event.is_private, event.out, state.allow_groups):
            return

        if not event.is_private and not is_chat_in_allowlist(event.chat_id, state.allowed_chats):
            return

        bot_id = bot_identity.get("id")
        if bot_id is not None and event.sender_id == bot_id:
            return

        sender_id = event.sender_id
        if not state.should_notify(sender_id):
            return
        state.mark_notified(sender_id)

        text = await _build_notification_text(state, event)
        try:
            await bot_client.send_message(cfg.owner_id, text)
            log.info("Notification sent.")
        except Exception as e:
            log.error(f"Failed to send notification: {e}")

    return on_new_message
