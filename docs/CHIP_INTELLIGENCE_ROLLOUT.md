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

Alongside the packet schema, define what "doctrine-rich" source material looks like for the domain.

The chip should know how to reject:

- event updates
- low-signal announcements
- repetitive source expansions that do not improve doctrine

Use the shared guide:

- `docs/CHIP_RESEARCH_QUALITY_RULESET.md`

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
11. Add a research-selection layer so the chip can choose the best next sources before bounded discovery runs.
12. Add a simple coverage-and-depth model so the chip can distinguish:

- missing research areas
- shallow doctrine areas
- overcrowded areas

13. Commit in small coherent chunks as the chip stabilizes.

## Commit Cadence Rule

Do not wait for one giant commit when working on a richer chip loop.

Preferred rule:

- one small commit per coherent change set

Good commit boundaries:

- loop-logic change
- docs or spec change
- research-source expansion wave
- DSPy runner improvement
- watchtower or memory surface change

Avoid:

- bundling unrelated runtime residue into those commits
- mixing docs, logic, generated artifacts, and queue state in one commit
- waiting so long that reviewable changes blur together

This keeps chip evolution:

- reviewable
- revertable
- easier to transfer to future chips

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
10. The chip can explain whether it needs more sources, deeper doctrine, or less repetitive source growth.
11. If the chip does bounded discovery, it can also explain which specific sources or source families it wants next and why.

## Recommended Docs Per Chip

- `docs/<DOMAIN>_SOURCE_MAP.md`
- `docs/<DOMAIN>_RESEARCH_PACKET.md`
- `docs/<DOMAIN>_RESEARCH_QUALITY_RULESET.md`
- `docs/<DOMAIN>_TAGGING_RULESET.md`
- `docs/<DOMAIN>_REALWORLD_EVAL.md`
- optional `docs/<DOMAIN>_DSPY_PLAN.md`

Shared reusable references:

- packet shape: `docs/CHIP_RESEARCH_PACKET_SCHEMA.md`
- tagging method: `docs/CHIP_TAGGING_RULESET.md`
- DSPy placement: `docs/CHIP_DSPY_METHOD.md`
- benchmark bridge: `docs/CHIP_BENCHMARK_BRIDGE_GUIDE.md`
- richer-chip loop pattern: `docs/CHIP_ONE_LOOP_FLYWHEEL.md`

## Rule

Do not add a generalized "intelligence framework" to core because one chip wants a richer research loop.

First prove the pattern in a chip.
Then prove it in a second chip.
Only then lift the minimum reusable contract back into Spark guidance.
