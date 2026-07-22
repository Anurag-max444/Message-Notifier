"""
COMMAND_LIST is the single source of truth for command names +
descriptions: it drives /help text AND the Telegram "/" quick-command
menu, so the two can never drift apart.
"""

COMMAND_LIST = [
    ("help", "Sabhi commands ki list dikhaye"),
    ("status", "Current cooldown, mute aur VIP status dikhaye"),
    ("skip", "Sab normal notifications kuch der ke liye mute karo"),
    ("resume", "Active mute turant hata do"),
    ("cooldown", "Normal users ke notify ke beech ka gap set karo (minutes)"),
    ("groups", "Group/channel messages ka notify on/off karo"),
    ("allowchat", "Sirf specific group/channel se notify karo (allow-list)"),
    ("disallowchat", "Ek chat ko allow-list se hatao"),
    ("allowedchats", "Allow-list me jo chats hain unki list dikhaye"),
    ("reveal", "Notification me sender ka naam dikhana on/off karo"),
    ("quiethours", "Roz ek fixed time window me auto-mute set karo"),
    ("mutelist", "Global mute + har VIP ka mute status, remaining time ke saath"),
    ("vip", "Kisi user ko VIP banao (optional label ke saath)"),
    ("unvip", "VIP status hatao"),
    ("viplabel", "Kisi existing VIP ka label badlo ya hatao"),
    ("vips", "Sabhi VIP users ki list, label ke hisaab se grouped"),
    ("vipmute", "Ek VIP user ko X minute ke liye mute karo"),
    ("vipcooldown", "VIP ko full-bypass ki jagah apna khud ka cooldown do"),
]
