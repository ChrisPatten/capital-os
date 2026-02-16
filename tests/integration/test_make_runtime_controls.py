from __future__ import annotations

from pathlib import Path
import os
import signal
import socket
import subprocess
import time

import pytest


def _can_bind_localhost() -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
        return True
    except PermissionError:
        return False


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run_make(target: str, env: dict[str, str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", target],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _base_env(tmp_path: Path, port: int) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "HOST": "127.0.0.1",
            "PORT": str(port),
            "BASE_URL": f"http://127.0.0.1:{port}",
            "CAPITAL_OS_DB_URL": f"sqlite:///{tmp_path / 'capital-os-runtime.db'}",
            "CAPITAL_OS_IDLE_SECONDS": "2",
            "RUN_DIR": str(tmp_path / "run"),
        }
    )
    return env


def _pid_file(env: dict[str, str]) -> Path:
    return Path(env["RUN_DIR"]) / "capital-os.pid"


def _run_file(env: dict[str, str], name: str) -> Path:
    return Path(env["RUN_DIR"]) / name


def _stop_runtime(env: dict[str, str]) -> None:
    _run_make("stop", env, timeout=10)


def test_make_run_is_idempotent_when_service_is_healthy(tmp_path: Path) -> None:
    if not _can_bind_localhost():
        pytest.skip("sandbox disallows localhost socket binding")
    port = _free_port()
    env = _base_env(tmp_path, port)

    try:
        assert _run_make("init", env).returncode == 0

        first = _run_make("run", env)
        assert first.returncode == 0, first.stderr
        pid_first = int(_pid_file(env).read_text(encoding="utf-8").strip())

        second = _run_make("run", env)
        assert second.returncode == 0, second.stderr
        pid_second = int(_pid_file(env).read_text(encoding="utf-8").strip())
        assert pid_second == pid_first

        stopped = _run_make("stop", env)
        assert stopped.returncode == 0
        assert not _run_file(env, "capital-os.pid").exists()
        assert not _run_file(env, "capital-os.url").exists()
        assert not _run_file(env, "last_request.ts").exists()
        assert not _run_file(env, "uvicorn.log").exists()
    finally:
        _stop_runtime(env)


def test_serve_idle_handles_stale_pid_and_exits_after_idle(tmp_path: Path) -> None:
    if not _can_bind_localhost():
        pytest.skip("sandbox disallows localhost socket binding")
    port = _free_port()
    env = _base_env(tmp_path, port)
    run_dir = Path(env["RUN_DIR"])

    try:
        assert _run_make("init", env).returncode == 0

        run_dir.mkdir(parents=True, exist_ok=True)
        _pid_file(env).write_text("999999", encoding="utf-8")

        first = _run_make("serve-idle", env)
        assert first.returncode == 0, first.stderr
        runtime_pid = int(_pid_file(env).read_text(encoding="utf-8").strip())

        second = _run_make("serve-idle", env)
        assert second.returncode == 0, second.stderr
        runtime_pid_second = int(_pid_file(env).read_text(encoding="utf-8").strip())
        assert runtime_pid_second == runtime_pid

        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                os.kill(runtime_pid, 0)
                time.sleep(0.2)
            except ProcessLookupError:
                break
        else:
            raise AssertionError("runtime did not stop after idle timeout")

        assert not _pid_file(env).exists()
    finally:
        _stop_runtime(env)
        pid_path = _pid_file(env)
        if pid_path.exists():
            pid = int(pid_path.read_text(encoding="utf-8").strip())
            os.kill(pid, signal.SIGKILL)
