import asyncio

import pytest


@pytest.fixture(autouse=True)
def _ensure_event_loop():
    """
    TelegramClient's constructor calls asyncio.get_event_loop() eagerly.
    Async tests (via the anyio plugin) create and close their own loop
    per test, which can leave the main thread without a "current" loop
    for later synchronous tests that construct a TelegramClient in a
    fixture. This keeps that call safe regardless of test order.
    """
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    yield
