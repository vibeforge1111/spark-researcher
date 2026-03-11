# Startup-Bench Promotion Bridge

This document defines the lightweight bridge between `startup-bench` and the startup chip.

The benchmark should remain the inner evaluation engine.
The startup chip should remain the doctrine, memory, and outer-validation engine.

The missing piece is a small promotion bridge that tells the startup chip what benchmark results deserve to move into the next evidence lane.

## Why This Exists

`startup-bench` already has:

- benchmark runs
- hidden and fresh packs
- real-world scenario families
- calibration and human-review operations

The startup chip already has:

- research packets
- benchmark-grounded and exploratory lanes
- memory and watchtower
- a new outer `realworld_validated` lane

What is missing is a clean handoff between them.

Right now, the startup chip can say:

- this benchmark run was strong

But it does not yet have a small standardized artifact that says:

- this doctrine is benchmark-grounded
- this is the key mechanism or boundary that emerged
- this is eligible or not eligible for outer real-world validation

That is the job of the promotion bridge.

## Design Rule

Do not restructure `startup-bench` around the startup chip.

Instead:

- keep `startup-bench` focused on benchmark integrity
- add one small export shape that the chip can consume

This keeps the benchmark clean and lets the startup chip evolve its doctrine system without contaminating benchmark operations.

## The Three Layers

### Layer 1. Benchmark Evaluation

Owned by `startup-bench`.

Purpose:

- run fixed scenarios and suites
- score model or operator behavior
- produce benchmark artifacts

Truth question:

- did this agent or doctrine hold up inside the benchmark?

### Layer 2. Promotion Bridge

Shared interface.

Purpose:

- turn benchmark outcomes into chip-usable eligibility artifacts

Truth question:

- did this benchmark result earn the right to influence doctrine promotion or outer validation?

### Layer 3. Chip Promotion And Outer Validation

Owned by the startup chip.

Purpose:

- store doctrine
- decide what becomes a boundary or lesson
- trigger outer real-world validation

Truth question:

- is this now useful outside the benchmark world?

## What The Bridge Should Export

The bridge should export a small artifact, conceptually something like:

- `promotion_packet.json`

This does not need to be an official public benchmark schema immediately.
It can begin as a chip-facing artifact.

## Proposed Artifact Shape

Recommended fields:

- `bridge_version`
- `source`
- `generated_at`
- `benchmark_profile`
- `suite_or_scenario_id`
- `runner_type`
- `runner_id`
- `comparison_class`
- `metric_name`
- `metric_value`
- `score_summary`
- `operator_or_doctrine_id`
- `evidence_lane`
- `promotion_candidate_kind`
- `primary_mechanism`
- `primary_boundary`
- `supporting_tracks`
- `eligibility_status`
- `eligibility_reasons`
- `blockers`
- `recommended_next_step`
- `trace_paths`
- `report_paths`

## Minimum Semantics

### `promotion_candidate_kind`

Allowed starting values:

- `benchmark_grounded_candidate`
- `benchmark_grounded_boundary`
- `benchmark_blocked`

### `eligibility_status`

Allowed starting values:

- `not_eligible`
- `eligible_for_chip_promotion`
- `eligible_for_realworld_validation`

### `recommended_next_step`

Allowed starting values:

- `store_as_benchmark_evidence`
- `promote_as_doctrine_candidate`
- `promote_as_boundary_candidate`
- `queue_for_realworld_validation`
- `hold_for_more_benchmark_evidence`
- `reject_for_now`

## What Should Make Something Eligible

The bridge should be conservative.

Default eligibility for outer validation should require:

- `comparison_class = benchmark_grounded`
- meaningful score quality relative to benchmark history
- no strong unresolved contradiction
- a legible mechanism or boundary worth validating

This does not mean every strong benchmark result automatically becomes outer-eval material.
It means the bridge can say:

- this result is strong enough to be considered

The chip can still apply stricter promotion rules.

## Recommended Eligibility Ladder

### Stage 1. Benchmark Evidence Only

Conditions:

- benchmark result exists
- signal is real but not strong enough yet

Bridge output:

- `promotion_candidate_kind = benchmark_grounded_candidate`
- `eligibility_status = eligible_for_chip_promotion`
- `recommended_next_step = store_as_benchmark_evidence`

### Stage 2. Doctrine Candidate

Conditions:

- benchmark result is near-best or clearly strong in-lane
- mechanism is reusable
- no serious contradiction

Bridge output:

- `promotion_candidate_kind = benchmark_grounded_candidate`
- `eligibility_status = eligible_for_chip_promotion`
- `recommended_next_step = promote_as_doctrine_candidate`

### Stage 3. Boundary Candidate

Conditions:

- benchmark result mainly reveals a failure surface or transfer limit

Bridge output:

- `promotion_candidate_kind = benchmark_grounded_boundary`
- `eligibility_status = eligible_for_chip_promotion`
- `recommended_next_step = promote_as_boundary_candidate`

### Stage 4. Outer Validation Eligible

Conditions:

- benchmark result is promoted or near-promotion quality
- doctrine or boundary is clear enough to test on real-world tasks

Bridge output:

- `eligibility_status = eligible_for_realworld_validation`
- `recommended_next_step = queue_for_realworld_validation`

## Important Naming Rule

Do not confuse:

- `startup-bench` real-world scenario families

with:

- startup chip outer `realworld_validated` tasks

These are not the same thing.

Recommended language:

- `benchmark real-world scenarios` for the benchmark repo
- `realworld validation tasks` for the startup chip

This naming separation prevents conceptual drift.

## Why Not Just Use Existing Suite Reports

Because suite reports are benchmark-facing, not doctrine-facing.

They are good for:

- benchmark comparison
- reporting
- official evaluation
- calibration review

They are not yet optimized for:

- doctrine promotion
- boundary extraction
- outer-validation eligibility

The bridge should be much smaller and much more opinionated.

## Where This Artifact Should Live

Best initial location:

- generated by the startup chip after a benchmark-grounded run
- stored under the startup chip runtime artifacts

Example:

- `artifacts/promotion/benchmark_grounded/<run_id>.json`

This keeps the first version lightweight.

Later, if `startup-bench` itself wants a first-class export command, that can be added there.

## Who Owns What

### `startup-bench` owns

- benchmark scoring
- calibration
- human-review operations
- official benchmark reporting

### the promotion bridge owns

- chip-facing interpretation of benchmark outputs
- promotion eligibility summary

### the startup chip owns

- doctrine promotion
- memory persistence
- outer real-world validation
- watchtower rendering

## Minimal First Implementation

Start with the smallest useful version.

1. After a benchmark-grounded startup-chip run, generate a bridge packet.
2. Infer:
   - `promotion_candidate_kind`
   - `eligibility_status`
   - `recommended_next_step`
3. Store it under startup-chip artifacts.
4. Show it in Obsidian.
5. Use it to decide whether the outer validation seed pack should run.

That is enough for v1.

## Anti-Patterns

Do not:

- rewrite `startup-bench` around doctrine promotion
- let heuristic frontier results emit benchmark promotion packets
- treat benchmark “real-world” scenario packs as the same thing as outer validation tasks
- auto-promote every good benchmark result into outer validation

## Spark Mapping

In Spark terms, the bridge becomes the rule that separates:

- `benchmark_grounded`

from:

- `realworld_validated`

It is the explicit gate between those lanes.

Without this bridge, the system will drift into hand-wavy promotion.

With it, the system can stay disciplined:

- source
- packet
- benchmark
- promotion bridge
- outer validation
- durable doctrine

## Final Recommendation

Do not restructure `startup-bench` deeply right now.

Add the promotion bridge first.

That will solve the main integration problem with the startup chip while preserving the benchmark's existing strengths.
