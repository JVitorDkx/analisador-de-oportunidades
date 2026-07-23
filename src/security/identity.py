"""Server-derived identity and profile controls."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from src.security.models import Principal, Profile, ProfileUpdateRequest


class UnauthenticatedError(PermissionError):
    """Raised when a session token is absent or not recognized."""


class Authenticator(Protocol):
    """Authenticate a request and derive its server-authoritative principal."""

    def authenticate(
        self,
        authorization: str | None,
        tenant_id: str | None = None,
    ) -> Principal: ...


class StaticSessionAuthenticator:
    """Deterministic session adapter used by the security integration suite."""

    def __init__(self, sessions: Mapping[str, Principal]) -> None:
        self._sessions = dict(sessions)

    def authenticate(
        self,
        authorization: str | None,
        tenant_id: str | None = None,
    ) -> Principal:
        scheme, separator, token = (authorization or "").partition(" ")
        if not separator or scheme.lower() != "bearer" or not token:
            raise UnauthenticatedError("a valid bearer session is required")
        try:
            principal = self._sessions[token]
        except KeyError as exc:
            raise UnauthenticatedError("a valid bearer session is required") from exc
        if tenant_id is not None and tenant_id != principal.tenant_id:
            raise UnauthenticatedError("a valid bearer session is required")
        return principal


class ProfileService:
    """Update only client-editable profile fields and preserve privileges."""

    def __init__(self, profiles: Mapping[str, Profile]) -> None:
        self._profiles = dict(profiles)

    def update(self, principal: Principal, request: ProfileUpdateRequest) -> Profile:
        profile = self._profiles.get(principal.user_id)
        if profile is None or profile.tenant_id != principal.tenant_id:
            raise UnauthenticatedError("profile does not match the authenticated session")
        updated = profile.model_copy(update={"display_name": request.display_name})
        self._profiles[principal.user_id] = updated
        return updated
