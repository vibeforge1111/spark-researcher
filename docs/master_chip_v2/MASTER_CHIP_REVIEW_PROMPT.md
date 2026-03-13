# Master Chip Review Prompt

> Use this to review an already-designed or already-implemented Spark domain chip.
> Replace `{DOMAIN_NAME}`, `{DOMAIN_DISPLAY_NAME}`, `{CHIP_PATH}`, and `{CONFIG_PATH}`.
> This prompt assumes the chip should conform to the standards in `docs/master_chip_v2/MASTER_CHIP_ARCHITECT_PROMPT_V2.md`.

---

Review the Spark domain chip for `{DOMAIN_NAME}` at `{CHIP_PATH}`.

Your job is to audit whether this chip is:

- structurally valid
- faithful to the current Spark chip contract
- honest about evidence
- strong enough to operate
- standardized at the base layer
- explicit about any real domain-specific deviations

This is a chip review, not a design brainstorm.
Prioritize findings, risks, regressions, drift, weak assumptions, and missing tests.

Do not start by summarizing the chip.
Start by identifying what is wrong, brittle, missing, misleading, or under-specified.

Use the real current standards from:

- `docs/CHIPS.md`
- `docs/CHIP_INTELLIGENCE_CONTRACT.md`
- `docs/CHIP_ONE_LOOP_FLYWHEEL.md`
- `docs/CHIP_MEMORY_ROLLOUT.md`
- `docs/CHIP_VALIDATION.md`
- `docs/AUTOLOOP.md`
- `docs/OBSIDIAN.md`
- `docs/CHECKLOOP.md`
- `docs/CHIP_RESEARCH_PACKET_SCHEMA.md`
- `docs/CHIP_TAGGING_RULESET.md`
- `docs/CHIP_BENCHMARK_BRIDGE_GUIDE.md`
- `docs/master_chip_v2/MASTER_CHIP_ARCHITECT_PROMPT_V2.md`
- `docs/master_chip_v2/MASTER_CHIP_IMPLEMENTATION_PROMPT.md`
- `docs/master_chip_v2/MASTER_CHIP_TESTING_PROMPT.md`

Also compare against the real core implementation in:

- `src/spark_researcher/chips.py`
- `src/spark_researcher/runner.py`
- `src/spark_researcher/candidates.py`
- `src/spark_researcher/memory.py`
- `src/spark_researcher/obsidian.py`

And compare against the strongest reference chips:

- `../domain-chip-startup-yc`
- `../domain-chip-trading-crypto`

Review the chip in this order:

1. manifest and command contract
2. project config and candidate structure
3. evaluate hook behavior
4. suggest hook behavior
5. packets hook behavior
6. watchtower hook behavior
7. memory-tier discipline
8. queue discipline
9. benchmark / heuristic separation
10. flywheel logic
11. autoloop compatibility
12. real-world validation logic
13. testing coverage

Required review questions:

### Manifest And Hook Contract

- Does the manifest actually conform to `spark-chip.v1`?
- Are all four hooks implemented and wired cleanly?
- Are any hidden conventions being relied on instead of the actual hook contract?
- Is the frontier grammar real and constrained, or just narrative text?

### Evaluator

- Does the evaluator return parseable metrics?
- Does it expose clear promotion gates?
- Does it distinguish benchmark-grounded from heuristic-frontier work honestly?
- Does it explain mechanism, boundary, verdict, and next step explicitly?
- Is there any ghost improvement where confidence grows without stronger evidence?

### Suggestion Logic

- Are suggestions bounded and mutation-grammar compliant?
- Does the chip use ledger evidence, failure priorities, or doctrine gaps meaningfully?
- Does it avoid replaying stale candidates?
- Does it reopen the frontier from winners and failures?
- Does it separate knowledge gaps from trial gaps?

### Packets

- Are packet families explicit and small?
- Are doctrine, boundary, benchmark evidence, and exploratory probe docs clearly separated?
- Is raw residue being treated as doctrine indirectly?
- Are memory tiers correct?

### Watchtower

- Are pages named consistently under `07-Domains/{DOMAIN_DISPLAY_NAME}/`?
- Does the watchtower tell the truth of the runtime?
- Are grounded doctrine and exploratory probes clearly separated?
- Can an operator tell what changed, what is trusted, and what is weak?
- Are there decorative pages with no operational role?

### Flywheel And Autoloop

- Is there one governing loop or several disconnected loops?
- Are the next bottlenecks explicit?
- Does the chip route correctly between research, trial, ranking, promotion, and contradiction work?
- Does it fit Spark autoloop semantics without hidden rituals?

### Real-World Validation

- Is outer validation defined honestly?
- Are benchmark and real-world lanes separated?
- Is promotion too eager for the strength of evidence?

### Testing

- Does the chip have a smoke test path?
- Does it have unit tests for evaluator, suggestions, packets, and watchtower?
- Does it test memory-tier correctness and watchtower truthfulness?
- Does it rely on manual operator rituals instead of reproducible checks?

Required output order:

1. `Findings`
2. `Open Questions`
3. `Testing Gaps`
4. `Risk Summary`
5. `Short Change Summary`

For `Findings`, list the issues in severity order:

- `critical`
- `high`
- `medium`
- `low`

For each finding include:

- title
- severity
- what is wrong
- why it matters
- file references when available
- what a correct fix should preserve

If no findings are present, say so explicitly and then list residual risks or missing test coverage.

Success condition:

The review should tell a strong operator whether the chip is trustworthy, where it deviates from the standard, and what must be fixed before the chip should be treated as a real domain surface.
