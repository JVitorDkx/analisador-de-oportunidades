"""Fail-closed runtime flags for the HTTP API."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_ENVIRONMENTS = {"production", "prod"}


def demo_mode_enabled(
    environment: Mapping[str, str] | None = None,
    *,
    local_env_path: Path | None = None,
) -> bool:
    """Enable database-free analysis only in an explicitly local runtime."""

    values = environment if environment is not None else os.environ
    runtime = (
        values.get("APP_ENV")
        or values.get("ENVIRONMENT")
        or values.get("NODE_ENV")
        or "development"
    ).strip().lower()
    if runtime in PRODUCTION_ENVIRONMENTS:
        return False

    configured = values.get("ENABLE_DEMO_MODE")
    if configured is None and environment is None:
        configured = _read_local_value(
            local_env_path or PROJECT_ROOT / ".env.local",
            "ENABLE_DEMO_MODE",
        )
    return configured is not None and configured.strip().lower() == "true"


def _read_local_value(path: Path, key: str) -> str | None:
    """Read one non-secret local flag without loading arbitrary environment data."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        candidate = line.strip()
        if not candidate or candidate.startswith("#") or "=" not in candidate:
            continue
        name, value = candidate.split("=", 1)
        if name.strip() == key:
            return value.strip().strip("\"'")
    return None
