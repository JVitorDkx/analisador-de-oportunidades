from __future__ import annotations

import unittest

from .support import AUTH_A, AUTH_B, build_client


class TenantIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = build_client()

    def test_user_a_cannot_read_user_b_resource(self) -> None:
        response = self.client.get("/security/v1/resources/resource-b", headers=AUTH_A)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "resource not found")

    def test_user_a_cannot_alter_user_b_resource(self) -> None:
        attack = self.client.patch(
            "/security/v1/resources/resource-b",
            headers=AUTH_A,
            json={"name": "stolen"},
        )

        self.assertEqual(attack.status_code, 404)
        owner_read = self.client.get("/security/v1/resources/resource-b", headers=AUTH_B)
        self.assertEqual(owner_read.status_code, 200)
        self.assertEqual(owner_read.json()["name"], "B resource")

    def test_user_a_cannot_delete_user_b_resource(self) -> None:
        attack = self.client.delete("/security/v1/resources/resource-b", headers=AUTH_A)

        self.assertEqual(attack.status_code, 404)
        owner_read = self.client.get("/security/v1/resources/resource-b", headers=AUTH_B)
        self.assertEqual(owner_read.status_code, 200)

    def test_authenticated_user_can_manage_own_tenant_resource(self) -> None:
        update = self.client.patch(
            "/security/v1/resources/resource-a",
            headers=AUTH_A,
            json={"name": "A resource updated"},
        )
        self.assertEqual(update.status_code, 200, update.text)
        self.assertEqual(update.json()["tenant_id"], "tenant-a")

        delete = self.client.delete("/security/v1/resources/resource-a", headers=AUTH_A)
        self.assertEqual(delete.status_code, 204, delete.text)
        self.assertEqual(
            self.client.get("/security/v1/resources/resource-a", headers=AUTH_A).status_code,
            404,
        )

    def test_tenant_id_cannot_be_overridden_in_update_payload(self) -> None:
        response = self.client.patch(
            "/security/v1/resources/resource-a",
            headers=AUTH_A,
            json={"name": "attempt", "tenant_id": "tenant-b"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"][0]["type"], "extra_forbidden")


if __name__ == "__main__":
    unittest.main()
