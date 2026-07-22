"""
Central place to load and validate all environment variables.
Kept separate from bot.py so it can be unit tested without touching
Telethon or the network.
"""

import os
from dataclasses import dataclass
from typing import Optional


class ConfigError(Exception):
    """Raised when required environment variables are missing or invalid."""


@dataclass(frozen=True)
class Config:
    api_id: int
    api_hash: str
    string_session: str
    bot_token: str
    owner_id: int
    control_owner_ids: tuple  # who's allowed to issue bot commands
    cooldown: int
    supabase_url: str
    supabase_key: str
    phone_number: Optional[str] = None  # only needed by generate_session.py


NOTIFICATION_TEXT = "🔔 Session Activated."


def _require(env: dict, name: str) -> str:
    value = env.get(name)
    if value is None or value.strip() == "":
        raise ConfigError(f"Missing required environment variable: {name}")
    return value.strip()


def _require_int(env: dict, name: str) -> int:
    raw = _require(env, name)
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be an integer, got: {raw!r}")


def _parse_control_owner_ids(raw: str, owner_id: int) -> tuple:
    """
    Comma-separated CONTROL_OWNER_IDS env var — who's allowed to issue
    bot commands. OWNER_ID is always included even if not listed, since
    it's the account that receives notifications and should always be
    able to control them.
    """
    ids = {owner_id}
    raw = raw.strip()
    if raw:
        try:
            ids |= {int(part.strip()) for part in raw.split(",") if part.strip()}
        except ValueError:
            raise ConfigError(f"CONTROL_OWNER_IDS must be comma-separated integers, got: {raw!r}")
    return tuple(sorted(ids))


def load_config(env: Optional[dict] = None, require_phone: bool = False) -> Config:
    """
    Load configuration from the given mapping (defaults to os.environ).

    require_phone=True is used by generate_session.py, which needs
    PHONE_NUMBER. The main bot never needs it.
    """
    env = os.environ if env is None else env

    api_id = _require_int(env, "API_ID")
    api_hash = _require(env, "API_HASH")
    owner_id = _require_int(env, "OWNER_ID")
    control_owner_ids = _parse_control_owner_ids(env.get("CONTROL_OWNER_IDS", ""), owner_id)
    cooldown = int(env.get("COOLDOWN", "30"))
    supabase_url = _require(env, "SUPABASE_URL")
    supabase_key = _require(env, "SUPABASE_SERVICE_KEY")

    if require_phone:
        # generate_session.py: STRING_SESSION/BOT_TOKEN not needed yet
        phone_number = _require(env, "PHONE_NUMBER")
        return Config(
            api_id=api_id,
            api_hash=api_hash,
            string_session="",
            bot_token="",
            owner_id=owner_id,
            control_owner_ids=control_owner_ids,
            cooldown=cooldown,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            phone_number=phone_number,
        )

    string_session = _require(env, "STRING_SESSION")
    bot_token = _require(env, "BOT_TOKEN")
    phone_number = env.get("PHONE_NUMBER", "").strip() or None

    return Config(
        api_id=api_id,
        api_hash=api_hash,
        string_session=string_session,
        bot_token=bot_token,
        owner_id=owner_id,
        control_owner_ids=control_owner_ids,
        cooldown=cooldown,
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        phone_number=phone_number,
    )
