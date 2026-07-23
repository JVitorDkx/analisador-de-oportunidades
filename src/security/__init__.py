"""Reusable default-deny controls for future SaaS boundaries."""

from src.security.app import create_security_app

__all__ = ["create_security_app"]
