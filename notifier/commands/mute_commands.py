"""/skip, /resume, /cooldown — global mute and cooldown controls."""

from telethon import events, Button

from notifier.commands.common import is_owner, to_thread

MUTE_OPTIONS = [1, 5, 10, 20, 60]  # minutes, used by /skip's inline buttons


def register_mute_commands(bot_client, cfg, state):
    @bot_client.on(events.NewMessage(pattern="/skip$"))
    async def cmd_skip(event):
        if not is_owner(event, cfg):
            return
        buttons = [
            [Button.inline(f"{m} min", data=f"skip_{m}") for m in MUTE_OPTIONS[:3]],
            [Button.inline(f"{m} min", data=f"skip_{m}") for m in MUTE_OPTIONS[3:]],
        ]
        await event.respond("Kitne minute ke liye mute karna hai?", buttons=buttons)

    @bot_client.on(events.CallbackQuery(pattern=r"skip_(\d+)"))
    async def cb_skip(event):
        if not is_owner(event, cfg):
            return
        minutes = int(event.pattern_match.group(1))
        await to_thread(state.mute_all_minutes, minutes)
        await event.edit(f"🔇 Muted for {minutes} minute(s).")

    @bot_client.on(events.NewMessage(pattern="/resume"))
    async def cmd_resume(event):
        if not is_owner(event, cfg):
            return
        await to_thread(state.resume)
        await event.respond("🔔 Mute cleared — notifications resumed.")

    @bot_client.on(events.NewMessage(pattern=r"/cooldown (\d+)"))
    async def cmd_cooldown(event):
        if not is_owner(event, cfg):
            return
        minutes = int(event.pattern_match.group(1))
        await to_thread(state.set_cooldown_minutes, minutes)
        await event.respond(f"✅ Cooldown set to {minutes} minute(s).")
