"""HMAC verification for raw webhook payloads."""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable


class InvalidWebhookSignature(ValueError):
    """Raised for a missing, malformed, stale, or invalid signature."""


class WebhookVerifier:
    """Verify `t=<unix>,v1=<hex>` signatures over timestamp and raw body."""

    def __init__(
        self,
        secret: bytes,
        *,
        tolerance_seconds: int = 300,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if len(secret) < 32:
            raise ValueError("webhook secret must contain at least 32 bytes")
        if tolerance_seconds <= 0:
            raise ValueError("webhook tolerance must be positive")
        self._secret = secret
        self._tolerance_seconds = tolerance_seconds
        self._clock = clock

    def verify(self, raw_body: bytes, signature_header: str | None) -> None:
        timestamp, supplied_signature = self._parse(signature_header)
        if abs(int(self._clock()) - timestamp) > self._tolerance_seconds:
            raise InvalidWebhookSignature("webhook signature timestamp is outside tolerance")

        signed_payload = str(timestamp).encode("ascii") + b"." + raw_body
        expected_signature = hmac.new(
            self._secret,
            signed_payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, supplied_signature):
            raise InvalidWebhookSignature("webhook signature does not match")

    @staticmethod
    def _parse(signature_header: str | None) -> tuple[int, str]:
        if not signature_header:
            raise InvalidWebhookSignature("webhook signature is required")

        parts: dict[str, str] = {}
        for component in signature_header.split(","):
            key, separator, value = component.strip().partition("=")
            if not separator or not key or not value or key in parts:
                raise InvalidWebhookSignature("webhook signature is malformed")
            parts[key] = value
        if set(parts) != {"t", "v1"}:
            raise InvalidWebhookSignature("webhook signature fields are invalid")
        try:
            timestamp = int(parts["t"])
            bytes.fromhex(parts["v1"])
        except (ValueError, KeyError) as exc:
            raise InvalidWebhookSignature("webhook signature is malformed") from exc
        if timestamp < 0 or len(parts["v1"]) != hashlib.sha256().digest_size * 2:
            raise InvalidWebhookSignature("webhook signature is malformed")
        return timestamp, parts["v1"]
