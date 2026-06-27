"""Regression test for Rayiea compete item #47."""

from __future__ import annotations

import json
from pathlib import Path


def test_rayiea_47_module_imports() -> None:
    """Smoke import for patched module."""
    import importlib

    importlib.import_module("src.spark_researcher.chip_starter")
