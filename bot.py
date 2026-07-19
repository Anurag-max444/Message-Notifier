"""
Telegram Message Notifier — entrypoint.

Jab bhi personal Telegram account (user session) par koi naya
private message aaye, ek Bot (BOT_TOKEN wala) OWNER_ID ko generic
notification bhejta hai. Sender, content, ya count kabhi reveal
nahi hote.

Key properties:
- Kabhi phone number nahi maangta. StringSession invalid/expired/revoked
  hone par turant clear error deta hai aur exit ho jata hai — interactive
  login kabhi trigger nahi hota.
- Sirf incoming private chats process karta hai; groups/channels aur
  apne khud ke bheje messages ignore hote hain.
- Cooldown se spam nahi hota.
- Disconnect hone par auto-reconnect karta hai (session-revocation jaisi
  unrecoverable errors ko chhodkar, jinke liye naya session chahiye).
"""

import sys
import asyncio

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import (
    AuthKeyUnregisteredError,
    AuthKeyDuplicatedError,
    SessionPasswordNeededError,
    SessionRevokedError,
    UserDeactivatedError,
    UserDeactivatedBanError,
)

from notifier.config import load_config, ConfigError, NOTIFICATION_TEXT
from notifier.logic import CooldownGate, should_process_message
from notifier.logging_setup import setup_logging
from notifier.health_server import start_health_server

load_dotenv()
log = setup_logging()

try:
    cfg = load_config()
except ConfigError as e:
    log.error(str(e))
    sys.exit(1)

# Render's Web Service plan expects an open port, or it repeatedly logs
# "No open ports detected" and can eventually fail the health check.
# This bot has no real HTTP work — this just satisfies that port scan.
_health_thread = start_health_server()
log.info("Health check server started.")

gate = CooldownGate(cooldown_seconds=cfg.cooldown)

user_client = TelegramClient(
    StringSession(cfg.string_session),
    cfg.api_id,
    cfg.api_hash,
    connection_retries=None,  # retry forever
    retry_delay=5,
    auto_reconnect=True,
)

bot_client = TelegramClient(
    "bot_session",
    cfg.api_id,
    cfg.api_hash,
    connection_retries=None,
    retry_delay=5,
    auto_reconnect=True,
)


@user_client.on(events.NewMessage(incoming=True))
async def on_new_message(event):
    if not should_process_message(event.is_private, event.out):
        return

    now = asyncio.get_event_loop().time()
    if not gate.should_notify(now):
        return
    gate.mark_sent(now)

    try:
        await bot_client.send_message(cfg.owner_id, NOTIFICATION_TEXT)
        log.info("Notification sent.")
    except Exception as e:
        log.error(f"Failed to send notification: {e}")


async def start_user_client():
    """
    Connects using StringSession ONLY. Never falls back to interactive
    phone/OTP prompts. If the session is invalid, fails fast with a
    clear, actionable error.
    """
    await user_client.connect()

    if not await user_client.is_user_authorized():
        log.error(
            "STRING_SESSION is invalid, expired, or revoked. "
            "This can happen if you logged out all sessions from the "
            "Telegram app, or removed/re-added the account on a device. "
            "Generate a fresh STRING_SESSION with scripts/generate_session.py "
            "and update the STRING_SESSION environment variable."
        )
        raise RuntimeError("invalid_string_session")

    me = await user_client.get_me()
    log.info(f"User client logged in as: {me.first_name} (ID: {me.id})")


async def start_bot_client():
    await bot_client.start(bot_token=cfg.bot_token)
    bot_me = await bot_client.get_me()
    log.info(f"Bot client logged in as: @{bot_me.username}")


async def main():
    while True:
        try:
            await start_user_client()
            await start_bot_client()

            log.info(f"Notifier started. Cooldown = {cfg.cooldown}s")
            await user_client.run_until_disconnected()

        except (
            AuthKeyUnregisteredError,
            AuthKeyDuplicatedError,
            SessionPasswordNeededError,
            SessionRevokedError,
            UserDeactivatedError,
            UserDeactivatedBanError,
        ) as e:
            # Unrecoverable without a new session or account-level fix.
            log.error(f"Fatal session error: {type(e).__name__}: {e}")
            log.error("Fix the underlying issue and redeploy. Exiting.")
            sys.exit(1)

        except RuntimeError as e:
            if str(e) == "invalid_string_session":
                sys.exit(1)
            log.error(f"Runtime error: {e}")
            log.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

        except Exception as e:
            log.error(f"Disconnected: {e}")
            log.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

        finally:
            if user_client.is_connected():
                await user_client.disconnect()
            if bot_client.is_connected():
                await bot_client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Stopped by user.")
