"""Authentication and RBAC helpers for the service layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from fastapi import Header, HTTPException, status


@dataclass(frozen=True)
class AuthSettings:
    """Configuration captured for documentation and future wiring."""

    issuer: Optional[str] = None
    audience: Optional[str] = None
    jwks_url: Optional[str] = None
    mtls_enabled: bool = False


@dataclass(frozen=True)
class AuthContext:
    """Represents the authenticated caller used for RBAC checks."""

    actor: str
    roles: tuple[str, ...]
    tenant: str
    reason: str


def parse_roles(raw_roles: Optional[str]) -> List[str]:
    if not raw_roles:
        return []
    return [role.strip() for role in raw_roles.split(",") if role.strip()]


def get_auth_context(  # pragma: no cover - exercised via integration tests
    x_actor: Optional[str] = Header(default=None, alias="X-Actor"),
    x_roles: Optional[str] = Header(default=None, alias="X-Roles"),
    x_tenant: Optional[str] = Header(default=None, alias="X-Tenant"),
    x_reason: Optional[str] = Header(default=None, alias="X-Reason"),
) -> AuthContext:
    """Derive an :class:`AuthContext` from required headers.

    In production this would validate JWTs or client certificates. For the
    purposes of the service implementation we treat the headers as mandatory
    so that RBAC behaviour is deterministic in tests and stubs.
    """

    if not x_actor or not x_roles or not x_tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication headers",
        )

    roles = parse_roles(x_roles)
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No roles associated with caller",
        )

    return AuthContext(
        actor=x_actor,
        roles=tuple(roles),
        tenant=x_tenant,
        reason=x_reason or "unspecified",
    )


def require_roles(context: AuthContext, allowed_roles: Iterable[str]) -> None:
    """Raise an HTTP 403 error when the caller lacks required roles."""

    if not set(context.roles).intersection(set(allowed_roles)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Caller lacks required role",
        )


def get_auth_settings() -> AuthSettings:
    """Return default auth settings; retained for completeness."""

    return AuthSettings()

