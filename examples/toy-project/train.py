from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    config = json.loads(Path("config.json").read_text(encoding="utf-8"))
    learning_rate = float(config["learning_rate"])
    weight_decay = float(config["weight_decay"])
    val_loss = 1.0 + ((learning_rate - 0.0003) ** 2) * 1000000 + abs(weight_decay - 0.02) * 5
    print(f"val_loss: {val_loss:.6f}")
    print("training_seconds: 5.0")


if __name__ == "__main__":
    main()

