# Chip Registry

This is the lightweight registry for known Spark domain chips.

## Standard

- manifest schema: `spark-chip.v1`
- hook I/O protocol: `spark-hook-io.v1`
- canonical schema file: `schemas/spark-chip.schema.json`

## Current Chips

- `startup-yc`
  - repo: `https://github.com/vibeforge1111/domain-chip-startup-yc`
  - domain: `startup`
  - purpose: YC startup factor research, bounded suggestion, startup packets, startup watchtower

- `trading`
  - repo: `https://github.com/vibeforge1111/domain-chip-trading`
  - domain: `trading`
  - purpose: regime-aware trading signal research, risk-adjusted edge suggestions, trading packets, trading watchtower

- `content`
  - repo: `https://github.com/vibeforge1111/domain-chip-content`
  - domain: `content`
  - purpose: content mechanism research, promotion-safe content beliefs, content packets, content watchtower

## Validation Snapshot

Validated against the current `spark-researcher` core on March 10, 2026:

- `startup-yc`
  - best `startup_score = 0.66`
  - winner: `theme:distribution_velocity + retention`

- `trading`
  - best `risk_adjusted_edge = 0.64`
  - winner: `wallet:momentum_base + slippage_discipline`

- `content`
  - best `useful_reach_score = 0.69`
  - winner: `hook:proof_founder + proof_quality`

## Rule

If a new chip needs behavior outside `evaluate`, `suggest`, `packets`, or `watchtower`, raise the standard version instead of silently growing one-off conventions.
