"""Validated environment configuration for Supabase user-scoped access."""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit


class SecurityConfigurationError(ValueError):
    """Raised when required security configuration is absent or unsafe."""


def _legacy_api_key_role(value: str) -> str | None:
    parts = value.split(".")
    if len(parts) != 3:
        return None
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
        claims = json.loads(decoded)
    except (UnicodeEncodeError, ValueError, json.JSONDecodeError):
        return None
    role = claims.get("role") if isinstance(claims, dict) else None
    return role if isinstance(role, str) else None


@dataclass(frozen=True, slots=True)
class SupabaseSettings:
    """Only public Supabase coordinates accepted by user-scoped repositories."""

    url: str
    publishable_key: str
    audience: str = "authenticated"

    def __post_init__(self) -> None:
        normalized_url = self.url.rstrip("/")
        parsed = urlsplit(normalized_url)
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise SecurityConfigurationError("SUPABASE_URL must be an absolute project URL")
        is_loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and is_loopback):
            raise SecurityConfigurationError("SUPABASE_URL must use HTTPS outside local development")
        if parsed.path not in {"", "/"}:
            raise SecurityConfigurationError("SUPABASE_URL must not contain a path")

        key = self.publishable_key.strip()
        if not key:
            raise SecurityConfigurationError("SUPABASE_PUBLISHABLE_KEY is required")
        if key.startswith("sb_secret_"):
            raise SecurityConfigurationError("secret Supabase keys cannot be used for user repositories")
        if key.startswith("sb_publishable_"):
            pass
        else:
            legacy_role = _legacy_api_key_role(key)
            if legacy_role != "anon":
                raise SecurityConfigurationError("only publishable or legacy anon keys are accepted")

        audience = self.audience.strip()
        if audience != "authenticated":
            raise SecurityConfigurationError("Supabase user JWT audience must be authenticated")

        object.__setattr__(self, "url", normalized_url)
        object.__setattr__(self, "publishable_key", key)
        object.__setattr__(self, "audience", audience)

    @property
    def issuer(self) -> str:
        return f"{self.url}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"

    @property
    def rest_url(self) -> str:
        return f"{self.url}/rest/v1"

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] = os.environ,
    ) -> SupabaseSettings:
        try:
            url = environment["SUPABASE_URL"]
            publishable_key = environment["SUPABASE_PUBLISHABLE_KEY"]
        except KeyError as exc:
            raise SecurityConfigurationError(f"missing required setting: {exc.args[0]}") from exc
        return cls(
            url=url,
            publishable_key=publishable_key,
            audience=environment.get("SUPABASE_JWT_AUDIENCE", "authenticated"),
        )
