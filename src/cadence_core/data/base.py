"""Shared data primitives."""

from __future__ import annotations


class DataError(RuntimeError):
    """Raised when a data source cannot be reached or returns unusable data."""
