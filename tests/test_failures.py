from __future__ import annotations

import json
from pathlib import Path

from spark_researcher.failures import failures_path, load_failures


def test_load_failures_skips_malformed_jsonl_rows(tmp_path: Path) -> None:
    path = failures_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            [
                json.dumps({"failure_type": "first", "summary": "kept"}),
                "{bad json",
                json.dumps(["not", "a", "dict"]),
                "",
                json.dumps({"failure_type": "second", "summary": "also kept"}),
            ]
        ),
        encoding="utf-8",
    )

    assert [row["failure_type"] for row in load_failures(tmp_path)] == ["first", "second"]
