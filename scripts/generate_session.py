"""
Run this ONCE on your LOCAL machine (never on Render) to generate a
fresh STRING_SESSION.

Saare inputs .env se aate hain — API_ID, API_HASH, PHONE_NUMBER.
Sirf Telegram ka login CODE (OTP) aur, agar 2FA on hai, tumhara
2FA password interactively poocha jayega — yeh unavoidable hai,
Telegram khud yeh values kahin store nahi karne deta.

Usage:
    cd scripts
    python generate_session.py

Required in .env (project root):
    API_ID=...
    API_HASH=...
    PHONE_NUMBER=+91XXXXXXXXXX
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

from notifier.config import load_config, ConfigError

load_dotenv()

try:
    cfg = load_config(require_phone=True)
except ConfigError as e:
    print(f"Config error: {e}")
    print("Make sure API_ID, API_HASH, and PHONE_NUMBER are set in your .env file.")
    sys.exit(1)

print(f"Generating session for phone number: {cfg.phone_number}")
print("Telegram will send a login code to that number/account.\n")

with TelegramClient(StringSession(), cfg.api_id, cfg.api_hash) as client:
    client.start(phone=cfg.phone_number)
    session_string = client.session.save()

    print("\n" + "=" * 60)
    print("Your STRING_SESSION (copy everything below this line):")
    print("=" * 60)
    print(session_string)
    print("=" * 60)
    print("\nPaste this into Render's STRING_SESSION environment variable.")
    print("NEVER share this value — it grants full access to your account.")
