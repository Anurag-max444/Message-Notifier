"""
Central place for the bot's user-facing UI text (welcome message,
unknown-command help, generic headers). Keeping these in one file
means the tone/wording can be changed without hunting through every
command module, and makes future translation easier.

Command-specific descriptions (used by /help and the Telegram menu)
live separately in notifier/commands/command_list.py, since those are
tightly coupled to each command's behavior rather than general UI copy.
"""

WELCOME_MESSAGE = (
    "👋 Namaste! Main tumhara personal message notifier bot hoon.\n\n"
    "Jab bhi tumhare monitored account par koi naya message aaye, main "
    "tumhe yahan alert kar dunga.\n\n"
    "Sab commands dekhne ke liye /help bhejo."
)

HELP_HEADER = "🤖 **Available Commands**"

UNKNOWN_COMMAND_HEADER = "❓ \"{command}\" koi valid command nahi hai."

UNKNOWN_COMMAND_SUGGESTION = "Kya tumhara matlab **/{suggestion}** tha?\n{usage}"

UNKNOWN_COMMAND_FALLBACK = "Yahan sab available commands hain:\n\n{help_text}"

NON_COMMAND_NUDGE = (
    "Commands se control karne ke liye niche di gayi list dekho:\n\n{help_text}"
)

NOT_AUTHORIZED = "Ye bot sirf owner ke liye hai."
