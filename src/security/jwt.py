"""Strict verification of Supabase Auth access tokens through project JWKS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from src.security.config import SupabaseSettings
from src.security.identity import UnauthenticatedError
from src.security.models import Principal
from src.security.repositories.contracts import TenantMembershipResolver


GENERIC_AUTHENTICATION_ERROR = "a valid bearer session is required"
ALLOWED_JWT_ALGORITHMS = ("ES256", "RS256")


class SigningKeyProvider(Protocol):
    """Resolve a verified public signing key for a JWT."""

    def get_signing_key_from_jwt(self, token: str) -> Any: ...


@dataclass(frozen=True, slots=True)
class VerifiedSupabaseToken:
    """Minimal trusted claims retained after signature and claim validation."""

    subject: str
    access_token: str
    session_id: str
    assurance_level: str


class SupabaseJwtVerifier:
    """Verify asymmetric Supabase JWTs without trusting unverified metadata."""

    def __init__(
        self,
        settings: SupabaseSettings,
        *,
        key_provider: SigningKeyProvider | None = None,
        leeway_seconds: int = 30,
    ) -> None:
        if leeway_seconds < 0 or leeway_seconds > 120:
            raise ValueError("JWT leeway must be between 0 and 120 seconds")
        self._settings = settings
        self._leeway_seconds = leeway_seconds
        # Cache the JWKS response for at most the edge cache window, but avoid
        # PyJWKClient's non-expiring per-key LRU so revoked keys age out.
        self._key_provider = key_provider or PyJWKClient(
            settings.jwks_url,
            cache_keys=False,
            cache_jwk_set=True,
            lifespan=600,
            timeout=5,
        )

    def verify(self, access_token: str) -> VerifiedSupabaseToken:
        try:
            header = jwt.get_unverified_header(access_token)
            algorithm = header.get("alg")
            key_id = header.get("kid")
            token_type = header.get("typ")
            if algorithm not in ALLOWED_JWT_ALGORITHMS:
                raise InvalidTokenError("JWT algorithm is not allowed")
            if not isinstance(key_id, str) or not key_id:
                raise InvalidTokenError("JWT key identifier is required")
            if token_type not in {None, "JWT"}:
                raise InvalidTokenError("JWT type is invalid")

            signing_key = self._key_provider.get_signing_key_from_jwt(access_token)
            claims = jwt.decode(
                access_token,
                key=signing_key.key,
                algorithms=list(ALLOWED_JWT_ALGORITHMS),
                audience=self._settings.audience,
                issuer=self._settings.issuer,
                leeway=self._leeway_seconds,
                options={
                    "require": [
                        "iss",
                        "aud",
                        "exp",
                        "iat",
                        "sub",
                        "role",
                        "aal",
                        "session_id",
                        "is_anonymous",
                    ]
                },
            )
            if claims["role"] != "authenticated" or claims["is_anonymous"] is not False:
                raise InvalidTokenError("JWT does not represent an authenticated user")
            if claims["aal"] not in {"aal1", "aal2"}:
                raise InvalidTokenError("JWT assurance level is invalid")

            subject = str(UUID(claims["sub"]))
            session_id = str(UUID(claims["session_id"]))
        except (
            InvalidTokenError,
            PyJWKClientError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise UnauthenticatedError(GENERIC_AUTHENTICATION_ERROR) from exc

        return VerifiedSupabaseToken(
            subject=subject,
            access_token=access_token,
            session_id=session_id,
            assurance_level=claims["aal"],
        )


class SupabaseJwtAuthenticator:
    """Combine a verified user JWT with database-authoritative tenant membership."""

    def __init__(
        self,
        verifier: SupabaseJwtVerifier,
        membership_resolver: TenantMembershipResolver,
    ) -> None:
        self._verifier = verifier
        self._membership_resolver = membership_resolver

    def authenticate(
        self,
        authorization: str | None,
        tenant_id: str | None = None,
    ) -> Principal:
        token = _bearer_token(authorization)
        if not tenant_id:
            raise UnauthenticatedError(GENERIC_AUTHENTICATION_ERROR)
        try:
            normalized_tenant_id = str(UUID(tenant_id))
        except (ValueError, AttributeError) as exc:
            raise UnauthenticatedError(GENERIC_AUTHENTICATION_ERROR) from exc

        verified = self._verifier.verify(token)
        role = self._membership_resolver.resolve(
            access_token=verified.access_token,
            user_id=verified.subject,
            tenant_id=normalized_tenant_id,
        )
        return Principal(
            user_id=verified.subject,
            tenant_id=normalized_tenant_id,
            role=role,
            access_token=verified.access_token,
        )


def _bearer_token(authorization: str | None) -> str:
    scheme, separator, token = (authorization or "").partition(" ")
    if not separator or scheme.lower() != "bearer" or not token or " " in token:
        raise UnauthenticatedError(GENERIC_AUTHENTICATION_ERROR)
    return token
