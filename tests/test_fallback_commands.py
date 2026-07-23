import pytest

from notifier.commands.fallback_commands import register_fallback_commands, _closest_command_usage
from notifier.lang import WELCOME_MESSAGE


class FakeCfg:
    control_owner_ids = (987654321,)


class FakeEvent:
    def __init__(self, sender_id, text):
        self.sender_id = sender_id
        self.raw_text = text
        self.responded = None

    async def respond(self, text):
        self.responded = text


@pytest.fixture
def handlers():
    registry = {}

    class FakeBotClient:
        def on(self, builder):
            def deco(fn):
                registry[id(builder)] = (builder, fn)
                return fn
            return deco

    register_fallback_commands(FakeBotClient(), FakeCfg())
    return registry


def _get(handlers, cls_name, pattern_text=None):
    for builder, fn in handlers.values():
        cls = type(builder).__name__
        pat = getattr(builder, "pattern", None)
        if cls != cls_name:
            continue
        if pattern_text is None and pat is None:
            return fn
        if pat is not None and getattr(pat, "__self__", None) and pat.__self__.pattern == pattern_text:
            return fn
    raise AssertionError(f"No handler found for {cls_name} / {pattern_text}")


class TestClosestCommandUsage:
    def test_close_typo_suggests_match(self):
        suggestion, usage = _closest_command_usage("groop")
        assert suggestion == "groups"
        assert usage.startswith("/groups - ")

    def test_completely_unrelated_returns_none(self):
        suggestion, usage = _closest_command_usage("xyz123qwerty")
        assert suggestion is None
        assert usage is None


@pytest.mark.anyio
async def test_start_command_sends_welcome_message(handlers):
    fn = _get(handlers, "NewMessage", "/start")
    ev = FakeEvent(987654321, "/start")
    await fn(ev)
    assert ev.responded == WELCOME_MESSAGE


@pytest.mark.anyio
async def test_start_ignored_for_non_owner(handlers):
    fn = _get(handlers, "NewMessage", "/start")
    ev = FakeEvent(111, "/start")
    await fn(ev)
    assert ev.responded is None


@pytest.mark.anyio
async def test_catch_all_stays_silent_for_known_command(handlers):
    fn = _get(handlers, "NewMessage", None)
    ev = FakeEvent(987654321, "/groups")
    await fn(ev)
    assert ev.responded is None


@pytest.mark.anyio
async def test_catch_all_suggests_close_typo(handlers):
    fn = _get(handlers, "NewMessage", None)
    ev = FakeEvent(987654321, "/groop")
    await fn(ev)
    assert "groups" in ev.responded


@pytest.mark.anyio
async def test_catch_all_shows_full_help_for_unrelated_command(handlers):
    fn = _get(handlers, "NewMessage", None)
    ev = FakeEvent(987654321, "/xyz123qwerty")
    await fn(ev)
    assert "Available Commands" in ev.responded


@pytest.mark.anyio
async def test_catch_all_nudges_on_plain_text(handlers):
    fn = _get(handlers, "NewMessage", None)
    ev = FakeEvent(987654321, "hi bhai")
    await fn(ev)
    assert "Available Commands" in ev.responded


@pytest.mark.anyio
async def test_catch_all_ignored_for_non_owner(handlers):
    fn = _get(handlers, "NewMessage", None)
    ev = FakeEvent(111, "/xyz123qwerty")
    await fn(ev)
    assert ev.responded is None
