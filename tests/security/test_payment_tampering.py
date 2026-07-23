from __future__ import annotations

import unittest

from .support import AUTH_A, build_client


class PaymentTamperingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = build_client()

    def test_checkout_uses_price_and_currency_from_official_server_catalog(self) -> None:
        response = self.client.post(
            "/security/v1/checkout",
            json={"plan_id": "basic-monthly"},
            headers=AUTH_A,
        )

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(
            response.json(),
            {
                "plan_id": "basic-monthly",
                "amount_minor": 4900,
                "currency": "BRL",
                "pricing_source": "server_catalog",
            },
        )

    def test_client_supplied_price_is_rejected_instead_of_trusted(self) -> None:
        response = self.client.post(
            "/security/v1/checkout",
            json={
                "plan_id": "basic-monthly",
                "price": 0,
                "amount_minor": 1,
                "currency": "BRL",
            },
            headers=AUTH_A,
        )

        self.assertEqual(response.status_code, 422)
        error_types = {error["type"] for error in response.json()["detail"]}
        self.assertEqual(error_types, {"extra_forbidden"})

    def test_plan_absent_from_official_catalog_is_rejected(self) -> None:
        response = self.client.post(
            "/security/v1/checkout",
            json={"plan_id": "forged-free-plan"},
            headers=AUTH_A,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "the selected plan is not authorized")

    def test_checkout_requires_authenticated_server_session(self) -> None:
        response = self.client.post(
            "/security/v1/checkout",
            json={"plan_id": "basic-monthly"},
        )

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
