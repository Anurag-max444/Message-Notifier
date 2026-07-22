"""/reveal — on/off toggle for including the sender's name in notifications."""

from telethon import events, Button

from notifier.commands.common import is_owner, to_thread


def register_reveal_commands(bot_client, cfg, state):
    @bot_client.on(events.NewMessage(pattern="/reveal$"))
    async def cmd_reveal(event):
        if not is_owner(event, cfg):
            return
        buttons = [[
            Button.inline("✅ On", data="reveal_on"),
            Button.inline("❌ Off", data="reveal_off"),
        ]]
        current = "on" if state.reveal_sender else "off"
        await event.respond(
            f"Sender ka naam notification me dikhana abhi **{current}** hai. Badlo?", buttons=buttons
        )

    @bot_client.on(events.CallbackQuery(pattern=r"reveal_(on|off)"))
    async def cb_reveal(event):
        if not is_owner(event, cfg):
            return
        reveal = event.pattern_match.group(1) == "on"
        await to_thread(state.set_reveal_sender, reveal)
        await event.edit(f"Sender reveal ab **{'on' if reveal else 'off'}** hai.")
