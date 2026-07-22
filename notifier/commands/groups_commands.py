"""
/groups           — global on/off toggle for group & channel notifications
/allowchat        — narrow it down to specific chats (empty list = all allowed)
/disallowchat     — remove a chat from the allow-list
/allowedchats     — list the current allow-list, with remove buttons
"""

from telethon import events, Button

from notifier.commands.common import is_owner, to_thread


def register_groups_commands(bot_client, cfg, state):
    @bot_client.on(events.NewMessage(pattern="/groups$"))
    async def cmd_groups(event):
        if not is_owner(event, cfg):
            return
        buttons = [[
            Button.inline("✅ On", data="groups_on"),
            Button.inline("❌ Off", data="groups_off"),
        ]]
        current = "on" if state.allow_groups else "off"
        await event.respond(f"Group/channel notifications abhi **{current}** hain. Badlo?", buttons=buttons)

    @bot_client.on(events.CallbackQuery(pattern=r"groups_(on|off)"))
    async def cb_groups(event):
        if not is_owner(event, cfg):
            return
        allow = event.pattern_match.group(1) == "on"
        await to_thread(state.set_allow_groups, allow)
        await event.edit(f"Group/channel notifications ab **{'on' if allow else 'off'}** hain.")

    @bot_client.on(events.NewMessage(pattern=r'/allowchat (-?\d+)(?: "([^"]+)")?$'))
    async def cmd_allowchat(event):
        if not is_owner(event, cfg):
            return
        chat_id = int(event.pattern_match.group(1))
        label = event.pattern_match.group(2)
        await to_thread(state.add_allowed_chat, chat_id, label)
        suffix = f' ("{label}")' if label else ""
        await event.respond(f"✅ Chat {chat_id}{suffix} added to the allow-list.")

    @bot_client.on(events.NewMessage(pattern=r"/disallowchat (-?\d+)"))
    async def cmd_disallowchat(event):
        if not is_owner(event, cfg):
            return
        chat_id = int(event.pattern_match.group(1))
        await to_thread(state.remove_allowed_chat, chat_id)
        await event.respond(f"Chat {chat_id} removed from the allow-list.")

    @bot_client.on(events.NewMessage(pattern="/allowedchats"))
    async def cmd_allowedchats(event):
        if not is_owner(event, cfg):
            return
        if not state.allowed_chats:
            await event.respond(
                "Allow-list khaali hai — jab /groups on ho, to **sab** groups/channels notify karte hain.\n"
                'Kisi specific chat tak seemit karne ke liye: `/allowchat <chat_id> "Label"`'
            )
            return
        for chat_id, label in sorted(state.allowed_chats.items()):
            text = f"💬 {chat_id}" + (f" — {label}" if label else "")
            buttons = [[Button.inline("❌ Remove", data=f"chatdel_{chat_id}")]]
            await event.respond(text, buttons=buttons)

    @bot_client.on(events.CallbackQuery(pattern=r"chatdel_(-?\d+)"))
    async def cb_chatdel(event):
        if not is_owner(event, cfg):
            return
        chat_id = int(event.pattern_match.group(1))
        await to_thread(state.remove_allowed_chat, chat_id)
        await event.edit(f"❌ Chat {chat_id} removed from the allow-list.")
