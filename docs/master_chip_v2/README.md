# Master Chip v2

This folder contains the `master_chip_v2` prompt stack for designing, building, reviewing, and testing Spark domain chips.

Use these docs in this order.

## Prompt Stack

1. `MASTER_CHIP_ARCHITECT_PROMPT_V2.md`

Use this when you want the full standards-heavy chip design prompt.

It is the most comprehensive version.
Use it when:

- defining a new domain chip standard
- transferring startup/trading lessons into a new domain
- identifying gaps in the current chip contract
- deciding what should stay standardized vs what should become domain-specific

2. `MASTER_CHIP_OPERATOR_PROMPT.md`

Use this when you want a shorter planning prompt derived from the architect prompt.

Use it when:

- crafting a new chip concept quickly
- briefing an operator or model on the chip design task
- running a lighter planning pass before implementation

3. `MASTER_CHIP_IMPLEMENTATION_PROMPT.md`

Use this after the design is approved and you want to actually build the chip repo.

Use it when:

- creating `spark-chip.json`
- creating `spark-researcher.project.json`
- implementing the 4 hooks
- wiring packet families, memory tiers, and watchtower pages

4. `MASTER_CHIP_REVIEW_PROMPT.md`

Use this to audit an existing chip.

Use it when:

- reviewing a finished chip repo
- checking whether a chip drifted from the standard
- identifying bugs, missing tests, weak evidence discipline, or watchtower dishonesty

5. `MASTER_CHIP_TESTING_PROMPT.md`

Use this to define or implement the chip testing system.

Use it when:

- designing smoke tests
- adding unit tests for evaluator, suggestions, packets, or watchtower
- validating memory-tier correctness
- validating watchtower truthfulness
- defining CI-safe vs manual-heavy test coverage

## Recommended Workflow

Use this sequence for a new chip:

1. `MASTER_CHIP_ARCHITECT_PROMPT_V2.md`
2. `MASTER_CHIP_OPERATOR_PROMPT.md`
3. `MASTER_CHIP_IMPLEMENTATION_PROMPT.md`
4. `MASTER_CHIP_TESTING_PROMPT.md`
5. `MASTER_CHIP_REVIEW_PROMPT.md`

Short version:

- architect = define the standard
- operator = compress the design task
- implementation = build the chip
- testing = prove it works
- review = audit whether it is actually good

## Rule

Do not skip the architect layer for domains that may require new standards.

If the domain might need:

- new benchmark bridge semantics
- new watchtower page types
- new comparison classes
- new packet families
- new testing rules

then start with `MASTER_CHIP_ARCHITECT_PROMPT_V2.md` first so the gap is made explicit instead of being smuggled into implementation.

## References

The prompt stack is grounded in:

- Spark core chip/runtime docs under `docs/`
- Spark core implementation under `src/spark_researcher/`
- `../domain-chip-startup-yc`
- `../domain-chip-trading-crypto`

