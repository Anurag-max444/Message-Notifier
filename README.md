# Telegram Message Notifier

Jab bhi tumhare personal Telegram account par koi naya private message
aaye, ek Bot tumhe generic notification bhejta hai — sender, content,
ya count kabhi reveal nahi hote.

## Project Structure

```
.
├── bot.py                      # Main entrypoint — run this in production
├── notifier/
│   ├── __init__.py
│   ├── config.py                # Loads + validates all env vars (testable)
│   ├── logic.py                  # Cooldown gate + message filter (pure, testable)
│   └── logging_setup.py          # Logging config
├── scripts/
│   └── generate_session.py       # One-time local script to create STRING_SESSION
├── tests/
│   ├── test_config.py
│   └── test_logic.py
├── requirements.txt
├── requirements-dev.txt          # adds pytest
├── runtime.txt                   # Python version for Render
├── render.yaml
├── pytest.ini
├── .env.example
└── .gitignore
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements-dev.txt
```

### 2. Create your `.env`

```bash
cp .env.example .env
```

Fill in `API_ID`, `API_HASH`, `PHONE_NUMBER`, and `OWNER_ID`.
`STRING_SESSION` and `BOT_TOKEN` come after the next step.

### 3. Generate STRING_SESSION (local machine only)

```bash
python scripts/generate_session.py
```

`API_ID`, `API_HASH`, and `PHONE_NUMBER` sab `.env` se uthaye jaate hain
— phone number type karne ki zaroorat nahi. Telegram sirf ek **login
code (OTP)** bhejega, aur agar 2FA on hai toh password poochega —
yeh do cheezein hi interactive rehti hain (Telegram inhe store nahi
karne deta, isliye env se possible nahi).

Output mein jo `STRING_SESSION` milega, usko `.env` mein paste karo.

### 4. Add BOT_TOKEN

`@BotFather` se bot banao, uska token `.env` mein `BOT_TOKEN` mein daalo.

### 5. Run locally

```bash
python bot.py
```

### 6. Deploy to Render

- Service type: **Background Worker**
- Build command: `pip install -r requirements.txt`
- Start command: `python bot.py`
- Set all env vars from `.env.example` (except `PHONE_NUMBER`, which
  isn't needed by `bot.py`) in Render's Environment tab.

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests cover `notifier/config.py` (env validation) and `notifier/logic.py`
(cooldown gate, message filtering) — pure logic, no live Telegram
connection needed.

## "Please enter your phone (or bot token)" error

Yeh error tab aata hai jab Telethon `STRING_SESSION` ko invalid
samajhta hai (expired, revoked, ya galat copy hua) aur interactive
login fallback trigger ho jata tha. Render pe koi terminal input
nahi hota, isliye `EOF` error aake crash-loop start ho jata.

`bot.py` mein ab session ko `connect()` + `is_user_authorized()` se
explicitly verify kiya jaata hai — agar invalid ho, turant clear error
deke exit hota hai, kabhi phone number nahi maangta.

**Fix:** `scripts/generate_session.py` chalao, naya `STRING_SESSION`
banao, Render env variable update karo.

## Session getting revoked (`SessionRevokedError`)

Agar Telegram app mein kisi account ko **"Log out"** kiya jaata hai
(chahe account switch karne ke process mein), toh Telegram us poore
account ka session hi khatam kar deta hai — sirf ek device ka nahi.
`STRING_SESSION` bhi usi account ka ek session hai, isliye woh bhi
revoke ho jaata hai aur sab devices se logout ho jaate hain.

**Bachne ka tareeka:** account switch karte waqt "Add Account" use
karo, us account ko kabhi "Log out"/"Remove" mat karo jispe notifier
chal raha hai.

## Bot "frozen"/limited by Telegram

Yeh code-level issue nahi hai. Fix:
1. `@BotFather` ko `/mybots` bhejo, bot select karo, status dekho
2. Agar limited dikhe, `@BotSupport` ko contact karo, bot username +
   issue batao
