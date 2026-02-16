from __future__ import annotations

from dataclasses import dataclass

from capital_os.config import AUTHN_METHOD_HEADER_TOKEN, get_settings


@dataclass(frozen=True)
class AuthContext:
    actor_id: str
    authn_method: str
    capabilities: tuple[str, ...]


def authenticate_token(token: str | None) -> AuthContext | None:
    if not token:
        return None
    identity = (get_settings().token_identities or {}).get(token)
    if not identity:
        return None
    return AuthContext(
        actor_id=str(identity["actor_id"]),
        authn_method=AUTHN_METHOD_HEADER_TOKEN,
        capabilities=tuple(identity["capabilities"]),  # type: ignore[arg-type]
    )


def authorize_tool(auth_context: AuthContext, tool_name: str) -> bool:
    required_capability = (get_settings().tool_capabilities or {}).get(tool_name)
    if required_capability is None:
        return False
    return required_capability in auth_context.capabilities
