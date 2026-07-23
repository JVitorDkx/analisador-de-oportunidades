"""Tenant-scoped repositories that deny cross-tenant object access."""

from __future__ import annotations

from collections.abc import Iterable

from src.security.models import Principal, TenantResource


class TenantResourceNotFound(LookupError):
    """Returned for absent and cross-tenant resources to avoid ID disclosure."""


class InMemoryTenantRepository:
    """Reference repository that applies tenant filtering to every operation."""

    def __init__(self, resources: Iterable[TenantResource] = ()) -> None:
        self._resources: dict[tuple[str, str], TenantResource] = {}
        for resource in resources:
            key = (resource.tenant_id, resource.resource_id)
            if key in self._resources:
                raise ValueError(f"duplicate tenant resource: {key}")
            self._resources[key] = resource

    def get(self, principal: Principal, resource_id: str) -> TenantResource:
        key = (principal.tenant_id, resource_id)
        try:
            return self._resources[key]
        except KeyError as exc:
            raise TenantResourceNotFound("resource not found") from exc

    def update(self, principal: Principal, resource_id: str, *, name: str) -> TenantResource:
        current = self.get(principal, resource_id)
        updated = current.model_copy(update={"name": name})
        self._resources[(principal.tenant_id, resource_id)] = updated
        return updated

    def delete(self, principal: Principal, resource_id: str) -> None:
        self.get(principal, resource_id)
        del self._resources[(principal.tenant_id, resource_id)]
