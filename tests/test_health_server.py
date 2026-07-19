import urllib.request
import time

from notifier.health_server import start_health_server


def test_health_server_responds_ok():
    # Use a distinct port so it doesn't clash with a real run.
    port = 10101
    start_health_server(port=port)

    # Give the server thread a moment to bind and start listening.
    time.sleep(0.2)

    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as resp:
        assert resp.status == 200
        assert resp.read() == b"ok"
