from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = PROJECT_ROOT / "supabase" / "migrations"


def migration(name: str) -> str:
    return (MIGRATIONS / name).read_text(encoding="utf-8").lower()


class AnalysisHistorySchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.history = migration("202607230001_analysis_history.sql")
        cls.quota = migration("202607230002_entitlements_and_quota.sql")
        cls.rls = migration("202607230003_analysis_rls_policies.sql")

    def test_history_schema_is_tenant_scoped_and_idempotent(self) -> None:
        self.assertIn("create table if not exists public.analyses", self.history)
        self.assertIn("create table if not exists public.analysis_advanced_details", self.history)
        self.assertIn("unique (tenant_id, idempotency_key)", self.history)
        self.assertIn("unique (tenant_id, client_analysis_id)", self.history)
        self.assertIn("foreign key (tenant_id, parent_analysis_id)", self.history)
        self.assertIn("references public.analyses (tenant_id, id)", self.history)
        self.assertIn("check (official_score is null or official_score between 0 and 100)", self.history)
        self.assertIn("check (jsonb_typeof(input_payload) = 'object')", self.history)
        self.assertIn("check (jsonb_typeof(result_payload) = 'object')", self.history)

    def test_versioned_free_and_pro_limits_are_server_seeded(self) -> None:
        self.assertIn("create table if not exists public.billing_plans", self.history)
        self.assertIn("('free', 'free', 3, 30, true)", self.history)
        self.assertIn("('pro', 'pro', 100, null, true)", self.history)
        self.assertIn("on conflict (plan_id) do update", self.history)
        self.assertIn("clients cannot mutate pricing or entitlements", self.history)

    def test_quota_reservation_is_atomic_and_idempotent(self) -> None:
        self.assertIn("create table if not exists public.analysis_quota_ledger", self.quota)
        self.assertIn("unique (tenant_id, idempotency_key)", self.quota)
        self.assertIn("pg_advisory_xact_lock", self.quota)
        self.assertIn("status in ('reserved', 'consumed', 'released')", self.quota)
        self.assertIn("ledger.status in ('reserved', 'consumed')", self.quota)
        self.assertIn("if existing_reservation.id is not null", self.quota)
        self.assertIn("existing_reservation.user_id <> auth.uid()", self.quota)
        self.assertIn("existing_reservation.status", self.quota)
        self.assertIn("existing_reservation.analysis_id", self.quota)
        self.assertIn("analysis quota exceeded", self.quota)

    def test_entitlement_and_quota_functions_verify_membership(self) -> None:
        self.assertIn("private.is_tenant_member(target_tenant_id)", self.quota)
        self.assertGreaterEqual(
            self.quota.count("membership.user_id = auth.uid()"),
            2,
        )
        function_headers = re.findall(
            r"create or replace function private\.(?:tenant_entitlement|reserve_analysis_quota|finalize_analysis_quota).*?as \$\$",
            self.quota,
            flags=re.DOTALL,
        )
        self.assertEqual(len(function_headers), 3)
        for header in function_headers:
            self.assertIn("security definer", header)
            self.assertIn("set search_path = ''", header)

    def test_all_new_tables_have_forced_rls(self) -> None:
        for table in (
            "billing_plans",
            "analyses",
            "analysis_advanced_details",
            "analysis_quota_ledger",
        ):
            self.assertIn(f"alter table public.{table} enable row level security", self.rls)
            self.assertIn(f"alter table public.{table} force row level security", self.rls)
            self.assertIn(f"revoke all on table public.{table} from anon, authenticated", self.rls)

    def test_advanced_payload_requires_both_membership_and_pro_tier(self) -> None:
        policy = re.search(
            r"create policy analysis_advanced_details_select_pro.*?\);",
            self.rls,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(policy)
        assert policy is not None
        self.assertIn("private.is_tenant_member(tenant_id)", policy.group())
        self.assertIn("entitlement.tier = 'pro'", policy.group())

    def test_authenticated_role_has_no_direct_write_grants(self) -> None:
        self.assertNotRegex(
            self.rls,
            r"grant\s+(?:insert|update|delete|all).*?to authenticated",
        )
        self.assertIn("grant select (", self.rls)
        self.assertNotIn("input_payload,", self.rls)
        self.assertNotIn("result_payload,", self.rls)


if __name__ == "__main__":
    unittest.main()
