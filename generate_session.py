"""
Run this ONCE on your LOCAL machine (not on Render) to generate a fresh
STRING_SESSION. This is the only place an interactive phone/OTP prompt
is expected and safe to answer.

Usage:
    python generate_session.py

It will ask for:
- API_ID, API_HASH (from https://my.telegram.org)
- Your phone number
- The login code Telegram sends you
- Your 2FA password (if enabled)

At the end it prints a STRING_SESSION value.
Copy that value into your Render environment variable STRING_SESSION.

NEVER share your STRING_SESSION with anyone — it grants full access
to your Telegram account, same as your password.
"""

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = int(input("Enter your API_ID: ").strip())
API_HASH = input("Enter your API_HASH: ").strip()

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    session_string = client.session.save()
    print("\n" + "=" * 60)
    print("Your STRING_SESSION (copy everything below this line):")
    print("=" * 60)
    print(session_string)
    print("=" * 60)
    print("\nPaste this into Render's STRING_SESSION environment variable.")
