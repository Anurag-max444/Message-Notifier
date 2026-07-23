# Telegram Message Notifier

Jab bhi tumhare personal Telegram account par koi naya incoming
**private** message aaye (kisi user ya bot se), ek Bot tumhe generic
notification bhejta hai. Groups/channels by default ignore hote hain
(runtime pe `/groups` se on kiye ja sakte hain). Sirf tumhare khud ke
bheje messages hamesha ignore hote hain. Content kabhi reveal nahi
hota; sender ka naam optional hai (`/reveal`).

Bot ko DM karke runtime pe poori tarah control kiya ja sakta hai —
cooldown badlo, sab kuch temporarily mute karo, roz ek fixed "quiet
hours" window set karo, ya specific "VIP" users set karo jinke
messages hamesha turant notify karein (ya apna khud ka custom
cooldown le lein).

## Project Structure

```
.
├── bot.py                        # Thin entrypoint — wiring + main loop only
├── notifier/
│   ├── __init__.py
│   ├── config.py                  # Loads + validates all env vars (testable)
│   ├── store/                     # Supabase persistence, split by concern
│   │   ├── __init__.py             # Re-exports everything below
│   │   ├── client.py                # Supabase client factory
│   │   ├── state_store.py           # notifier_state table
│   │   ├── vip_store.py             # notifier_vips table
│   │   └── chat_store.py            # notifier_allowed_chats table
│   ├── state.py                   # Cooldown/mute/VIP/allow-list business logic (testable)
│   ├── logic.py                   # Pure message-filter logic (testable)
│   ├── group_filter.py            # Pure per-chat allow-list logic (testable)
│   ├── vip_labels.py               # Pure VIP-by-label grouping logic (testable)
│   ├── handlers.py                # user_client: watches for new messages
│   ├── commands/                  # bot_client: owner-only commands, split by feature
│   │   ├── __init__.py             # register_commands + register_bot_menu
│   │   ├── command_list.py          # COMMAND_LIST — single source of truth
│   │   ├── common.py                # is_owner / to_thread / fmt_seconds helpers
│   │   ├── mute_commands.py         # /skip /resume /cooldown
│   │   ├── groups_commands.py       # /groups /allowchat /disallowchat /allowedchats
│   │   ├── reveal_commands.py       # /reveal
│   │   ├── quiethours_commands.py   # /quiethours
│   │   ├── vip_commands.py          # /vip /unvip /viplabel /vipmute /vipcooldown /vips
│   │   ├── status_commands.py       # /help /status /mutelist
│   │   └── fallback_commands.py     # /start + unknown-command / non-command catch-all
│   ├── lang/                      # User-facing UI text, centralized
│   │   ├── __init__.py             # Re-exports lang.py
│   │   └── lang.py                  # Welcome message, error templates, etc.
│   ├── logging_setup.py           # Console + rotating file logging
│   └── health_server.py           # Tiny HTTP server for Render's port scan
├── scripts/
│   └── generate_session.py        # One-time local script to create STRING_SESSION
├── tests/
│   ├── test_config.py
│   ├── test_state.py
│   ├── test_logic.py
│   ├── test_group_filter.py
│   ├── test_vip_labels.py
│   ├── test_commands.py
│   ├── test_fallback_commands.py
│   ├── test_lang.py
│   ├── test_handlers.py
│   ├── test_logging_setup.py
│   ├── test_health_server.py
│   └── conftest.py                 # shared pytest fixtures
├── logs/                          # Rotating log files (bot.log, gitignored contents)
├── requirements.txt
├── requirements-dev.txt           # adds pytest, anyio
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
    cooldown_seconds int,  -- null = full bypass (instant, every message)
    label text,             -- optional, for grouping in /vips
    created_at timestamptz not null default now()
);

create table if not exists notifier_allowed_chats (
    chat_id bigint primary key,
    label text,
    created_at timestamptz not null default now()
);

create table if not exists notifier_state (
    id int primary key default 1,
    cooldown_seconds int not null default 30,
    global_mute_until bigint not null default 0,
    allow_groups boolean not null default false,
    reveal_sender boolean not null default false,
    quiet_start text,  -- "HH:MM" or null
    quiet_end text,    -- "HH:MM" or null
    constraint single_row check (id = 1)
);

insert into notifier_state (id, cooldown_seconds, global_mute_until, allow_groups, reveal_sender)
values (1, 30, 0, false, false)
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

DM the bot itself (`@your_bot_username`) — only IDs in
`CONTROL_OWNER_IDS` (which always includes `OWNER_ID`) are allowed to
use these, everyone else is silently ignored. Same list also shows up
in Telegram's own "/" quick-command menu automatically (set via API on
every startup — see `notifier/commands/__init__.py::register_bot_menu`).

Send `/start` any time for a short welcome message. If you mistype a
command (or send plain text), the bot suggests the closest match or
shows the full command list — no need to remember exact syntax.

```
/start - Welcome message
/help - Sabhi commands ki list dikhaye
/status - Current cooldown, mute aur VIP status dikhaye
/skip - Sab normal notifications kuch der ke liye mute karo
/resume - Active mute turant hata do
/cooldown - Normal users ke notify ke beech ka gap set karo (minutes)
/groups - Group/channel messages ka notify on/off karo
/allowchat - Sirf specific group/channel se notify karo (allow-list)
/disallowchat - Ek chat ko allow-list se hatao
/allowedchats - Allow-list me jo chats hain unki list dikhaye
/reveal - Notification me sender ka naam dikhana on/off karo
/quiethours - Roz ek fixed time window me auto-mute set karo
/mutelist - Global mute + har VIP ka mute status, remaining time ke saath
/vip - Kisi user ko VIP banao (optional label ke saath)
/unvip - VIP status hatao
/viplabel - Kisi existing VIP ka label badlo ya hatao
/vips - Sabhi VIP users ki list, label ke hisaab se grouped
/vipmute - Ek VIP user ko X minute ke liye mute karo
/vipcooldown - VIP ko full-bypass ki jagah apna khud ka cooldown do
```

**Usage:**
| Command | Effect |
|---|---|
| `/skip` | Shows buttons (1/5/10/20/60 min) to temporarily mute all normal notifications |
| `/resume` | Clears an active `/skip` mute immediately |
| `/cooldown <minutes>` | Sets the gap between notifications for normal (non-VIP) senders |
| `/groups` | Buttons to turn group/channel notifications on or off (off by default) |
| `/allowchat <chat_id> ["label"]` | Narrows group/channel notifications to only this chat. Once any chat is added, only listed chats notify — everything else is skipped even with `/groups` on |
| `/disallowchat <chat_id>` | Removes a chat from the allow-list. If the list becomes empty, all groups/channels are allowed again (as long as `/groups` is on) |
| `/allowedchats` | Lists every chat in the allow-list with a "Remove" button each |
| `/reveal` | Buttons to include the sender's first name in the notification text (off by default — notifications stay generic) |
| `/quiethours <start> <end>` | e.g. `/quiethours 23:00 07:00` — auto-mutes normal notifications daily in that window (wraps midnight fine). `/quiethours off` clears it |
| `/mutelist` | Detailed view: global mute + quiet hours + every individually-muted VIP, all with remaining time |
| `/vip <user_id> ["label"]` | That user's messages always notify instantly, ignoring mute/cooldown, by default. Optional label groups them in `/vips` (e.g. `/vip 111 "College Group"`) |
| `/unvip <user_id>` | Removes VIP status |
| `/viplabel <user_id> "label"` | Relabels an existing VIP. `/viplabel <user_id> off` clears the label |
| `/vips` | Lists every VIP grouped by label, each with inline "Mute 10m / Mute 60m / Remove" buttons |
| `/vipmute <user_id> <minutes>` | Mutes just that one VIP user for X minutes |
| `/vipcooldown <user_id> <seconds>` | Gives that VIP their own cooldown instead of full bypass (e.g. `/vipcooldown 111 5`) |
| `/vipcooldown <user_id> off` | Restores full bypass (instant, every message) for that VIP |
| `/status` | Quick summary: cooldown, mute, groups (+ allow-list count), reveal, quiet hours, VIP count |
| `/help` | Shows this list |

All of this state lives in Supabase (`notifier_state`, `notifier_vips`,
and `notifier_allowed_chats` tables), so it survives bot
restarts/redeploys.

**Finding a group/channel's chat ID:** forward any message from that
chat to [@userinfobot](https://t.me/userinfobot) or
[@RawDataBot](https://t.me/RawDataBot) — it'll show the numeric ID
(negative for groups/channels, e.g. `-100123456789`).

### Multiple owners

By default only `OWNER_ID` can use the commands above. To let a
trusted second person (or account) control the bot too, set
`CONTROL_OWNER_IDS` to a comma-separated list, e.g.:

```
CONTROL_OWNER_IDS=111111111,222222222
```

`OWNER_ID` is always included automatically even if you leave this
blank or don't list it explicitly.

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

## `/groups` on karne ke baad bhi group messages notify nahi ho rahe

Fixed. Root cause: Telethon ko har group/channel ka `access_hash`
cache mein chahiye hota hai taaki uske messages ka event sahi se ban
sake — aur `/reveal` ke liye sender ka naam resolve karne mein bhi
yehi cache use hota hai. Bina is cache ke, group/channel updates
silently drop ho sakte the (na koi error, na koi log — isliye pakadna
mushkil tha).

Fix: `bot.py` ab login ke turant baad ek baar `user_client.get_dialogs()`
call karta hai, jo account ke saare chats (private, groups, channels)
ka cache warm kar deta hai. Agar naye group mein baad mein add ho, us
group se bhi notify chalu karne ke liye bot ko ek baar restart karna
sabse reliable hai (dialog cache turant refresh ho jaata hai).
