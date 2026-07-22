"""
Owner-only control commands for the notifier bot. DM the bot itself
(@your_bot_username) to use these — anyone not in cfg.control_owner_ids
is silently ignored.

Split into one file per feature area:
    command_list.py           -> COMMAND_LIST, the single source of truth
    common.py                  -> is_owner / to_thread / fmt_seconds helpers
    mute_commands.py           -> /skip, /resume, /cooldown
    groups_commands.py         -> /groups, /allowchat, /disallowchat, /allowedchats
    reveal_commands.py         -> /reveal
    quiethours_commands.py     -> /quiethours
    vip_commands.py            -> /vip, /unvip, /viplabel, /vipmute, /vipcooldown, /vips
    status_commands.py         -> /help, /status, /mutelist
"""

from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault

from notifier.commands.command_list import COMMAND_LIST
from notifier.commands.mute_commands import register_mute_commands
from notifier.commands.groups_commands import register_groups_commands
from notifier.commands.reveal_commands import register_reveal_commands
from notifier.commands.quiethours_commands import register_quiethours_commands
from notifier.commands.vip_commands import register_vip_commands
from notifier.commands.status_commands import register_status_commands, help_text

__all__ = ["COMMAND_LIST", "register_commands", "register_bot_menu", "help_text"]


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
    register_status_commands(bot_client, cfg, state)
    register_mute_commands(bot_client, cfg, state)
    register_groups_commands(bot_client, cfg, state)
    register_reveal_commands(bot_client, cfg, state)
    register_quiethours_commands(bot_client, cfg, state)
    register_vip_commands(bot_client, cfg, state)
