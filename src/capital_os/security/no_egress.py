from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import socket
from typing import Any


class NetworkEgressBlockedError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Outbound network egress is blocked by runtime policy")
        self.error_code = "network_egress_blocked"


_GUARD_ACTIVE: ContextVar[bool] = ContextVar("no_egress_guard_active", default=False)
_ALLOWLIST: ContextVar[tuple[str, ...]] = ContextVar("no_egress_allowlist", default=())
_INSTALLED = False
_ORIGINAL_CREATE_CONNECTION = socket.create_connection
_ORIGINAL_SOCKET_CONNECT = socket.socket.connect


def _host_from_address(address: Any) -> str | None:
    if isinstance(address, tuple) and address:
        host = address[0]
        if isinstance(host, str):
            return host.lower()
    return None


def _guarded_create_connection(address, *args, **kwargs):  # noqa: ANN001
    if _GUARD_ACTIVE.get():
        host = _host_from_address(address)
        if host not in _ALLOWLIST.get():
            raise NetworkEgressBlockedError()
    return _ORIGINAL_CREATE_CONNECTION(address, *args, **kwargs)


def _guarded_socket_connect(self, address):  # noqa: ANN001
    if _GUARD_ACTIVE.get():
        host = _host_from_address(address)
        if host not in _ALLOWLIST.get():
            raise NetworkEgressBlockedError()
    return _ORIGINAL_SOCKET_CONNECT(self, address)


def install_no_egress_guardrails() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    socket.create_connection = _guarded_create_connection
    socket.socket.connect = _guarded_socket_connect
    _INSTALLED = True


@contextmanager
def enforce_no_egress(*, allowlist: tuple[str, ...] = ()):
    enabled_token = _GUARD_ACTIVE.set(True)
    allowlist_token = _ALLOWLIST.set(tuple(sorted(set(host.lower() for host in allowlist))))
    try:
        yield
    finally:
        _ALLOWLIST.reset(allowlist_token)
        _GUARD_ACTIVE.reset(enabled_token)
