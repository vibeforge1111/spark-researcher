"""Tests for the dashboard snapshot builder and frontend build."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CHIP_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_ROOT = CHIP_ROOT / "dashboard"


@pytest.mark.skipif(
    not (DASHBOARD_ROOT / "node_modules").exists(),
    reason="npm install not run — skipping dashboard build tests",
)
class TestDashboardBuild:
    def test_snapshot_builder_produces_json(self) -> None:
        result = subprocess.run(
            ["node", str(DASHBOARD_ROOT / "scripts" / "build-dashboard-data.mjs")],
            capture_output=True,
            text=True,
            cwd=str(DASHBOARD_ROOT),
            timeout=15,
        )
        assert result.returncode == 0, f"build-dashboard-data failed: {result.stderr}"
        output_path = DASHBOARD_ROOT / "src" / "generated" / "incubator-dashboard.json"
        assert output_path.exists()
        data = json.loads(output_path.read_text("utf-8"))
        assert "generatedAt" in data
        assert "ventures" in data
        assert isinstance(data["ventures"], list)

    def test_snapshot_has_required_keys(self) -> None:
        output_path = DASHBOARD_ROOT / "src" / "generated" / "incubator-dashboard.json"
        if not output_path.exists():
            pytest.skip("snapshot not built")
        data = json.loads(output_path.read_text("utf-8"))
        required_keys = [
            "generatedAt", "product", "latestTick", "queueSnapshot",
            "state", "scout", "ventures", "feed",
        ]
        for key in required_keys:
            assert key in data, f"missing key: {key}"

    def test_typescript_compiles(self) -> None:
        result = subprocess.run(
            "npx tsc -b --noEmit",
            capture_output=True,
            text=True,
            cwd=str(DASHBOARD_ROOT),
            timeout=30,
            shell=True,
        )
        assert result.returncode == 0, f"tsc failed: {result.stdout}\n{result.stderr}"

    def test_vite_build_succeeds(self) -> None:
        result = subprocess.run(
            "npm run build",
            capture_output=True,
            text=True,
            cwd=str(DASHBOARD_ROOT),
            timeout=60,
            shell=True,
        )
        assert result.returncode == 0, f"vite build failed: {result.stderr}"
        assert (DASHBOARD_ROOT / "dist" / "index.html").exists()
