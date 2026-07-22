"""
Owner-only control commands for the notifier bot. DM the bot itself
(@your_bot_username) to use these — anyone other than OWNER_ID is
silently ignored.

COMMAND_LIST is the single source of truth for command names +
descriptions: it drives /help text AND the Telegram "/" quick-command
menu (see register_bot_menu below), so the two can never drift apart.
"""

import asyncio
import time

from telethon import events, Button
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault

MUTE_OPTIONS = [1, 5, 10, 20, 60]  # minutes, used by /skip's inline buttons

COMMAND_LIST = [
    ("help", "Sabhi commands ki list dikhaye"),
    ("status", "Current cooldown, mute aur VIP status dikhaye"),
    ("skip", "Sab normal notifications kuch der ke liye mute karo"),
    ("resume", "Active mute turant hata do"),
    ("cooldown", "Normal users ke notify ke beech ka gap set karo (minutes)"),
    ("vip", "Kisi user ko VIP banao — hamesha turant notify karega"),
    ("unvip", "VIP status hatao"),
    ("vips", "Sabhi VIP users ki list, mute/remove buttons ke saath"),
    ("vipmute", "Ek VIP user ko X minute ke liye mute karo"),
]


def _help_text() -> str:
    lines = [f"/{cmd} - {desc}" for cmd, desc in COMMAND_LIST]
    return "🤖 **Available Commands**\n\n" + "\n".join(lines)


def _is_owner(event, cfg) -> bool:
    return event.sender_id == cfg.owner_id


async def register_bot_menu(bot_client) -> None:
    """
    Pushes COMMAND_LIST to Telegram's official bot command menu — the
    list that pops up when the owner taps "/" in the chat with the bot.
    """
    commands = [BotCommand(cmd, desc) for cmd, desc in COMMAND_LIST]
    await bot_client(SetBotCommandsRequest(
        scope=BotCommandScopeDefault(), lang_code="", commands=commands
    ))


def register_commands(bot_client, cfg, state, log):
    """Registers every owner-only command + callback handler on bot_client."""

    @bot_client.on(events.NewMessage(pattern="/help"))
    async def cmd_help(event):
        if not _is_owner(event, cfg):
            return
        await event.respond(_help_text())

    @bot_client.on(events.NewMessage(pattern="/status"))
    async def cmd_status(event):
        if not _is_owner(event, cfg):
            return
        now = time.time()
        mute_left = max(0, int(state.global_mute_until - now))
        vip_count = len(state.vip_users)
        lines = [
            "📊 **Status**",
            f"Cooldown: {state.cooldown_seconds // 60} min",
            f"Global mute: {'active, ' + str(mute_left) + 's left' if mute_left else 'off'}",
            f"VIP users: {vip_count}",
        ]
        await event.respond("\n".join(lines))

    @bot_client.on(events.NewMessage(pattern="/skip$"))
    async def cmd_skip(event):
        if not _is_owner(event, cfg):
            return
        buttons = [
            [Button.inline(f"{m} min", data=f"skip_{m}") for m in MUTE_OPTIONS[:3]],
            [Button.inline(f"{m} min", data=f"skip_{m}") for m in MUTE_OPTIONS[3:]],
        ]
        await event.respond("Kitne minute ke liye mute karna hai?", buttons=buttons)

    @bot_client.on(events.CallbackQuery(pattern=r"skip_(\d+)"))
    async def cb_skip(event):
        if not _is_owner(event, cfg):
            return
        minutes = int(event.pattern_match.group(1))
        await _to_thread(state.mute_all_minutes, minutes)
        await event.edit(f"🔇 Muted for {minutes} minute(s).")

    @bot_client.on(events.NewMessage(pattern="/resume"))
    async def cmd_resume(event):
        if not _is_owner(event, cfg):
            return
        await _to_thread(state.resume)
        await event.respond("🔔 Mute cleared — notifications resumed.")

    @bot_client.on(events.NewMessage(pattern=r"/cooldown (\d+)"))
    async def cmd_cooldown(event):
        if not _is_owner(event, cfg):
            return
        minutes = int(event.pattern_match.group(1))
        await _to_thread(state.set_cooldown_minutes, minutes)
        await event.respond(f"✅ Cooldown set to {minutes} minute(s).")

    @bot_client.on(events.NewMessage(pattern=r"/vip (\d+)"))
    async def cmd_vip(event):
        if not _is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        await _to_thread(state.add_vip, user_id)
        await event.respond(f"⭐ User {user_id} is now VIP — always notifies instantly.")

    @bot_client.on(events.NewMessage(pattern=r"/unvip (\d+)"))
    async def cmd_unvip(event):
        if not _is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        await _to_thread(state.remove_vip, user_id)
        await event.respond(f"User {user_id} is no longer VIP.")

    @bot_client.on(events.NewMessage(pattern=r"/vipmute (\d+) (\d+)"))
    async def cmd_vipmute(event):
        if not _is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        minutes = int(event.pattern_match.group(2))
        await _to_thread(state.mute_vip_minutes, user_id, minutes)
        await event.respond(f"🔇 VIP user {user_id} muted for {minutes} minute(s).")

    @bot_client.on(events.NewMessage(pattern="/vips"))
    async def cmd_vips(event):
        if not _is_owner(event, cfg):
            return
        if not state.vip_users:
            await event.respond("Koi VIP user nahi hai.")
            return
        for user_id in sorted(state.vip_users):
            muted_until = state.vip_mute_until.get(user_id, 0)
            muted = muted_until > time.time()
            label = f"⭐ {user_id}" + (" (muted)" if muted else "")
            buttons = [[
                Button.inline("🔇 Mute 10m", data=f"vmute_{user_id}_10"),
                Button.inline("🔇 Mute 60m", data=f"vmute_{user_id}_60"),
                Button.inline("❌ Remove", data=f"vdel_{user_id}"),
            ]]
            await event.respond(label, buttons=buttons)

    @bot_client.on(events.CallbackQuery(pattern=r"vmute_(\d+)_(\d+)"))
    async def cb_vmute(event):
        if not _is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        minutes = int(event.pattern_match.group(2))
        await _to_thread(state.mute_vip_minutes, user_id, minutes)
        await event.edit(f"🔇 VIP {user_id} muted for {minutes} minute(s).")

    @bot_client.on(events.CallbackQuery(pattern=r"vdel_(\d+)"))
    async def cb_vdel(event):
        if not _is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        await _to_thread(state.remove_vip, user_id)
        await event.edit(f"❌ {user_id} removed from VIP.")


async def _to_thread(func, *args):
    """Small wrapper so command handlers stay readable above."""
    return await asyncio.to_thread(func, *args)
