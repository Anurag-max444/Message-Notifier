"""/quiethours — sets or clears a daily auto-mute window (e.g. 23:00-07:00)."""

import re

from telethon import events

from notifier.commands.common import is_owner, to_thread

_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def register_quiethours_commands(bot_client, cfg, state):
    @bot_client.on(events.NewMessage(pattern=r"/quiethours off"))
    async def cmd_quiethours_off(event):
        if not is_owner(event, cfg):
            return
        await to_thread(state.clear_quiet_hours)
        await event.respond("🔔 Quiet hours cleared.")

    @bot_client.on(events.NewMessage(pattern=r"/quiethours (\S+) (\S+)"))
    async def cmd_quiethours(event):
        if not is_owner(event, cfg):
            return
        start, end = event.pattern_match.group(1), event.pattern_match.group(2)
        if not (_HHMM.match(start) and _HHMM.match(end)):
            await event.respond("Format: `/quiethours 23:00 07:00` (24-hour HH:MM).")
            return
        await to_thread(state.set_quiet_hours, start, end)
        await event.respond(f"🌙 Quiet hours set: {start} – {end} daily.")
