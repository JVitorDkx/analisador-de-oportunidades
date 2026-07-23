"""Strict DTOs for the isolated SaaS security boundary."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


NonEmptyString = Annotated[str, Field(min_length=1, max_length=128)]
PlanId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,63}$")]
Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class StrictSecurityModel(BaseModel):
    """Reject fields that are not explicitly part of a security contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Plan(StrictSecurityModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    plan_id: PlanId
    amount_minor: Annotated[int, Field(gt=0)]
    currency: Currency


class CheckoutRequest(StrictSecurityModel):
    plan_id: PlanId


class CheckoutResponse(StrictSecurityModel):
    plan_id: PlanId
    amount_minor: Annotated[int, Field(gt=0)]
    currency: Currency
    pricing_source: Literal["server_catalog"]


class Principal(StrictSecurityModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    user_id: NonEmptyString
    tenant_id: NonEmptyString
    role: Literal["owner", "admin", "member"]
    access_token: Annotated[str | None, Field(min_length=1, exclude=True, repr=False)] = None


class TenantResource(StrictSecurityModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    resource_id: NonEmptyString
    tenant_id: NonEmptyString
    name: NonEmptyString


class ResourceUpdateRequest(StrictSecurityModel):
    name: NonEmptyString


class Profile(StrictSecurityModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    user_id: NonEmptyString
    tenant_id: NonEmptyString
    display_name: NonEmptyString
    role: Literal["owner", "admin", "member"]


class ProfileUpdateRequest(StrictSecurityModel):
    display_name: NonEmptyString


class WebhookAcceptedResponse(StrictSecurityModel):
    accepted: Literal[True]
