"""Middleware module for vehicle inspection API."""

from .auth import get_current_inspector, auth_required

__all__ = ["get_current_inspector", "auth_required"]
