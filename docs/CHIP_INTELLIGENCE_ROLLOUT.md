# Chip Intelligence Rollout

Use this after a chip already has the newer memory and watchtower model.

The purpose is to move from "the chip can run" to "the chip is learning from the right external intelligence and proving value outside its own benchmark."

## Rollout Order

1. Add a source registry.

Document:

- best people
- best primary materials
- best datasets
- best real-world feedback loops

2. Add a research packet schema.

The packet should capture:

- source
- claim
- mechanism
- boundary
- contradiction
- confidence
- promotion status

3. Add evidence lanes.

At minimum:

- `research_grounded`
- `benchmark_grounded`
- `realworld_validated`
- `exploratory_frontier`

4. Add a small real-world eval set.

Do not wait for a giant dataset. Ten strong cases are better than a hundred weak ones.

5. Add one narrow inference optimizer only if it has a grader.

Good first targets:

- mechanism extraction
- contradiction extraction
- doctrine drafting
- next-probe ranking

Implementation note:

- start with packet extraction from near-source notes before trying richer rankers
- record a baseline before letting a slot influence operational decisions

6. Rebuild memory and watchtower so the new lanes are visible.
7. Add a readiness page or equivalent operator surface for any live DSPy slots.

## What To Keep Portable

These should transfer across chips:

- source-registry structure
- research-packet shape
- evidence-lane names
- promotion policy categories
- watchtower page types
- real-world eval framing

These should stay domain-specific:

- source lists
- benchmark datasets
- mechanism vocabulary
- real-world tasks
- grading details

## Acceptance Checks

The rollout is not complete until all of these are true.

1. The chip has an explicit source map.
2. Research packets exist as a first-class artifact, not just freeform notes.
3. Research-grounded and benchmark-grounded evidence do not share one verdict lane.
4. The chip has at least one real-world evaluation surface.
5. Any DSPy use is tied to a narrow graded subroutine.
6. Watchtower pages show which claims are exploratory, benchmark-grounded, research-grounded, or real-world validated.
7. Any DSPy slot in live use has a visible baseline, dataset count, and readiness status.

## Recommended Docs Per Chip

- `docs/<DOMAIN>_SOURCE_MAP.md`
- `docs/<DOMAIN>_RESEARCH_PACKET.md`
- `docs/<DOMAIN>_REALWORLD_EVAL.md`
- optional `docs/<DOMAIN>_DSPY_PLAN.md`

The shared packet shape is documented in `docs/CHIP_RESEARCH_PACKET_SCHEMA.md`.

The reusable DSPy placement method for chips is documented in `docs/CHIP_DSPY_METHOD.md`.

## Rule

Do not add a generalized "intelligence framework" to core because one chip wants a richer research loop.

First prove the pattern in a chip.
Then prove it in a second chip.
Only then lift the minimum reusable contract back into Spark guidance.
