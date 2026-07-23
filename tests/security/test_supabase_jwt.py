from __future__ import annotations

import time
import unittest
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWK

from src.security.config import SecurityConfigurationError, SupabaseSettings
from src.security.identity import UnauthenticatedError
from src.security.jwt import SupabaseJwtAuthenticator, SupabaseJwtVerifier


USER_ID = "11111111-1111-4111-8111-111111111111"
SESSION_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
ISSUER = "https://example-project.supabase.co/auth/v1"
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_JWK = jwt.algorithms.RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key(), as_dict=True)
PUBLIC_JWK.update({"kid": "test-signing-key", "alg": "RS256", "use": "sig"})


class StaticKeyProvider:
    def __init__(self) -> None:
        self.signing_key = PyJWK.from_dict(PUBLIC_JWK)
        self.requested_tokens: list[str] = []

    def get_signing_key_from_jwt(self, token: str) -> PyJWK:
        self.requested_tokens.append(token)
        return self.signing_key


class RecordingMembershipResolver:
    def __init__(self, role: str = "member") -> None:
        self.role = role
        self.calls: list[dict[str, str]] = []

    def resolve(self, **kwargs: str):
        self.calls.append(kwargs)
        return self.role


def settings() -> SupabaseSettings:
    return SupabaseSettings(
        url="https://example-project.supabase.co",
        publishable_key="sb_publishable_test_public_key",
    )


def token(overrides: dict[str, Any] | None = None, *, algorithm: str = "RS256") -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": "authenticated",
        "exp": now + 300,
        "iat": now,
        "sub": USER_ID,
        "role": "authenticated",
        "aal": "aal1",
        "session_id": SESSION_ID,
        "is_anonymous": False,
    }
    claims.update(overrides or {})
    key: Any = PRIVATE_KEY if algorithm == "RS256" else "x" * 32
    return jwt.encode(
        claims,
        key,
        algorithm=algorithm,
        headers={"kid": "test-signing-key", "typ": "JWT"},
    )


class SupabaseSettingsTests(unittest.TestCase):
    def test_derives_auth_and_rest_endpoints_from_project_url(self) -> None:
        config = settings()

        self.assertEqual(config.issuer, ISSUER)
        self.assertEqual(config.jwks_url, f"{ISSUER}/.well-known/jwks.json")
        self.assertEqual(config.rest_url, "https://example-project.supabase.co/rest/v1")

    def test_rejects_secret_and_legacy_service_role_keys(self) -> None:
        with self.assertRaises(SecurityConfigurationError):
            SupabaseSettings(
                url="https://example-project.supabase.co",
                publishable_key="sb_secret_forbidden",
            )

        service_role_key = jwt.encode({"role": "service_role"}, "x" * 32, algorithm="HS256")
        with self.assertRaises(SecurityConfigurationError):
            SupabaseSettings(
                url="https://example-project.supabase.co",
                publishable_key=service_role_key,
            )

    def test_allows_http_only_for_loopback_local_development(self) -> None:
        local = SupabaseSettings(
            url="http://127.0.0.1:54321",
            publishable_key="sb_publishable_local_key",
        )
        self.assertEqual(local.url, "http://127.0.0.1:54321")

        with self.assertRaises(SecurityConfigurationError):
            SupabaseSettings(
                url="http://example-project.supabase.co",
                publishable_key="sb_publishable_test_key",
            )


class SupabaseJwtVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.key_provider = StaticKeyProvider()
        self.verifier = SupabaseJwtVerifier(
            settings(),
            key_provider=self.key_provider,
            leeway_seconds=0,
        )

    def test_verifies_signature_and_required_supabase_claims(self) -> None:
        encoded = token()

        verified = self.verifier.verify(encoded)

        self.assertEqual(verified.subject, USER_ID)
        self.assertEqual(verified.session_id, SESSION_ID)
        self.assertEqual(verified.assurance_level, "aal1")
        self.assertEqual(verified.access_token, encoded)
        self.assertEqual(self.key_provider.requested_tokens, [encoded])

    def test_rejects_expired_wrong_issuer_and_wrong_audience_tokens(self) -> None:
        invalid_tokens = (
            token({"exp": int(time.time()) - 1}),
            token({"iss": "https://attacker.invalid/auth/v1"}),
            token({"aud": "anon"}),
        )
        for encoded in invalid_tokens:
            with self.subTest(encoded=encoded[-16:]):
                with self.assertRaisesRegex(UnauthenticatedError, "valid bearer session"):
                    self.verifier.verify(encoded)

    def test_rejects_symmetric_algorithm_before_key_resolution(self) -> None:
        encoded = token(algorithm="HS256")

        with self.assertRaises(UnauthenticatedError):
            self.verifier.verify(encoded)

        self.assertEqual(self.key_provider.requested_tokens, [])

    def test_rejects_token_signed_by_an_untrusted_asymmetric_key(self) -> None:
        attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        unverified_claims = jwt.decode(token(), options={"verify_signature": False})
        forged = jwt.encode(
            unverified_claims,
            attacker_key,
            algorithm="RS256",
            headers={"kid": "test-signing-key", "typ": "JWT"},
        )

        with self.assertRaises(UnauthenticatedError):
            self.verifier.verify(forged)

    def test_rejects_privileged_anonymous_and_incomplete_tokens(self) -> None:
        invalid_tokens = (
            token({"role": "service_role"}),
            token({"is_anonymous": True}),
            token({"sub": "not-a-uuid"}),
            token({"session_id": "not-a-uuid"}),
            token({"aal": "aal3"}),
        )
        incomplete_claims = {"is_anonymous": None}
        invalid_tokens += (token(incomplete_claims),)

        for encoded in invalid_tokens:
            with self.subTest(encoded=encoded[-16:]):
                with self.assertRaises(UnauthenticatedError):
                    self.verifier.verify(encoded)


class SupabaseJwtAuthenticatorTests(unittest.TestCase):
    def test_resolves_selected_tenant_from_database_membership(self) -> None:
        resolver = RecordingMembershipResolver(role="owner")
        authenticator = SupabaseJwtAuthenticator(
            SupabaseJwtVerifier(settings(), key_provider=StaticKeyProvider()),
            resolver,
        )
        encoded = token()

        principal = authenticator.authenticate(f"Bearer {encoded}", TENANT_ID)

        self.assertEqual(principal.user_id, USER_ID)
        self.assertEqual(principal.tenant_id, TENANT_ID)
        self.assertEqual(principal.role, "owner")
        self.assertEqual(principal.access_token, encoded)
        self.assertNotIn("access_token", principal.model_dump())
        self.assertNotIn(encoded, repr(principal))
        self.assertEqual(
            resolver.calls,
            [{"access_token": encoded, "user_id": USER_ID, "tenant_id": TENANT_ID}],
        )

    def test_rejects_missing_or_malformed_tenant_selector(self) -> None:
        resolver = RecordingMembershipResolver()
        authenticator = SupabaseJwtAuthenticator(
            SupabaseJwtVerifier(settings(), key_provider=StaticKeyProvider()),
            resolver,
        )

        for tenant_id in (None, "", "attacker-tenant"):
            with self.subTest(tenant_id=tenant_id):
                with self.assertRaises(UnauthenticatedError):
                    authenticator.authenticate(f"Bearer {token()}", tenant_id)

        self.assertEqual(resolver.calls, [])

    def test_rejects_non_bearer_authorization(self) -> None:
        authenticator = SupabaseJwtAuthenticator(
            SupabaseJwtVerifier(settings(), key_provider=StaticKeyProvider()),
            RecordingMembershipResolver(),
        )

        for authorization in (None, "", "Basic credentials", "Bearer token with-spaces"):
            with self.subTest(authorization=authorization):
                with self.assertRaises(UnauthenticatedError):
                    authenticator.authenticate(authorization, TENANT_ID)


if __name__ == "__main__":
    unittest.main()
