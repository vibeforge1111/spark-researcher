from __future__ import annotations

from importlib.util import find_spec


def optimizer_status() -> dict[str, object]:
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
