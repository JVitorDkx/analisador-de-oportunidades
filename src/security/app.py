"""Isolated HTTP boundary used to prove future SaaS security invariants."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status

from src.security.identity import ProfileService, StaticSessionAuthenticator, UnauthenticatedError
from src.security.models import (
    CheckoutRequest,
    CheckoutResponse,
    Principal,
    Profile,
    ProfileUpdateRequest,
    ResourceUpdateRequest,
    TenantResource,
    WebhookAcceptedResponse,
)
from src.security.pricing import CheckoutService, UnknownPlanError
from src.security.tenancy import InMemoryTenantRepository, TenantResourceNotFound
from src.security.webhooks import InvalidWebhookSignature, WebhookVerifier


def create_security_app(
    *,
    checkout_service: CheckoutService,
    webhook_verifier: WebhookVerifier,
    authenticator: StaticSessionAuthenticator,
    tenant_repository: InMemoryTenantRepository,
    profile_service: ProfileService,
) -> FastAPI:
    """Create an isolated reference boundary without changing the v1 API."""

    application = FastAPI(title="SaaS Security Boundary", docs_url=None, redoc_url=None)

    def authenticated_principal(
        authorization: Annotated[str | None, Header()] = None,
    ) -> Principal:
        try:
            return authenticator.authenticate(authorization)
        except UnauthenticatedError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    @application.post(
        "/security/v1/checkout",
        response_model=CheckoutResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_checkout(
        payload: CheckoutRequest,
        _principal: Principal = Depends(authenticated_principal),
    ) -> CheckoutResponse:
        try:
            return checkout_service.create(payload)
        except UnknownPlanError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

    @application.post(
        "/security/v1/webhooks/provider",
        response_model=WebhookAcceptedResponse,
    )
    async def receive_webhook(
        request: Request,
        x_webhook_signature: Annotated[str | None, Header()] = None,
    ) -> WebhookAcceptedResponse:
        raw_body = await request.body()
        try:
            webhook_verifier.verify(raw_body, x_webhook_signature)
        except InvalidWebhookSignature as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        return WebhookAcceptedResponse(accepted=True)

    @application.get("/security/v1/resources/{resource_id}", response_model=TenantResource)
    def get_resource(
        resource_id: str,
        principal: Principal = Depends(authenticated_principal),
    ) -> TenantResource:
        try:
            return tenant_repository.get(principal, resource_id)
        except TenantResourceNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @application.patch("/security/v1/resources/{resource_id}", response_model=TenantResource)
    def update_resource(
        resource_id: str,
        payload: ResourceUpdateRequest,
        principal: Principal = Depends(authenticated_principal),
    ) -> TenantResource:
        try:
            return tenant_repository.update(principal, resource_id, name=payload.name)
        except TenantResourceNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @application.delete(
        "/security/v1/resources/{resource_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_resource(
        resource_id: str,
        principal: Principal = Depends(authenticated_principal),
    ) -> Response:
        try:
            tenant_repository.delete(principal, resource_id)
        except TenantResourceNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.patch("/security/v1/profile", response_model=Profile)
    def update_profile(
        payload: ProfileUpdateRequest,
        principal: Principal = Depends(authenticated_principal),
    ) -> Profile:
        try:
            return profile_service.update(principal, payload)
        except UnauthenticatedError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return application
