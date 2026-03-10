# Checkloop

Use the local checkloop repo as the 1:1 proving ground for `spark-researcher` before trusting a new change.

## Current Repo

- checker path: `C:\Users\USER\Desktop\spark-researcher-checkloop-pristine`
- expected sync target: the current `main` commit of `C:\Users\USER\Desktop\spark-researcher`

## Standard Flow

```powershell
cd C:\Users\USER\Desktop\spark-researcher-checkloop-pristine
git fetch origin
git pull --ff-only origin main
git rev-parse HEAD
$env:PYTHONPATH='src'
python -m pip install -e .
python -m spark_researcher.cli autoloop --command train --rounds 4 --suggest-limit 4
python -m spark_researcher.cli trainers run
python -m spark_researcher.cli memory sync
python -m spark_researcher.cli beliefs build
python -m spark_researcher.cli obsidian build
python -m spark_researcher.cli summary
python -m spark_researcher.cli packets status
python -m spark_researcher.cli advisory providers
python -m spark_researcher.cli advisory review
python -m spark_researcher.cli optimizer export-advisory-dataset
python -m spark_researcher.cli line-budget --limit 8000
```

## Goal

Prove four things:

- the core loop still converges cleanly
- the memory, beliefs, and vault pipeline still works
- the advisory and optimizer sidecars still work
- the repo still stays inside the line budget

## Rule

If the checkloop needs extra manual rituals, document them explicitly or fix the core. Do not let hidden operator habits become part of the standard flow.
