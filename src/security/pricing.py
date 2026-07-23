"""Server-authoritative pricing controls."""

from __future__ import annotations

from collections.abc import Iterable

from src.security.models import CheckoutRequest, CheckoutResponse, Plan


class UnknownPlanError(ValueError):
    """Raised when a client selects a plan absent from the official catalog."""


class PlanCatalog:
    """Immutable server-side view of the plans authorized for checkout."""

    def __init__(self, plans: Iterable[Plan]) -> None:
        entries: dict[str, Plan] = {}
        for plan in plans:
            if plan.plan_id in entries:
                raise ValueError(f"duplicate plan_id: {plan.plan_id}")
            entries[plan.plan_id] = plan
        if not entries:
            raise ValueError("at least one official plan is required")
        self._entries = entries

    def resolve(self, plan_id: str) -> Plan:
        try:
            return self._entries[plan_id]
        except KeyError as exc:
            raise UnknownPlanError("the selected plan is not authorized") from exc


class CheckoutService:
    """Create checkout values exclusively from the official server catalog."""

    def __init__(self, catalog: PlanCatalog) -> None:
        self._catalog = catalog

    def create(self, request: CheckoutRequest) -> CheckoutResponse:
        plan = self._catalog.resolve(request.plan_id)
        return CheckoutResponse(
            plan_id=plan.plan_id,
            amount_minor=plan.amount_minor,
            currency=plan.currency,
            pricing_source="server_catalog",
        )
