# Presets

`spark-researcher init` can scaffold three lightweight starting points.

## `coding`

- target metric: `test_score`
- goal: maximize
- default command: `python run_eval.py`
- intended for code improvement loops, benchmark harnesses, and reviewable patches

## `research`

- target metric: `val_loss`
- goal: minimize
- default command: `python train.py`
- intended for training loops, model sweeps, and experiment-heavy repos

## `content`

- target metric: `quality_score`
- goal: maximize
- default command: `python score_content.py`
- intended for prompt/content evaluation loops with a fixed scorer

## Rule

Presets are scaffolds, not truths. Replace the placeholder command and metric patterns before calling a project operational.

- Keep one fixed evaluator per project so mutation and judgment stay separate.
