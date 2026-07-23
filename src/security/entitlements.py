"""Server-authoritative tenant entitlement resolution."""

from __future__ import annotations

from collections.abc import Mapping

from src.security.identity import UnauthenticatedError
from src.security.models import Principal, TenantEntitlement


class StaticEntitlementResolver:
    """Deterministic entitlement adapter for isolated tests."""

    def __init__(self, entitlements: Mapping[str, TenantEntitlement]) -> None:
        self._entitlements = dict(entitlements)

    def resolve(self, principal: Principal) -> TenantEntitlement:
        try:
            return self._entitlements[principal.tenant_id]
        except KeyError as exc:
            raise UnauthenticatedError("a valid bearer session is required") from exc
