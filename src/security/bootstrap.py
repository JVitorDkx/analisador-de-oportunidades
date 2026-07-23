"""Production composition for Supabase authentication and persistence."""

from __future__ import annotations

from dataclasses import dataclass

from src.security.config import SupabaseSettings
from src.security.jwt import SupabaseJwtAuthenticator, SupabaseJwtVerifier
from src.security.repositories.supabase import (
    SupabasePostgrestClient,
    SupabaseProfileRepository,
    SupabaseTenantMembershipResolver,
    SupabaseTenantRepository,
)


@dataclass(frozen=True, slots=True)
class SupabaseSecurityDependencies:
    authenticator: SupabaseJwtAuthenticator
    tenant_repository: SupabaseTenantRepository
    profile_repository: SupabaseProfileRepository


def build_supabase_security_dependencies(
    settings: SupabaseSettings | None = None,
) -> SupabaseSecurityDependencies:
    """Build stateless user-scoped dependencies from validated configuration."""

    resolved_settings = settings or SupabaseSettings.from_environment()
    client = SupabasePostgrestClient(resolved_settings)
    membership_resolver = SupabaseTenantMembershipResolver(client)
    return SupabaseSecurityDependencies(
        authenticator=SupabaseJwtAuthenticator(
            SupabaseJwtVerifier(resolved_settings),
            membership_resolver,
        ),
        tenant_repository=SupabaseTenantRepository(client),
        profile_repository=SupabaseProfileRepository(client),
    )
