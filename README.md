# Telegram Message Notifier

Jab bhi tumhare personal Telegram account par koi naya private message
aaye, ek Bot tumhe generic notification bhejta hai — sender, content,
ya count kabhi reveal nahi hota.

## Setup

### 1. Fresh STRING_SESSION generate karo (sirf local machine par)

```bash
pip install telethon
python generate_session.py
```

Phone number aur OTP maangega — yeh normal hai, sirf isi script mein.
Jo `STRING_SESSION` print hoga usko copy kar lo.

### 2. Render Environment Variables set karo

- `API_ID`
- `API_HASH`
- `STRING_SESSION` (Step 1 se)
- `BOT_TOKEN` (@BotFather se)
- `OWNER_ID` (apna numeric Telegram user ID — @userinfobot se milega)
- `COOLDOWN` (optional, default 30 seconds)

### 3. Deploy

Service type: **Background Worker**
Build command: `pip install -r requirements.txt`
Start command: `python bot.py`

## "Please enter your phone (or bot token)" error ka root cause

Yeh error tab aata hai jab Telethon `StringSession` ko invalid samajhta
hai — expired, revoked, ya galat copy hua (extra space/newline) — aur
purane code mein fallback interactive login trigger ho jata tha. Render
pe koi terminal input nahi hota, isliye turant `EOF` error aake
crash-loop start ho jata tha.

Iss naye `bot.py` mein:
- Session ko `connect()` + `is_user_authorized()` se explicitly verify
  kiya jata hai
- Agar invalid ho, toh turant clear error deke exit hota hai —
  kabhi phone number nahi maangta, kabhi infinite loop nahi karta
- Fix: `generate_session.py` chala ke naya `STRING_SESSION` banao aur
  Render env variable update karo

## Bot "frozen"/limited ho jaye toh

Agar BotFather ki taraf se bot limited/frozen hua hai (spam flag,
report, ya activity spike ki wajah se), yeh code-level issue nahi hai.
Iska fix:
1. `@BotFather` ko `/mybots` bhejo, apna bot select karo, status dekho
2. Agar limited dikhe, toh `@BotSupport` (Telegram ka official support
   bot) ko contact karo aur apna bot username + issue batao

## Files

- `bot.py` — main notifier (production ready)
- `generate_session.py` — one-time local script for fresh StringSession
- `requirements.txt` — dependencies
- `runtime.txt` — Python version pin for Render
- `render.yaml` — optional Render blueprint
- `.env.example` — template for local `.env`
