"""
/start                — friendly welcome message
Catch-all handler     — runs on every message the owner sends:
    - If it's a valid command, does nothing (a specific handler already
      replies to it).
    - If it's an unrecognized command (e.g. a typo), suggests the
      closest match using difflib, showing that command's usage line.
    - If it's not a command at all, nudges the owner towards /help by
      showing the full command list.
"""

import re
import difflib

from telethon import events

from notifier.commands.common import is_owner
from notifier.commands.command_list import COMMAND_LIST
from notifier.commands.status_commands import help_text
from notifier.lang import (
    WELCOME_MESSAGE,
    UNKNOWN_COMMAND_HEADER,
    UNKNOWN_COMMAND_SUGGESTION,
    UNKNOWN_COMMAND_FALLBACK,
    NON_COMMAND_NUDGE,
)

_COMMAND_WORD = re.compile(r"^/(\w+)")
_EXTRA_KNOWN_COMMANDS = {"start"}  # not in COMMAND_LIST (it's a Telegram convention, not a control command)
_USAGE_BY_COMMAND = dict(COMMAND_LIST)
_KNOWN_COMMANDS = set(_USAGE_BY_COMMAND) | _EXTRA_KNOWN_COMMANDS


def _closest_command_usage(command: str):
    """Returns (suggested_command, usage_line) or (None, None) if nothing is close enough."""
    matches = difflib.get_close_matches(command, _KNOWN_COMMANDS, n=1, cutoff=0.5)
    if not matches:
        return None, None
    suggestion = matches[0]
    desc = _USAGE_BY_COMMAND.get(suggestion)
    usage = f"/{suggestion} - {desc}" if desc else f"/{suggestion}"
    return suggestion, usage


def register_fallback_commands(bot_client, cfg):
    @bot_client.on(events.NewMessage(pattern="/start"))
    async def cmd_start(event):
        if not is_owner(event, cfg):
            return
        await event.respond(WELCOME_MESSAGE)

    @bot_client.on(events.NewMessage())
    async def catch_all(event):
        if not is_owner(event, cfg):
            return

        text = (event.raw_text or "").strip()
        match = _COMMAND_WORD.match(text)

        if not match:
            await event.respond(NON_COMMAND_NUDGE.format(help_text=help_text()))
            return

        command = match.group(1).lower()
        if command in _KNOWN_COMMANDS:
            return  # a specific handler already handles this one

        header = UNKNOWN_COMMAND_HEADER.format(command=command)
        suggestion, usage = _closest_command_usage(command)
        if suggestion:
            body = UNKNOWN_COMMAND_SUGGESTION.format(suggestion=suggestion, usage=usage)
        else:
            body = UNKNOWN_COMMAND_FALLBACK.format(help_text=help_text())
        await event.respond(f"{header}\n{body}")
