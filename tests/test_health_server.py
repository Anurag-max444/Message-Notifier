import urllib.request
import time

from notifier.health_server import start_health_server


def test_health_server_responds_ok_to_get():
    port = 10101
    start_health_server(port=port)
    time.sleep(0.2)

    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as resp:
        assert resp.status == 200
        assert resp.read() == b"ok"


def test_health_server_responds_ok_to_head():
    # Uptime monitors (UptimeRobot, etc.) send HEAD requests, not GET.
    # Without a do_HEAD handler, BaseHTTPRequestHandler replies with
    # 501 Not Implemented, which looks like downtime to monitors.
    port = 10103
    start_health_server(port=port)
    time.sleep(0.2)

    req = urllib.request.Request(f"http://127.0.0.1:{port}/", method="HEAD")
    with urllib.request.urlopen(req, timeout=2) as resp:
        assert resp.status == 200
