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
- Bot ka apna bheja hua notification message dobara khud ko notify
  nahi karta (infinite loop se bachne ke liye).
- Bot ko DM karke control kiya ja sakta hai (sirf OWNER_ID se):
    /skip                    -> button se duration choose karke sab
                                 notifications temporarily mute karo
    /cooldown <minutes>      -> normal users ke liye gap set karo
    /vip <user_id>           -> is user ka har message turant notify
                                 karega, mute/cooldown ignore karke
    /unvip <user_id>         -> VIP status hatao
    /vipmute <user_id> <min> -> sirf is VIP user ko X minute mute karo
  Saari state (cooldown, mute, VIP list) Supabase me persist hoti hai —
  restart/redeploy ke baad bhi yaad rehti hai.
- Disconnect hone par auto-reconnect karta hai (session-revocation jaisi
  unrecoverable errors ko chhodkar, jinke liye naya session chahiye).
"""

import sys
import time
import asyncio

from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
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
from notifier.logic import should_process_message
from notifier.logging_setup import setup_logging
from notifier.health_server import start_health_server
from notifier import store

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


_bot_user_id = None  # set once bot_client logs in; used to ignore our own notifications

supabase = store.get_client(cfg.supabase_url, cfg.supabase_key)

# --- Runtime-controllable notification state (loaded from Supabase, then
# kept in memory for fast per-message checks; every change is written
# through to Supabase immediately so it survives restarts/redeploys) ---
_state = store.load_state(supabase)
cooldown_seconds = _state["cooldown_seconds"]
global_mute_until = _state["global_mute_until"]
last_notify_time = 0.0
vip_mute_until = store.load_vips(supabase)  # {user_id: muted_until}
vip_users = set(vip_mute_until.keys())
log.info(f"Loaded state from Supabase: cooldown={cooldown_seconds}s, VIPs={sorted(vip_users)}")

_SKIP_OPTIONS = [1, 5, 10, 20, 60]  # minutes


def _is_owner(event) -> bool:
    return event.sender_id == cfg.owner_id


@user_client.on(events.NewMessage())
async def on_new_message(event):
    if not should_process_message(event.is_private, event.out):
        return

    # Without this check, the notification we send below would itself
    # arrive as a new incoming message on the monitored account, causing
    # an infinite notify-loop (bot -> notification -> triggers itself -> ...).
    if _bot_user_id is not None and event.sender_id == _bot_user_id:
        return

    global last_notify_time
    now = time.time()
    sender = event.sender_id

    if sender in vip_users:
        # VIP users bypass global mute and cooldown entirely — every
        # single message notifies, no matter how many or how soon.
        if vip_mute_until.get(sender, 0) > now:
            return
    else:
        if now < global_mute_until:
            return
        if now - last_notify_time < cooldown_seconds:
            return
        last_notify_time = now

    try:
        await bot_client.send_message(cfg.owner_id, NOTIFICATION_TEXT)
        log.info("Notification sent.")
    except Exception as e:
        log.error(f"Failed to send notification: {e}")


# --- Owner-only control commands (sent by DMing the bot itself) ---

@bot_client.on(events.NewMessage(pattern="/skip"))
async def cmd_skip(event):
    if not _is_owner(event):
        return
    buttons = [
        [Button.inline(f"{m} min", data=f"skip_{m}") for m in _SKIP_OPTIONS[:3]],
        [Button.inline(f"{m} min", data=f"skip_{m}") for m in _SKIP_OPTIONS[3:]],
    ]
    await event.respond("Kitne minute ke liye mute karna hai?", buttons=buttons)


@bot_client.on(events.CallbackQuery(pattern=r"skip_(\d+)"))
async def cb_skip(event):
    if not _is_owner(event):
        return
    global global_mute_until
    minutes = int(event.pattern_match.group(1))
    global_mute_until = time.time() + minutes * 60
    await asyncio.to_thread(store.save_global_mute, supabase, int(global_mute_until))
    await event.edit(f"🔇 Muted for {minutes} minute(s).")


@bot_client.on(events.NewMessage(pattern=r"/cooldown (\d+)"))
async def cmd_cooldown(event):
    if not _is_owner(event):
        return
    global cooldown_seconds
    minutes = int(event.pattern_match.group(1))
    cooldown_seconds = minutes * 60
    await asyncio.to_thread(store.save_cooldown, supabase, cooldown_seconds)
    await event.respond(f"✅ Cooldown set to {minutes} minute(s).")


@bot_client.on(events.NewMessage(pattern=r"/vip (\d+)"))
async def cmd_vip(event):
    if not _is_owner(event):
        return
    user_id = int(event.pattern_match.group(1))
    vip_users.add(user_id)
    vip_mute_until.setdefault(user_id, 0)
    await asyncio.to_thread(store.add_vip, supabase, user_id)
    await event.respond(f"⭐ User {user_id} is now VIP — always notifies instantly.")


@bot_client.on(events.NewMessage(pattern=r"/unvip (\d+)"))
async def cmd_unvip(event):
    if not _is_owner(event):
        return
    user_id = int(event.pattern_match.group(1))
    vip_users.discard(user_id)
    vip_mute_until.pop(user_id, None)
    await asyncio.to_thread(store.remove_vip, supabase, user_id)
    await event.respond(f"User {user_id} is no longer VIP.")


@bot_client.on(events.NewMessage(pattern=r"/vipmute (\d+) (\d+)"))
async def cmd_vipmute(event):
    if not _is_owner(event):
        return
    user_id = int(event.pattern_match.group(1))
    minutes = int(event.pattern_match.group(2))
    until_ts = int(time.time() + minutes * 60)
    vip_mute_until[user_id] = until_ts
    await asyncio.to_thread(store.set_vip_mute, supabase, user_id, until_ts)
    await event.respond(f"🔇 VIP user {user_id} muted for {minutes} minute(s).")


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
    global _bot_user_id
    await bot_client.start(bot_token=cfg.bot_token)
    bot_me = await bot_client.get_me()
    _bot_user_id = bot_me.id
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
