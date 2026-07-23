"""/help, /status, /mutelist — read-only overviews of current settings."""

import time

from telethon import events

from notifier.commands.common import is_owner, fmt_seconds
from notifier.commands.command_list import COMMAND_LIST
from notifier.lang import HELP_HEADER


def help_text() -> str:
    lines = [f"/{cmd} - {desc}" for cmd, desc in COMMAND_LIST]
    return f"{HELP_HEADER}\n\n" + "\n".join(lines)


def register_status_commands(bot_client, cfg, state):
    @bot_client.on(events.NewMessage(pattern="/help"))
    async def cmd_help(event):
        if not is_owner(event, cfg):
            return
        await event.respond(help_text())

    @bot_client.on(events.NewMessage(pattern="/status"))
    async def cmd_status(event):
        if not is_owner(event, cfg):
            return
        now = time.time()
        mute_left = max(0, int(state.global_mute_until - now))
        quiet = f"{state.quiet_start}\u2013{state.quiet_end}" if state.has_quiet_hours() else "off"
        allowlist_note = (
            f", {len(state.allowed_chats)} chat(s) allow-listed" if state.allowed_chats else ""
        )
        lines = [
            "📊 **Status**",
            f"Cooldown: {state.cooldown_seconds // 60} min",
            f"Global mute: {'active, ' + fmt_seconds(mute_left) + ' left' if mute_left else 'off'}",
            f"Groups/channels: {'on' if state.allow_groups else 'off'}{allowlist_note}",
            f"Reveal sender: {'on' if state.reveal_sender else 'off'}",
            f"Quiet hours: {quiet}" + (" (active now)" if state.is_quiet_now(now) else ""),
            f"VIP users: {len(state.vip_users)}",
            "",
            "Use /mutelist for a detailed per-VIP breakdown.",
        ]
        await event.respond("\n".join(lines))

    @bot_client.on(events.NewMessage(pattern="/mutelist"))
    async def cmd_mutelist(event):
        if not is_owner(event, cfg):
            return
        now = time.time()
        lines = ["🔇 **Mute Overview**", ""]

        global_left = state.global_mute_until - now
        lines.append(
            f"Global: active, {fmt_seconds(global_left)} left" if global_left > 0 else "Global: not muted"
        )

        if state.has_quiet_hours():
            lines.append(
                f"Quiet hours: {state.quiet_start}\u2013{state.quiet_end}"
                + (" (active now)" if state.is_quiet_now(now) else "")
            )

        vip_lines = []
        for user_id in sorted(state.vip_users):
            left = state.vips[user_id]["muted_until"] - now
            if left > 0:
                vip_lines.append(f"  VIP {user_id}: muted, {fmt_seconds(left)} left")
        if vip_lines:
            lines.append("")
            lines.append("VIP mutes:")
            lines.extend(vip_lines)
        elif state.vip_users:
            lines.append("")
            lines.append("No individual VIP mutes active.")

        await event.respond("\n".join(lines))
