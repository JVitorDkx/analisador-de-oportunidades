"""User-token-bound repositories for the Supabase PostgREST Data API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID

import httpx2

from src.security.config import SupabaseSettings
from src.security.identity import UnauthenticatedError
from src.security.models import Principal, Profile, ProfileUpdateRequest, TenantResource
from src.security.repositories.contracts import SecurityRepositoryUnavailable, TenantRole
from src.security.tenancy import TenantResourceNotFound


class ResponseLike(Protocol):
    status_code: int

    def json(self) -> Any: ...


class HttpClientLike(Protocol):
    def request(self, method: str, url: str, **kwargs: Any) -> ResponseLike: ...


class PostgrestRequestError(RuntimeError):
    """Base class for sanitized Data API failures."""


class PostgrestAccessDenied(PostgrestRequestError):
    """The Data API rejected the supplied user token or operation."""


class PostgrestUnavailable(PostgrestRequestError):
    """The Data API was unavailable or returned an invalid response."""


class SupabasePostgrestClient:
    """Issue stateless requests with a publishable key and one user's JWT."""

    def __init__(
        self,
        settings: SupabaseSettings,
        *,
        http_client: HttpClientLike | None = None,
    ) -> None:
        self._settings = settings
        self._http_client = http_client or httpx2.Client(
            timeout=5.0,
            follow_redirects=False,
        )

    def rows(
        self,
        method: str,
        table: str,
        *,
        access_token: str,
        params: Mapping[str, str],
        payload: Mapping[str, Any] | None = None,
        return_representation: bool = False,
    ) -> list[dict[str, Any]]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "apikey": self._settings.publishable_key,
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if return_representation:
            headers["Prefer"] = "return=representation"

        try:
            response = self._http_client.request(
                method,
                f"{self._settings.rest_url}/{table}",
                headers=headers,
                params=dict(params),
                json=dict(payload) if payload is not None else None,
            )
        except httpx2.HTTPError as exc:
            raise PostgrestUnavailable("Supabase Data API is unavailable") from exc

        if response.status_code in {401, 403}:
            raise PostgrestAccessDenied("Supabase Data API denied the request")
        if response.status_code >= 500:
            raise PostgrestUnavailable("Supabase Data API is unavailable")
        if response.status_code >= 400:
            raise PostgrestRequestError("Supabase Data API rejected the request")
        try:
            data = response.json()
        except (TypeError, ValueError) as exc:
            raise PostgrestUnavailable("Supabase Data API returned an invalid response") from exc
        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            raise PostgrestUnavailable("Supabase Data API returned an invalid response")
        return data


class SupabaseTenantMembershipResolver:
    """Resolve tenant authority from RLS-protected membership rows."""

    def __init__(self, client: SupabasePostgrestClient) -> None:
        self._client = client

    def resolve(
        self,
        *,
        access_token: str,
        user_id: str,
        tenant_id: str,
    ) -> TenantRole:
        try:
            rows = self._client.rows(
                "GET",
                "tenant_memberships",
                access_token=access_token,
                params={
                    "select": "role",
                    "tenant_id": f"eq.{tenant_id}",
                    "user_id": f"eq.{user_id}",
                    "limit": "1",
                },
            )
        except PostgrestAccessDenied as exc:
            raise UnauthenticatedError("a valid bearer session is required") from exc
        except (PostgrestRequestError, PostgrestUnavailable) as exc:
            raise SecurityRepositoryUnavailable("tenant membership could not be verified") from exc

        if len(rows) != 1 or rows[0].get("role") not in {"owner", "admin", "member"}:
            raise UnauthenticatedError("a valid bearer session is required")
        return rows[0]["role"]


class SupabaseTenantRepository:
    """CRUD projects through explicit tenant filters plus database RLS."""

    def __init__(self, client: SupabasePostgrestClient) -> None:
        self._client = client

    def get(self, principal: Principal, resource_id: str) -> TenantResource:
        rows = self._project_rows("GET", principal, resource_id)
        return _one_project(rows)

    def update(
        self,
        principal: Principal,
        resource_id: str,
        *,
        name: str,
    ) -> TenantResource:
        rows = self._project_rows(
            "PATCH",
            principal,
            resource_id,
            payload={"name": name},
            return_representation=True,
        )
        return _one_project(rows)

    def delete(self, principal: Principal, resource_id: str) -> None:
        rows = self._project_rows(
            "DELETE",
            principal,
            resource_id,
            return_representation=True,
        )
        _one_project(rows)

    def _project_rows(
        self,
        method: str,
        principal: Principal,
        resource_id: str,
        *,
        payload: Mapping[str, Any] | None = None,
        return_representation: bool = False,
    ) -> list[dict[str, Any]]:
        try:
            normalized_resource_id = str(UUID(resource_id))
            normalized_tenant_id = str(UUID(principal.tenant_id))
        except ValueError as exc:
            raise TenantResourceNotFound("resource not found") from exc
        try:
            return self._client.rows(
                method,
                "projects",
                access_token=_access_token(principal),
                params={
                    "select": "id,tenant_id,name",
                    "id": f"eq.{normalized_resource_id}",
                    "tenant_id": f"eq.{normalized_tenant_id}",
                    "limit": "1",
                },
                payload=payload,
                return_representation=return_representation,
            )
        except PostgrestAccessDenied as exc:
            raise TenantResourceNotFound("resource not found") from exc
        except (PostgrestRequestError, PostgrestUnavailable) as exc:
            raise SecurityRepositoryUnavailable("tenant repository is unavailable") from exc


class SupabaseProfileRepository:
    """Update only the profile field exposed by the strict HTTP DTO."""

    def __init__(self, client: SupabasePostgrestClient) -> None:
        self._client = client

    def update(self, principal: Principal, request: ProfileUpdateRequest) -> Profile:
        try:
            rows = self._client.rows(
                "PATCH",
                "profiles",
                access_token=_access_token(principal),
                params={
                    "select": "user_id,display_name",
                    "user_id": f"eq.{principal.user_id}",
                    "limit": "1",
                },
                payload={"display_name": request.display_name},
                return_representation=True,
            )
        except PostgrestAccessDenied as exc:
            raise UnauthenticatedError("a valid bearer session is required") from exc
        except (PostgrestRequestError, PostgrestUnavailable) as exc:
            raise SecurityRepositoryUnavailable("profile repository is unavailable") from exc
        if len(rows) != 1:
            raise UnauthenticatedError("profile does not match the authenticated session")
        row = rows[0]
        try:
            return Profile(
                user_id=row["user_id"],
                tenant_id=principal.tenant_id,
                display_name=row["display_name"],
                role=principal.role,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SecurityRepositoryUnavailable("profile repository returned invalid data") from exc


def _one_project(rows: list[dict[str, Any]]) -> TenantResource:
    if len(rows) != 1:
        raise TenantResourceNotFound("resource not found")
    row = rows[0]
    try:
        return TenantResource(
            resource_id=row["id"],
            tenant_id=row["tenant_id"],
            name=row["name"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SecurityRepositoryUnavailable("tenant repository returned invalid data") from exc


def _access_token(principal: Principal) -> str:
    if principal.access_token is None:
        raise UnauthenticatedError("a valid bearer session is required")
    return principal.access_token
