#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import sys
import threading
import time

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class LastRequestTouchMiddleware:
    def __init__(self, app, last_request_file: Path):
        self.app = app
        self.last_request_file = last_request_file

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            touch_last_request(self.last_request_file)
        await self.app(scope, receive, send)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def touch_last_request(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(utc_now_iso(), encoding="utf-8")


def seconds_since_touch(path: Path) -> float:
    if not path.exists():
        return 0.0
    try:
        last_seen = datetime.fromisoformat(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return 0.0
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    return max((datetime.now(timezone.utc) - last_seen).total_seconds(), 0.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Capital OS API with idle shutdown support")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--pid-file", default=".run/capital-os.pid")
    parser.add_argument("--url-file", default=".run/capital-os.url")
    parser.add_argument("--last-request-file", default=".run/last_request.ts")
    parser.add_argument("--idle-seconds", type=int, default=0)
    parser.add_argument("--check-interval-seconds", type=float, default=0.5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pid_file = Path(args.pid_file)
    url_file = Path(args.url_file)
    last_request_file = Path(args.last_request_file)

    from capital_os.main import app as capital_app

    wrapped_app = LastRequestTouchMiddleware(capital_app, last_request_file)
    config = uvicorn.Config(app=wrapped_app, host=args.host, port=args.port, log_level="info")
    server = uvicorn.Server(config)

    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    url_file.write_text(f"http://{args.host}:{args.port}", encoding="utf-8")
    touch_last_request(last_request_file)

    def request_shutdown(*_):
        server.should_exit = True

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    try:
        while server_thread.is_alive() and not server.should_exit:
            time.sleep(args.check_interval_seconds)
            if args.idle_seconds > 0 and seconds_since_touch(last_request_file) >= args.idle_seconds:
                server.should_exit = True
        server_thread.join(timeout=5)
    finally:
        pid_file.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
