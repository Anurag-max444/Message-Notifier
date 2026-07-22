"""
/vip <id> ["label"]      — add a VIP, optionally tagged with a label
/unvip <id>               — remove VIP status
/viplabel <id> "label"    — relabel an existing VIP (or "off" to clear)
/vipmute <id> <minutes>   — mute just that VIP for X minutes
/vipcooldown <id> <secs>  — give that VIP a custom cooldown instead of full bypass
/vipcooldown <id> off     — restore full bypass (instant, every message)
/vips                     — list every VIP, grouped by label, with inline buttons
"""

import time

from telethon import events, Button

from notifier.commands.common import is_owner, to_thread
from notifier.vip_labels import group_vips_by_label


def register_vip_commands(bot_client, cfg, state):
    @bot_client.on(events.NewMessage(pattern=r'/vip (\d+)(?: "([^"]+)")?$'))
    async def cmd_vip(event):
        if not is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        label = event.pattern_match.group(2)
        await to_thread(state.add_vip, user_id, label)
        suffix = f' tagged as "{label}"' if label else ""
        await event.respond(f"⭐ User {user_id} is now VIP{suffix} — always notifies instantly.")

    @bot_client.on(events.NewMessage(pattern=r"/unvip (\d+)"))
    async def cmd_unvip(event):
        if not is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        await to_thread(state.remove_vip, user_id)
        await event.respond(f"User {user_id} is no longer VIP.")

    @bot_client.on(events.NewMessage(pattern=r'/viplabel (\d+) "([^"]+)"'))
    async def cmd_viplabel(event):
        if not is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        label = event.pattern_match.group(2)
        await to_thread(state.set_vip_label, user_id, label)
        await event.respond(f"🏷 VIP {user_id} labeled as \"{label}\".")

    @bot_client.on(events.NewMessage(pattern=r"/viplabel (\d+) off"))
    async def cmd_viplabel_off(event):
        if not is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        await to_thread(state.set_vip_label, user_id, None)
        await event.respond(f"VIP {user_id}'s label cleared.")

    @bot_client.on(events.NewMessage(pattern=r"/vipmute (\d+) (\d+)"))
    async def cmd_vipmute(event):
        if not is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        minutes = int(event.pattern_match.group(2))
        await to_thread(state.mute_vip_minutes, user_id, minutes)
        await event.respond(f"🔇 VIP user {user_id} muted for {minutes} minute(s).")

    @bot_client.on(events.NewMessage(pattern=r"/vipcooldown (\d+) off"))
    async def cmd_vipcooldown_off(event):
        if not is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        await to_thread(state.set_vip_cooldown_seconds, user_id, None)
        await event.respond(f"⭐ VIP {user_id} back to full bypass — notifies every message instantly.")

    @bot_client.on(events.NewMessage(pattern=r"/vipcooldown (\d+) (\d+)"))
    async def cmd_vipcooldown(event):
        if not is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        seconds = int(event.pattern_match.group(2))
        await to_thread(state.set_vip_cooldown_seconds, user_id, seconds)
        await event.respond(f"⏱ VIP {user_id} now has a {seconds}s cooldown between notifications.")

    @bot_client.on(events.NewMessage(pattern="/vips"))
    async def cmd_vips(event):
        if not is_owner(event, cfg):
            return
        if not state.vip_users:
            await event.respond("Koi VIP user nahi hai.")
            return

        now = time.time()
        for label, user_ids in group_vips_by_label(state.vips).items():
            await event.respond(f"**{label}**")
            for user_id in user_ids:
                info = state.vips[user_id]
                muted = info["muted_until"] > now
                cd = info["cooldown_seconds"]
                cd_label = "instant" if cd is None else f"{cd}s cooldown"
                text = f"⭐ {user_id} ({cd_label})" + (" 🔇 muted" if muted else "")
                buttons = [[
                    Button.inline("🔇 Mute 10m", data=f"vmute_{user_id}_10"),
                    Button.inline("🔇 Mute 60m", data=f"vmute_{user_id}_60"),
                    Button.inline("❌ Remove", data=f"vdel_{user_id}"),
                ]]
                await event.respond(text, buttons=buttons)

    @bot_client.on(events.CallbackQuery(pattern=r"vmute_(\d+)_(\d+)"))
    async def cb_vmute(event):
        if not is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        minutes = int(event.pattern_match.group(2))
        await to_thread(state.mute_vip_minutes, user_id, minutes)
        await event.edit(f"🔇 VIP {user_id} muted for {minutes} minute(s).")

    @bot_client.on(events.CallbackQuery(pattern=r"vdel_(\d+)"))
    async def cb_vdel(event):
        if not is_owner(event, cfg):
            return
        user_id = int(event.pattern_match.group(1))
        await to_thread(state.remove_vip, user_id)
        await event.edit(f"❌ {user_id} removed from VIP.")
