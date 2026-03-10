from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    examples_path = Path("training_examples.jsonl")
    compiled_path = Path("compiled.json")
    count = 0
    if examples_path.exists():
        count = sum(1 for line in examples_path.read_text(encoding="utf-8").splitlines() if line.strip())
    payload = {"compiled_examples": count, "status": "ok"}
    compiled_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"compiled_examples: {count}")


if __name__ == "__main__":
    main()

