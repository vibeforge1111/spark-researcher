# Toy Project

This is a tiny deterministic target for Spark Researcher.

- `train.py` reads `config.json`
- it prints `val_loss` and `training_seconds`
- the optimum is near `learning_rate=0.0003` and `weight_decay=0.02`
- `trainer.py` simulates a DSPy-style compile trigger from `training_examples.jsonl`

