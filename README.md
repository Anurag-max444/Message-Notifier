# Telegram Message Notifier

Jab bhi tumhare personal Telegram account par koi naya incoming
**private** message aaye (kisi user ya bot se), ek Bot tumhe generic
notification bhejta hai. Groups/channels ignore hote hain. Sirf tumhare
khud ke bheje messages bhi ignore hote hain. Sender, content, ya count
kabhi reveal nahi hote.

Bot ko DM karke runtime pe control kiya ja sakta hai — cooldown badlo,
sab kuch temporarily mute karo, ya specific "VIP" users set karo jinke
messages hamesha turant notify karein, mute/cooldown ignore karke.

## Project Structure

```
.
├── bot.py                        # Thin entrypoint — wiring + main loop only
├── notifier/
│   ├── __init__.py
│   ├── config.py                  # Loads + validates all env vars (testable)
│   ├── store.py                   # Supabase persistence layer
│   ├── state.py                   # Cooldown/mute/VIP business logic (testable)
│   ├── logic.py                   # Pure message-filter logic (testable)
│   ├── handlers.py                # user_client: watches for new messages
│   ├── commands.py                # bot_client: owner-only commands + menu
│   ├── logging_setup.py           # Console + rotating file logging
│   └── health_server.py           # Tiny HTTP server for Render's port scan
├── scripts/
│   └── generate_session.py        # One-time local script to create STRING_SESSION
├── tests/
│   ├── test_config.py
│   ├── test_state.py
│   ├── test_logic.py
│   ├── test_commands.py
│   ├── test_handlers.py
│   ├── test_logging_setup.py
│   └── test_health_server.py
├── logs/                          # Rotating log files (bot.log, gitignored contents)
├── requirements.txt
├── requirements-dev.txt           # adds pytest
├── runtime.txt                    # Python version for Render
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

Fill in `API_ID`, `API_HASH`, `PHONE_NUMBER`, `OWNER_ID`, `SUPABASE_URL`,
and `SUPABASE_SERVICE_KEY`. `STRING_SESSION` and `BOT_TOKEN` come after
the next step.

`SUPABASE_URL`/`SUPABASE_SERVICE_KEY` come from your Supabase project's
Settings > API page. Run this SQL once in the Supabase SQL Editor to
create the tables the bot needs:

```sql
create table if not exists notifier_vips (
    user_id bigint primary key,
    muted_until bigint not null default 0,
    created_at timestamptz not null default now()
);

create table if not exists notifier_state (
    id int primary key default 1,
    cooldown_seconds int not null default 30,
    global_mute_until bigint not null default 0,
    constraint single_row check (id = 1)
);

insert into notifier_state (id, cooldown_seconds, global_mute_until)
values (1, 30, 0)
on conflict (id) do nothing;
```

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

- Service type: **Web Service** (Background Worker costs money on Render;
  Web Service has a free tier, so this project runs a tiny built-in
  health-check HTTP server just to satisfy Render's port scan — the
  bot's real job is still just listening to Telegram, not serving web
  traffic)
- Build command: `pip install -r requirements.txt`
- Start command: `python bot.py`
- Set all env vars from `.env.example` (except `PHONE_NUMBER`, which
  isn't needed by `bot.py`) in Render's Environment tab, plus `PORT`
  (Render sets this automatically on Web Service plans, but `10000`
  is used as a local fallback)

## Bot Control Commands

DM the bot itself (`@your_bot_username`) — only `OWNER_ID` is allowed
to use these, everyone else is silently ignored. Same list also shows
up in Telegram's own "/" quick-command menu automatically (set via API
on every startup — see `notifier/commands.py::register_bot_menu`).

```
/help - Sabhi commands ki list dikhaye
/status - Current cooldown, mute aur VIP status dikhaye
/skip - Sab normal notifications kuch der ke liye mute karo
/resume - Active mute turant hata do
/cooldown - Normal users ke notify ke beech ka gap set karo (minutes)
/vip - Kisi user ko VIP banao — hamesha turant notify karega
/unvip - VIP status hatao
/vips - Sabhi VIP users ki list, mute/remove buttons ke saath
/vipmute - Ek VIP user ko X minute ke liye mute karo
```

**Usage:**
| Command | Effect |
|---|---|
| `/skip` | Shows buttons (1/5/10/20/60 min) to temporarily mute all normal notifications |
| `/resume` | Clears an active `/skip` mute immediately |
| `/cooldown <minutes>` | Sets the gap between notifications for normal (non-VIP) senders |
| `/vip <user_id>` | That user's messages always notify instantly, ignoring mute/cooldown |
| `/unvip <user_id>` | Removes VIP status |
| `/vips` | Lists every VIP with inline "Mute 10m / Mute 60m / Remove" buttons |
| `/vipmute <user_id> <minutes>` | Mutes just that one VIP user for X minutes |
| `/status` | Shows current cooldown, whether globally muted (and for how long), VIP count |
| `/help` | Shows this list |

All of this state lives in Supabase (`notifier_state` and
`notifier_vips` tables), so it survives bot restarts/redeploys.

### BotFather setup (optional, cosmetic)

Send these to `@BotFather` once to give your bot a proper identity:

- `/setdescription` → shown on the bot's empty chat screen before first message:
  > Personal notifier — DM ya koi private message aane par tumhe alert karta hai. Sirf owner ke liye control commands available hain.

- `/setabouttext` → shown on the bot's profile page:
  > Private message notifier bot.

The actual command menu (`/help`, `/skip`, etc.) does **not** need to be
set via BotFather's `/setcommands` — the bot pushes it automatically on
every startup so it can never drift out of sync with the code.



## Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests cover `notifier/config.py` (env validation), `notifier/state.py`
(cooldown/mute/VIP logic), `notifier/logic.py` (message filtering),
`notifier/commands.py` / `notifier/handlers.py` (registration wiring),
and `notifier/logging_setup.py` — all pure/mocked, no live Telegram
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

## UptimeRobot shows "501 Not Implemented" / ongoing incident

Uptime monitors like UptimeRobot send **HEAD** requests, not GET.
Python's `BaseHTTPRequestHandler` auto-replies with `501 Not Implemented`
to any HTTP method that doesn't have a matching `do_*` handler — so a
server with only `do_GET` looks "up" in a browser (which sends GET) but
"down" to the monitor (which sends HEAD).

`notifier/health_server.py` now defines both `do_GET` and `do_HEAD`,
both returning `200`. Verify locally:

```bash
curl -I http://localhost:10000/   # HEAD request — should show HTTP/1.0 200
curl    http://localhost:10000/   # GET request  — should print "ok"
```

## "No open ports detected" on Render

Render's **Web Service** plan expects something listening on a port;
without it, Render repeatedly logs this warning and can eventually
fail the health check / cancel the deploy — even though the bot itself
is running fine.

`notifier/health_server.py` starts a tiny background HTTP server
(always returns `200 ok`) purely to satisfy that port scan. It has no
effect on the bot's actual behavior. Confirm it's working locally:

```bash
python bot.py
# in another terminal:
curl http://localhost:10000/
```

## Bot "frozen"/limited by Telegram

Yeh code-level issue nahi hai. Fix:
1. `@BotFather` ko `/mybots` bhejo, bot select karo, status dekho
2. Agar limited dikhe, `@BotSupport` ko contact karo, bot username +
   issue batao

## Future Ideas

Kuch aage ke improvements jo add kiye ja sakte hain (abhi nahi kiye,
bas ideas hain):

- **`/mutelist`** — active global mute aur har VIP-specific mute ek
  saath, remaining time ke saath dikhaye (abhi `/status` sirf summary
  deta hai).
- **Sender name in notification** — abhi notification generic hai
  (koi detail nahi). Ek `/reveal on|off` command se optional toggle ho
  sakta hai jo sender ka first name (content nahi) include kare.
- **Per-VIP custom cooldown** — abhi VIP ka matlab hai "no cooldown
  at all". Ek beech ka option: VIP ko apna khud ka chhota cooldown do
  (jaise 5 sec), poori tarah bypass ki jagah.
- **Scheduled quiet hours** — jaise raat 11 baje se subah 7 baje tak
  auto-mute, `/quiethours 23:00 07:00` command se set karke.
- **Multiple owners** — abhi sirf ek `OWNER_ID`. Agar 2 log control
  karna chahein (jaise tum aur ek trusted dost), `OWNER_IDS` list
  support add ki ja sakti hai.
- **Supabase Row Level Security (RLS)** — abhi service_role key use ho
  raha hai jo RLS bypass karta hai (safe hai kyunki key sirf tumhare
  Render env mein hai), lekin agar future mein koi frontend dashboard
  banaya jaaye VIP list dekhne ke liye, tab RLS policies zaroori
  hongi.
- **Health check dashboard** — `notifier/health_server.py` abhi sirf
  `200 ok` return karta hai. Isko ek chhota JSON status endpoint bana
  sakte hain (`{"cooldown": 30, "vips": 2, "muted": false}`) jo
  monitoring ke liye useful ho.
