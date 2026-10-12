"""Cadence core — asset-agnostic building blocks for the Cadence trading platform.

This package is deliberately dependency-light: a pure-Python judgment layer, a
Brier/ECE calibration layer, a context digest, a standard-library HTTP layer with
an on-disk cache and a rate limiter, and a **macro context engine** that supplies
structured macro data and curated news to a judgment model.

It moves no money and makes no price forecasts. The macro engine exists to
*explain and calibrate* the macro backdrop — and to be measured honestly.
"""

from __future__ import annotations

__version__ = "0.1.0"
