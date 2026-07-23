from __future__ import annotations

import unittest

from .support import AUTH_A, build_client


class PrivilegeEscalationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = build_client()

    def test_role_cannot_be_changed_through_profile_payload(self) -> None:
        response = self.client.patch(
            "/security/v1/profile",
            headers=AUTH_A,
            json={"display_name": "Attacker", "role": "admin"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"][0]["type"], "extra_forbidden")

    def test_is_admin_mass_assignment_is_rejected(self) -> None:
        response = self.client.patch(
            "/security/v1/profile",
            headers=AUTH_A,
            json={"display_name": "Attacker", "is_admin": True},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"][0]["type"], "extra_forbidden")

    def test_allowed_profile_update_preserves_server_owned_role(self) -> None:
        response = self.client.patch(
            "/security/v1/profile",
            headers=AUTH_A,
            json={"display_name": "Safe Name"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["display_name"], "Safe Name")
        self.assertEqual(response.json()["role"], "member")
        self.assertNotIn("is_admin", response.json())

    def test_profile_update_requires_authenticated_session(self) -> None:
        response = self.client.patch(
            "/security/v1/profile",
            json={"display_name": "Anonymous"},
        )

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
