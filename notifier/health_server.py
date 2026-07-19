"""
Render 'Web Service' plans expect something listening on a port,
otherwise it repeatedly logs "No open ports detected" and can fail
health checks. This bot has no real HTTP work to do, so this module
just runs a tiny background HTTP server that always returns 200 OK.

Runs in a daemon thread so it never blocks the asyncio event loop
that Telethon uses in bot.py.
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._reply(include_body=True)

    def do_HEAD(self):
        # Uptime monitors (UptimeRobot, etc.) send HEAD requests.
        # Without this, BaseHTTPRequestHandler auto-replies with
        # 501 Not Implemented, which monitors treat as downtime.
        self._reply(include_body=False)

    def _reply(self, include_body: bool):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "2")
        self.end_headers()
        if include_body:
            self.wfile.write(b"ok")

    def log_message(self, format, *args):
        # Silence default request logging — keep bot logs clean.
        pass


def start_health_server(port: int = None) -> threading.Thread:
    """
    Starts a tiny HTTP server on a background daemon thread and
    returns the thread. Port defaults to Render's PORT env var,
    falling back to 10000 for local runs.
    """
    if port is None:
        port = int(os.getenv("PORT", "10000"))

    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread
