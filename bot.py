import os
import time
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
STRING_SESSION = os.getenv("STRING_SESSION")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

user = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
bot = TelegramClient("bot_session", API_ID, API_HASH)

COOLDOWN = 30
last_notification = 0


@user.on(events.NewMessage(incoming=True))
async def handler(event):
    global last_notification

    # Sirf private chats
    if not event.is_private:
        return

    now = time.time()

    if now - last_notification < COOLDOWN:
        return

    last_notification = now

    try:
        await bot.send_message(
            OWNER_ID,
            "🔔 Session Activated."
        )
    except Exception as e:
        print("Bot Error:", e)


async def main():
    await user.start()
    await bot.start(bot_token=BOT_TOKEN)

    me = await user.get_me()
    print(f"Logged in as: {me.first_name}")
    print("Notifier Started ✅")

    await user.run_until_disconnected()


with user:
    user.loop.run_until_complete(main())