"""Structural contracts shared by production repositories and in-memory doubles."""

from __future__ import annotations

from typing import Literal, Protocol

from src.security.models import (
    Principal,
    Profile,
    ProfileUpdateRequest,
    TenantEntitlement,
    TenantResource,
)


TenantRole = Literal["owner", "admin", "member"]


class SecurityRepositoryUnavailable(RuntimeError):
    """Raised when the persistence boundary cannot complete a safe request."""


class TenantMembershipResolver(Protocol):
    def resolve(
        self,
        *,
        access_token: str,
        user_id: str,
        tenant_id: str,
    ) -> TenantRole: ...


class TenantEntitlementResolver(Protocol):
    def resolve(self, principal: Principal) -> TenantEntitlement: ...


class TenantRepository(Protocol):
    def get(self, principal: Principal, resource_id: str) -> TenantResource: ...

    def update(
        self,
        principal: Principal,
        resource_id: str,
        *,
        name: str,
    ) -> TenantResource: ...

    def delete(self, principal: Principal, resource_id: str) -> None: ...


class ProfileRepository(Protocol):
    def update(self, principal: Principal, request: ProfileUpdateRequest) -> Profile: ...
