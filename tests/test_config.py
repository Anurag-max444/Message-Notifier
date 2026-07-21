import pytest

from notifier.config import load_config, ConfigError


def base_env(**overrides):
    env = {
        "API_ID": "123456",
        "API_HASH": "abcdef123456",
        "STRING_SESSION": "fake_session_string",
        "BOT_TOKEN": "123456:fake_bot_token",
        "OWNER_ID": "987654321",
        "COOLDOWN": "30",
        "SUPABASE_URL": "https://fake.supabase.co",
        "SUPABASE_SERVICE_KEY": "fake_service_key",
    }
    env.update(overrides)
    return env


def test_load_config_success():
    cfg = load_config(base_env())
    assert cfg.api_id == 123456
    assert cfg.api_hash == "abcdef123456"
    assert cfg.string_session == "fake_session_string"
    assert cfg.bot_token == "123456:fake_bot_token"
    assert cfg.owner_id == 987654321
    assert cfg.cooldown == 30
    assert cfg.supabase_url == "https://fake.supabase.co"
    assert cfg.supabase_key == "fake_service_key"


def test_missing_supabase_url_raises():
    env = base_env()
    del env["SUPABASE_URL"]
    with pytest.raises(ConfigError, match="SUPABASE_URL"):
        load_config(env)


def test_missing_supabase_key_raises():
    env = base_env()
    del env["SUPABASE_SERVICE_KEY"]
    with pytest.raises(ConfigError, match="SUPABASE_SERVICE_KEY"):
        load_config(env)


def test_cooldown_defaults_to_30_when_missing():
    env = base_env()
    del env["COOLDOWN"]
    cfg = load_config(env)
    assert cfg.cooldown == 30


def test_missing_api_id_raises():
    env = base_env()
    del env["API_ID"]
    with pytest.raises(ConfigError, match="API_ID"):
        load_config(env)


def test_missing_api_hash_raises():
    env = base_env()
    del env["API_HASH"]
    with pytest.raises(ConfigError, match="API_HASH"):
        load_config(env)


def test_missing_string_session_raises():
    env = base_env()
    del env["STRING_SESSION"]
    with pytest.raises(ConfigError, match="STRING_SESSION"):
        load_config(env)


def test_missing_bot_token_raises():
    env = base_env()
    del env["BOT_TOKEN"]
    with pytest.raises(ConfigError, match="BOT_TOKEN"):
        load_config(env)


def test_missing_owner_id_raises():
    env = base_env()
    del env["OWNER_ID"]
    with pytest.raises(ConfigError, match="OWNER_ID"):
        load_config(env)


def test_non_integer_api_id_raises():
    env = base_env(API_ID="not_a_number")
    with pytest.raises(ConfigError, match="API_ID must be an integer"):
        load_config(env)


def test_non_integer_owner_id_raises():
    env = base_env(OWNER_ID="not_a_number")
    with pytest.raises(ConfigError, match="OWNER_ID must be an integer"):
        load_config(env)


def test_blank_string_treated_as_missing():
    env = base_env(API_HASH="   ")
    with pytest.raises(ConfigError, match="API_HASH"):
        load_config(env)


def test_require_phone_true_needs_phone_number():
    env = base_env()
    del env["STRING_SESSION"]
    del env["BOT_TOKEN"]
    env["PHONE_NUMBER"] = "+911234567890"
    cfg = load_config(env, require_phone=True)
    assert cfg.phone_number == "+911234567890"


def test_require_phone_true_missing_phone_raises():
    env = base_env()
    with pytest.raises(ConfigError, match="PHONE_NUMBER"):
        load_config(env, require_phone=True)


def test_phone_number_optional_for_main_bot():
    cfg = load_config(base_env())
    assert cfg.phone_number is None
