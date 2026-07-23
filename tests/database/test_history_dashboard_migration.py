from __future__ import annotations

import unittest
from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "202607230006_history_dashboard_rpcs.sql"
)


class HistoryDashboardMigrationTests(unittest.TestCase):
    def test_history_functions_are_tenant_bound_and_hardened(self) -> None:
        sql = MIGRATION.read_text(encoding="utf-8").lower()
        self.assertEqual(sql.count("security definer"), 3)
        self.assertEqual(sql.count("set search_path = ''"), 3)
        self.assertGreaterEqual(sql.count("private.is_tenant_member(target_tenant_id)"), 3)
        self.assertIn("analysis.tenant_id = target_tenant_id", sql)

    def test_free_retention_and_server_quota_are_applied(self) -> None:
        sql = MIGRATION.read_text(encoding="utf-8").lower()
        self.assertIn("private.tenant_entitlement(target_tenant_id)", sql)
        self.assertIn("make_interval(days => retention_days)", sql)
        self.assertIn("analysis_quota_ledger", sql)
        self.assertIn("status in ('reserved', 'consumed')", sql)

    def test_only_authenticated_role_can_execute(self) -> None:
        sql = MIGRATION.read_text(encoding="utf-8").lower()
        self.assertEqual(sql.count("grant execute on function"), 3)
        self.assertEqual(sql.count("from public, anon"), 3)


if __name__ == "__main__":
    unittest.main()
