from __future__ import annotations

import unittest

from .support import NOW, build_client, webhook_signature


class WebhookSignatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = build_client()
        self.body = b'{"id":"event-001","type":"payment.confirmed"}'

    def post(self, body: bytes, signature: str | None = None):
        headers = {"Content-Type": "application/json"}
        if signature is not None:
            headers["X-Webhook-Signature"] = signature
        return self.client.post(
            "/security/v1/webhooks/provider",
            content=body,
            headers=headers,
        )

    def test_webhook_without_signature_returns_401(self) -> None:
        response = self.post(self.body)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "webhook signature is required")

    def test_webhook_with_invalid_signature_returns_401(self) -> None:
        response = self.post(self.body, f"t={NOW},v1={'0' * 64}")

        self.assertEqual(response.status_code, 401)

    def test_signature_for_different_raw_body_returns_401(self) -> None:
        signature = webhook_signature(self.body)

        response = self.post(self.body + b" ", signature)

        self.assertEqual(response.status_code, 401)

    def test_expired_signature_returns_401(self) -> None:
        stale_timestamp = NOW - 301

        response = self.post(
            self.body,
            webhook_signature(self.body, timestamp=stale_timestamp),
        )

        self.assertEqual(response.status_code, 401)

    def test_valid_signature_is_accepted(self) -> None:
        response = self.post(self.body, webhook_signature(self.body))

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"accepted": True})


if __name__ == "__main__":
    unittest.main()
