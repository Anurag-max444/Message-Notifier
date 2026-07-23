"""
Telegram Message Notifier — entrypoint.

Jab bhi personal Telegram account (user session) par koi naya
incoming private message aaye (kisi user ya bot se), ek Bot (BOT_TOKEN
wala) OWNER_ID ko generic notification bhejta hai. Sender, content, ya
count kabhi reveal nahi hote. Groups/channels ignore hote hain.

Key properties:
- Kabhi phone number nahi maangta. StringSession invalid/expired/revoked
  hone par turant clear error deta hai aur exit ho jata hai — interactive
  login kabhi trigger nahi hota.
- Sirf incoming private chats process karta hai; groups/channels aur
  apne khud ke bheje messages ignore hote hain.
- Bot ka apna bheja hua notification message dobara khud ko notify
  nahi karta (infinite loop se bachne ke liye).
- Bot ko DM karke control kiya ja sakta hai (sirf OWNER_ID se) —
  puri command list ke liye /help bhejo, ya notifier/commands.py dekho.
  Saari state (cooldown, mute, VIP list) Supabase me persist hoti hai —
  restart/redeploy ke baad bhi yaad rehti hai.
- Disconnect hone par auto-reconnect karta hai (session-revocation jaisi
  unrecoverable errors ko chhodkar, jinke liye naya session chahiye).

Project structure:
    bot.py                     -> yeh file: wiring + main loop only
    notifier/config.py         -> env var loading/validation
    notifier/store.py          -> Supabase persistence layer
    notifier/state.py          -> cooldown/mute/VIP business logic
    notifier/logic.py          -> pure message-filter logic
    notifier/handlers.py       -> user_client message watcher
    notifier/commands.py       -> owner-only bot commands + menu
    notifier/logging_setup.py  -> console + rotating file logging
    notifier/health_server.py  -> Render port-scan health check
"""

import sys
import asyncio

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    AuthKeyUnregisteredError,
    AuthKeyDuplicatedError,
    SessionPasswordNeededError,
    SessionRevokedError,
    UserDeactivatedError,
    UserDeactivatedBanError,
)

from notifier.config import load_config, ConfigError
from notifier.logging_setup import setup_logging
from notifier.health_server import start_health_server
from notifier import store
from notifier.state import NotifyState
from notifier.handlers import register_notify_handler
from notifier.commands import register_commands, register_bot_menu

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

supabase = store.get_client(cfg.supabase_url, cfg.supabase_key)
state = NotifyState.load(supabase)
log.info(
    f"Loaded state from Supabase: cooldown={state.cooldown_seconds}s, "
    f"VIPs={sorted(state.vip_users)}"
)

# Populated once bot_client logs in (see start_bot_client); shared with
# handlers.py so it can ignore the bot's own outgoing notifications.
bot_identity = {"id": None}

register_notify_handler(user_client, bot_client, cfg, state, log, bot_identity)
register_commands(bot_client, cfg, state, log)


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

    # HIDDEN BUG FIX: Telethon needs each chat's access_hash cached to
    # correctly build events for groups/channels (and to resolve sender
    # entities for /reveal). Without this, group/channel messages can be
    # silently dropped and event.get_sender() can fail for them — which
    # is exactly why /groups and /reveal appeared broken. Calling
    # get_dialogs() once after login warms that cache for every chat
    # the account is a member of.
    dialogs = await user_client.get_dialogs()
    log.info(f"Cached {len(dialogs)} dialog(s) for group/channel event resolution.")


async def start_bot_client():
    await bot_client.start(bot_token=cfg.bot_token)
    bot_me = await bot_client.get_me()
    bot_identity["id"] = bot_me.id
    await register_bot_menu(bot_client)
    log.info(f"Bot client logged in as: @{bot_me.username}")


async def main():
    while True:
        try:
            await start_user_client()
            await start_bot_client()

            log.info("Notifier started.")
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
