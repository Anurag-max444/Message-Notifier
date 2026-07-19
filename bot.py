import os
import time
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
STRING_SESSION = os.getenv("STRING_SESSION")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

COOLDOWN = int(os.getenv("COOLDOWN", "30"))

last_notification = 0

user = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH
)

bot = TelegramClient(
    "bot_session",
    API_ID,
    API_HASH
)


@user.on(events.NewMessage(incoming=True))
async def new_message(event):
    global last_notification

    # Sirf private chats
    if not event.is_private:
        return

    # Apne hi messages ignore
    if event.out:
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
        print("Notification Sent")
    except Exception as e:
        print("Bot Error:", e)


async def start_clients():
    await user.start()
    await bot.start(bot_token=BOT_TOKEN)

    me = await user.get_me()

    print("=" * 50)
    print(f"Logged in as : {me.first_name}")
    print(f"User ID      : {me.id}")
    print("Notifier Started ✅")
    print("=" * 50)


async def main():
    while True:
        try:
            await start_clients()
            await user.run_until_disconnected()

        except Exception as e:
            print(f"Disconnected : {e}")
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())