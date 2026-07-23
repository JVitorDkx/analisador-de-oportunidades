"""Authenticated API composition backed by Supabase identity and entitlements."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from src.security.bootstrap import build_supabase_security_dependencies
from src.security.config import SecurityConfigurationError
from src.security.identity import Authenticator, UnauthenticatedError
from src.security.models import Principal, TenantEntitlement
from src.security.repositories.contracts import (
    SecurityRepositoryUnavailable,
    TenantEntitlementResolver,
)


class ApiAuthenticationError(PermissionError):
    """Raised when a protected API request has no valid tenant identity."""


class ApiSecurityUnavailable(RuntimeError):
    """Raised when production authentication cannot be safely resolved."""


@dataclass(frozen=True, slots=True)
class ApiSecurityDependencies:
    authenticator: Authenticator
    entitlement_resolver: TenantEntitlementResolver


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    principal: Principal
    entitlement: TenantEntitlement


@lru_cache(maxsize=1)
def production_api_security_dependencies() -> ApiSecurityDependencies:
    """Build and cache the production JWKS/PostgREST security boundary."""

    try:
        dependencies = build_supabase_security_dependencies()
    except SecurityConfigurationError as exc:
        raise ApiSecurityUnavailable("API authentication is not configured") from exc
    return ApiSecurityDependencies(
        authenticator=dependencies.authenticator,
        entitlement_resolver=dependencies.entitlement_resolver,
    )


def authenticate_session(
    dependencies: ApiSecurityDependencies,
    *,
    authorization: str | None,
    tenant_id: str | None,
) -> AuthenticatedSession:
    """Resolve signed identity, membership and plan without trusting the client."""

    try:
        principal = dependencies.authenticator.authenticate(authorization, tenant_id)
        entitlement = dependencies.entitlement_resolver.resolve(principal)
    except UnauthenticatedError as exc:
        raise ApiAuthenticationError("a valid tenant session is required") from exc
    except SecurityRepositoryUnavailable as exc:
        raise ApiSecurityUnavailable("tenant security services are unavailable") from exc
    return AuthenticatedSession(principal=principal, entitlement=entitlement)
