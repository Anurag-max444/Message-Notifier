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
    cooldown: int
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
    cooldown = int(env.get("COOLDOWN", "30"))

    if require_phone:
        # generate_session.py: STRING_SESSION/BOT_TOKEN not needed yet
        phone_number = _require(env, "PHONE_NUMBER")
        return Config(
            api_id=api_id,
            api_hash=api_hash,
            string_session="",
            bot_token="",
            owner_id=owner_id,
            cooldown=cooldown,
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
        cooldown=cooldown,
        phone_number=phone_number,
    )
