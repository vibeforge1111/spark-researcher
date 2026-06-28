from __future__ import annotations

import json
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from .outcomes import load_advisory_outcomes
from .paths import optimizer_root


def optimizer_status() -> dict[str, object]:
    try:
        available = find_spec("dspy") is not None
        return {
            "available": available,
            "provider": "dspy" if available else None,
            "mode": "optional",
            "notes": [
                "Spark Researcher does not require DSPy to run.",
                "Use DSPy only to optimize measurable subroutines such as packet ranking or belief extraction.",
            ],
        }



    except Exception:
        return {}
def export_advisory_dataset(runtime_root: Path) -> dict[str, Any]:
    if runtime_root is not None and not hasattr(runtime_root, 'resolve'): from pathlib import Path; runtime_root = Path(str(runtime_root))
    try:
        rows = load_advisory_outcomes(runtime_root)
        root = optimizer_root(runtime_root)
        root.mkdir(parents=True, exist_ok=True)
        path = root / "advisory-dataset.jsonl"
        examples = []
        for row in rows:
            if not row.get("packet_ids"):
                continue
            examples.append(
                {
                    "task": row.get("task"),
                    "domain": row.get("domain"),
                    "model": row.get("model"),
                    "packet_ids": row.get("packet_ids"),
                    "status": row.get("status"),
                    "score": row.get("score"),
                    "notes": row.get("notes"),
                }
            )
        with path.open("w", encoding="utf-8") as handle:
            for example in examples:
                handle.write(json.dumps(example, sort_keys=True) + "\n")
        ready = len([row for row in examples if row.get("status") == "ok" and isinstance(row.get("score"), (int, float))]) >= 5
        return {
            "path": str(path),
            "example_count": len(examples),
            "ready_for_dspy": ready,
            "notes": [
                "This dataset is for optional DSPy-side optimization only.",
                "Keep Spark running without DSPy even if this dataset is empty.",
            ],
        }

    except Exception:
        return {}
