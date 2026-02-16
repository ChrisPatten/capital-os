from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass(frozen=True)
class RequestSecurityContext:
    actor_id: str
    authn_method: str
    authorization_result: str


_REQUEST_SECURITY_CONTEXT: ContextVar[RequestSecurityContext | None] = ContextVar(
    "request_security_context",
    default=None,
)


def set_request_security_context(context: RequestSecurityContext) -> Token:
    return _REQUEST_SECURITY_CONTEXT.set(context)


def clear_request_security_context(token: Token) -> None:
    _REQUEST_SECURITY_CONTEXT.reset(token)


def get_request_security_context() -> RequestSecurityContext | None:
    return _REQUEST_SECURITY_CONTEXT.get()
