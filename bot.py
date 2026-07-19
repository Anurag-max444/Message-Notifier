"""
Telegram Message Notifier
--------------------------
Jab bhi personal Telegram account (user session) par koi naya
private message aaye, ek Bot (BOT_TOKEN wala) OWNER_ID ko generic
notification bhejta hai.

- Kabhi phone number nahi maangta (StringSession invalid hone par
  turant clear error deta hai, interactive login kabhi nahi maangta)
- Sirf private incoming messages, groups/channels ignore
- Outgoing messages ignore
- Cooldown support (spam se bachne ke liye)
- Auto reconnect on disconnect
- Full exception logging
"""

import os
import sys
import time
import asyncio
import logging

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

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("tg-notifier")

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        log.error(f"Missing required environment variable: {name}")
        sys.exit(1)
    return value.strip()


API_ID_RAW = _require_env("API_ID")
API_HASH = _require_env("API_HASH")
STRING_SESSION = _require_env("STRING_SESSION")
BOT_TOKEN = _require_env("BOT_TOKEN")
OWNER_ID_RAW = _require_env("OWNER_ID")
COOLDOWN = int(os.getenv("COOLDOWN", "30"))

try:
    API_ID = int(API_ID_RAW)
except ValueError:
    log.error("API_ID must be an integer.")
    sys.exit(1)

try:
    OWNER_ID = int(OWNER_ID_RAW)
except ValueError:
    log.error("OWNER_ID must be an integer.")
    sys.exit(1)

NOTIFICATION_TEXT = "🔔 New message received on your Telegram account."

last_notification = 0.0

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
# User client: uses the existing StringSession (your personal account).
# connection_retries / retry_delay control auto-reconnect behaviour.
user_client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
    connection_retries=None,   # retry forever
    retry_delay=5,
    auto_reconnect=True,
)

# Bot client: sends the actual notification message.
bot_client = TelegramClient(
    "bot_session",
    API_ID,
    API_HASH,
    connection_retries=None,
    retry_delay=5,
    auto_reconnect=True,
)


# ---------------------------------------------------------------------------
# Event handler
# ---------------------------------------------------------------------------
@user_client.on(events.NewMessage(incoming=True))
async def on_new_message(event):
    global last_notification

    # Ignore groups/channels — only 1:1 private chats
    if not event.is_private:
        return

    # Ignore messages sent by yourself
    if event.out:
        return

    now = time.time()
    if now - last_notification < COOLDOWN:
        return
    last_notification = now

    try:
        await bot_client.send_message(OWNER_ID, NOTIFICATION_TEXT)
        log.info("Notification sent.")
    except Exception as e:
        log.error(f"Failed to send notification: {e}")


# ---------------------------------------------------------------------------
# Startup / session validation
# ---------------------------------------------------------------------------
async def start_user_client():
    """
    Connects the user client using StringSession ONLY.
    Never falls back to interactive phone/OTP prompts.
    If the session is invalid/expired/revoked, fails fast with a clear error
    instead of looping forever asking for a phone number.
    """
    await user_client.connect()

    if not await user_client.is_user_authorized():
        log.error(
            "STRING_SESSION is invalid, expired, or revoked. "
            "Telethon would normally ask for a phone number here — "
            "this script refuses to do that. "
            "Generate a fresh STRING_SESSION locally (see generate_session.py) "
            "and update the STRING_SESSION environment variable."
        )
        raise RuntimeError("Invalid STRING_SESSION")

    me = await user_client.get_me()
    log.info(f"User client logged in as: {me.first_name} (ID: {me.id})")


async def start_bot_client():
    await bot_client.start(bot_token=BOT_TOKEN)
    bot_me = await bot_client.get_me()
    log.info(f"Bot client logged in as: @{bot_me.username}")


# ---------------------------------------------------------------------------
# Main loop with auto-reconnect
# ---------------------------------------------------------------------------
async def main():
    while True:
        try:
            await start_user_client()
            await start_bot_client()

            log.info(f"Notifier started. Cooldown = {COOLDOWN}s")
            await user_client.run_until_disconnected()

        except (
            AuthKeyUnregisteredError,
            AuthKeyDuplicatedError,
            SessionPasswordNeededError,
            SessionRevokedError,
            UserDeactivatedError,
            UserDeactivatedBanError,
        ) as e:
            # These are unrecoverable without generating a new session
            # or resolving an account issue. Do not loop forever.
            log.error(f"Fatal session error: {type(e).__name__}: {e}")
            log.error("Fix the underlying issue and redeploy. Exiting.")
            sys.exit(1)

        except RuntimeError as e:
            if str(e) == "Invalid STRING_SESSION":
                sys.exit(1)
            log.error(f"Runtime error: {e}")
            log.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

        except Exception as e:
            log.error(f"Disconnected: {e}")
            log.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

        finally:
            # Ensure clean disconnect before retry loop reconnects
            if user_client.is_connected():
                await user_client.disconnect()
            if bot_client.is_connected():
                await bot_client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Stopped by user.")
