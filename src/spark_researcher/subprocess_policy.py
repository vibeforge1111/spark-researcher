from __future__ import annotations

import math
import os


SUBPROCESS_TIMEOUT_ENV = "SPARK_RESEARCHER_SUBPROCESS_TIMEOUT_SECONDS"
MAX_SUBPROCESS_TIMEOUT_SECONDS = 3600.0


def subprocess_timeout_seconds(default_seconds: float) -> float:
    raw = os.environ.get(SUBPROCESS_TIMEOUT_ENV, "").strip()
    try:
        seconds = float(raw) if raw else float(default_seconds)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Spark Researcher subprocess timeout configuration is invalid; use 1-3600 seconds.") from exc
    if not math.isfinite(seconds) or seconds < 1 or seconds > MAX_SUBPROCESS_TIMEOUT_SECONDS:
        raise RuntimeError("Spark Researcher subprocess timeout configuration is invalid; use 1-3600 seconds.")
    return seconds
