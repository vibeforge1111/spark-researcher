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

3. Add a small tag registry.

Start with the smallest useful registry for recurring packet patterns.

At minimum, define:

- contradiction tags
- when a tag is allowed to be added
- how DSPy may suggest tags without owning the registry

Use the shared guide:

- `docs/CHIP_TAGGING_RULESET.md`

4. Add evidence lanes.

At minimum:

- `research_grounded`
- `benchmark_grounded`
- `realworld_validated`
- `exploratory_frontier`

5. Add a small real-world eval set.

Do not wait for a giant dataset. Ten strong cases are better than a hundred weak ones.

6. Add a benchmark bridge if the chip has a real benchmark lane.

The bridge should:

- translate benchmark outputs into chip-facing promotion eligibility
- stay smaller than the benchmark report
- decide what becomes eligible for chip promotion or outer validation

Use the shared guide:

- `docs/CHIP_BENCHMARK_BRIDGE_GUIDE.md`

7. Add one narrow inference optimizer only if it has a grader.

Good first targets:

- mechanism extraction
- contradiction extraction
- doctrine drafting
- next-probe ranking

Implementation note:

- start with packet extraction from near-source notes before trying richer rankers
- record a baseline before letting a slot influence operational decisions

8. Rebuild memory and watchtower so the new lanes are visible.
9. Add a readiness page or equivalent operator surface for any live DSPy slots.
10. Move toward one governing loop with separate research frontier and trial frontier once the chip has enough source and benchmark depth.

## What To Keep Portable

These should transfer across chips:

- source-registry structure
- research-packet shape
- tag-registry rules
- evidence-lane names
- promotion policy categories
- one-loop governing pattern
- research frontier vs trial frontier split
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
3. The chip has a small stable tag registry and a rule for when new tags may be added.
4. Research-grounded and benchmark-grounded evidence do not share one verdict lane.
5. The chip has at least one real-world evaluation surface.
6. If the chip has a benchmark lane, it has a benchmark bridge or equivalent explicit promotion gate.
7. Any DSPy use is tied to a narrow graded subroutine.
8. Watchtower pages show which claims are exploratory, benchmark-grounded, research-grounded, or real-world validated.
9. Any DSPy slot in live use has a visible baseline, dataset count, and readiness status.

## Recommended Docs Per Chip

- `docs/<DOMAIN>_SOURCE_MAP.md`
- `docs/<DOMAIN>_RESEARCH_PACKET.md`
- `docs/<DOMAIN>_TAGGING_RULESET.md`
- `docs/<DOMAIN>_REALWORLD_EVAL.md`
- optional `docs/<DOMAIN>_DSPY_PLAN.md`

The shared packet shape is documented in `docs/CHIP_RESEARCH_PACKET_SCHEMA.md`.

The shared tagging method is documented in `docs/CHIP_TAGGING_RULESET.md`.

The reusable DSPy placement method for chips is documented in `docs/CHIP_DSPY_METHOD.md`.

The reusable benchmark-to-chip bridge method is documented in `docs/CHIP_BENCHMARK_BRIDGE_GUIDE.md`.

The reusable one-loop flywheel pattern for richer chips is documented in `docs/CHIP_ONE_LOOP_FLYWHEEL.md`.

## Rule

Do not add a generalized "intelligence framework" to core because one chip wants a richer research loop.

First prove the pattern in a chip.
Then prove it in a second chip.
Only then lift the minimum reusable contract back into Spark guidance.
