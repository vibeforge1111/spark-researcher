# Chip Validation

Use this protocol to validate any Spark domain chip against the current `spark-researcher` core.

## Goal

Prove four things:

- the chip manifest is valid
- the chip still runs through the current Spark bridge
- the chip produces memory and watchtower output correctly
- the chip converges cleanly without hidden system errors
- the chip can reopen the frontier from winners and failures instead of only replaying a fixed candidate list

## Use A Clean Repo

Prefer a pristine clone or a clean working tree.

If the chip repo already has generated run state or local drift, clone a fresh checker copy before validation.

## Standard Flow

From the chip repo root:

```powershell
$env:PYTHONPATH='C:\Users\USER\Desktop\spark-researcher\src;src'
python -m spark_researcher.cli chips validate
python -m spark_researcher.cli autoloop --command research
python -m spark_researcher.cli memory sync
python -m spark_researcher.cli obsidian build
python -m spark_researcher.cli summary
```

## Required Pass Conditions

- `chips validate` returns `valid: true`
- `autoloop` exits cleanly
- every run returns exit code `0`
- `memory sync` succeeds and emits domain documents
- `obsidian build` succeeds and emits domain pages
- `summary` reports the expected best metric for the chip

## What To Report

- chip name and schema version
- best metric reached
- winning candidate
- run count
- memory document count
- domain page count
- whether suggestions were appended or the chip exhausted its current frontier
- any regressions, plateaus, or system errors

## Current Reference Results

Validation on March 10, 2026:

- `startup-yc`
  - first frontier best `startup_score = 0.66`
  - reopened frontier best `startup_score = 0.68`
  - current strongest winner: `theme:distribution_velocity + retention + founder_velocity`
- `trading`
  - first frontier best `risk_adjusted_edge = 0.64`
  - current strongest winner remains `wallet:momentum_base + slippage_discipline`
  - reopened frontier should now suggest transfer checks and stress tests from that winner
- `content`
  - first frontier best `useful_reach_score = 0.69`
  - current strongest winner remains `hook:proof_founder + proof_quality`
  - reopened frontier should now suggest audience-fit checks and counterexample probes from that winner

## Rule

If a chip requires extra one-off steps outside this flow, fix the chip or raise the chip standard explicitly. Do not let hidden operator rituals become part of the protocol.
