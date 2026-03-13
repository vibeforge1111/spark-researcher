# Master Chip Testing Prompt

> Use this when you want to design or implement the testing system for a Spark domain chip.
> Replace `{DOMAIN_NAME}`, `{DOMAIN_DISPLAY_NAME}`, `{CHIP_PATH}`, and `{CONFIG_PATH}`.
> This prompt covers smoke tests, unit tests, runtime integration checks, and watchtower truthfulness checks.

---

Design the testing system for the Spark domain chip `{DOMAIN_NAME}` at `{CHIP_PATH}`.

Your job is to define and, when appropriate, implement a testing strategy that is:

- small
- deterministic where possible
- honest about what is and is not testable
- aligned with the real Spark runtime
- strong enough to catch contract breaks, evidence drift, and watchtower lies

Do not build a giant testing framework.
Use the smallest test system that proves the chip is real, stable, and reviewable.

Base the testing system on the current Spark standards in:

- `docs/CHIP_VALIDATION.md`
- `docs/CHECKLOOP.md`
- `docs/RELIABILITY_TEST_PLAN.md`
- `docs/OBSIDIAN.md`
- `docs/CHIP_MEMORY_ROLLOUT.md`
- `docs/AUTOLOOP.md`
- `docs/testing-chip/README.md`
- `docs/testing-chip/cli.py`

Also inspect the runtime behavior in:

- `src/spark_researcher/chips.py`
- `src/spark_researcher/runner.py`
- `src/spark_researcher/candidates.py`
- `src/spark_researcher/memory.py`
- `src/spark_researcher/obsidian.py`

And compare test needs against:

- `../domain-chip-startup-yc`
- `../domain-chip-trading-crypto`

Your output must define four layers of testing:

1. `contract smoke tests`
2. `domain unit tests`
3. `runtime integration tests`
4. `watchtower and memory truthfulness tests`

---

## Testing Principles

The testing system must prove:

1. the manifest and hooks are valid
2. the evaluator is deterministic or honestly bounded
3. the suggest hook proposes valid unseen candidates
4. packets map into explicit memory tiers
5. watchtower pages reflect real runtime state
6. autoloop can run without hidden operator rituals
7. benchmark and heuristic lanes remain separated
8. real-world promotion is not over-eager

The tests should prefer:

- pure-function unit tests for scoring and classification logic
- temporary-directory integration tests for hook IO
- one or two end-to-end smoke paths for runtime behavior
- explicit truthfulness checks on memory and Obsidian outputs

Avoid:

- brittle snapshot spam
- tests that only assert that a file exists but not what it means
- hidden network dependence unless the design explicitly requires it
- non-deterministic test data unless it is clearly marked as optional or manual

---

## Layer 1: Contract Smoke Tests

Define the smallest repeatable smoke suite that proves the chip bridge works.

At minimum include:

1. manifest validates via `chips validate`
2. `chips status` returns the expected hook list
3. `evaluate` hook runs on a baseline candidate
4. `suggest` hook returns valid suggestions or an honest empty result
5. `packets` hook emits documents
6. `watchtower` hook emits pages
7. `memory sync` succeeds
8. `obsidian build` succeeds

Recommended command flow:

```powershell
python -m spark_researcher.cli chips validate --config {CONFIG_PATH}
python -m spark_researcher.cli chips status --config {CONFIG_PATH}
python -m spark_researcher.cli run --config {CONFIG_PATH} --command research
python -m spark_researcher.cli candidates suggest --config {CONFIG_PATH} --command research
python -m spark_researcher.cli memory sync --config {CONFIG_PATH}
python -m spark_researcher.cli obsidian build --config {CONFIG_PATH}
python -m spark_researcher.cli summary --config {CONFIG_PATH}
```

Smoke tests must verify more than process exit code.
Also verify:

- metrics were parsed
- packet docs were emitted
- domain pages were generated
- queue semantics stayed clean

---

## Layer 2: Domain Unit Tests

Implement fast, local unit tests around the chip's own logic.

At minimum define unit tests for:

### Evaluator Logic

- baseline scoring
- mutation-to-score mapping
- gate thresholds
- verdict routing
- next-step routing
- comparison-class assignment
- boundary extraction

### Suggest Logic

- suggestions stay inside mutation grammar
- duplicates are not proposed
- frontier reopens from winners and failures
- knowledge gaps and trial gaps route differently
- contradiction pressure can influence next probes

### Packet Logic

- promoted doctrine docs are emitted only when evidence is sufficient
- boundary docs appear for failure surfaces
- exploratory docs remain exploratory
- packet kinds and slugs are stable
- memory tiers map correctly

### Watchtower Logic

- expected page set is emitted
- paths are stable and normalized
- key operator counters render correctly
- losing-candidate explanations are shown when available
- grounded doctrine and exploratory probes are separated

If the chip has pure helper functions, test them directly.
If the chip keeps everything inside one large CLI file, isolate the deterministic helper logic and test that logic instead of only shelling out.

Preferred test structure:

- `tests/test_evaluate.py`
- `tests/test_suggest.py`
- `tests/test_packets.py`
- `tests/test_watchtower.py`

Use temporary directories and synthetic ledger rows where possible.

---

## Layer 3: Runtime Integration Tests

Define tests that run the chip through the actual Spark bridge.

At minimum include:

### Hook IO Integration

- invoke each hook through the standard `--input/--output` flow
- assert the response shape matches the contract

### Runner Integration

- run one baseline candidate
- run one non-baseline candidate
- assert the ledger record contains:
  - `metric_value`
  - `verdict`
  - `chip_result`
  - correct `comparison_class` when relevant

### Queue Integration

- run `candidates suggest`
- ensure suggestions land in generated queue state, not stable config
- ensure duplicates are not appended

### Memory Integration

- run `memory sync`
- confirm chip docs appear in the memory manifest
- confirm expected kinds and tiers are present

### Obsidian Integration

- run `obsidian build`
- confirm required domain pages exist
- confirm runtime pages and domain pages are mutually consistent

### Autoloop Integration

- run one bounded `autoloop`
- verify the loop exits cleanly
- verify the chip can reopen the frontier from recent evidence

Do not require a huge continuous loop for routine testing.
One bounded proof path is enough for the default suite.

---

## Layer 4: Watchtower And Memory Truthfulness Tests

This layer is mandatory.
A chip is not trustworthy if its watchtower tells a cleaner story than its artifacts support.

Define tests for:

### Memory Truthfulness

- doctrine docs outrank raw residue
- boundary docs are discoverable
- exploratory docs do not appear as doctrine
- working memory is current and chip-state-shaped
- tier counts in memory manifest match actual docs

### Watchtower Truthfulness

- the watchtower reflects generated page counts accurately
- doctrine pages reflect actual promoted docs
- frontier pages reflect actual exploratory docs
- benchmark evidence pages reflect actual benchmark docs
- queue counts match runtime queue state
- "why it lost" reflects actual losing rows when available

### Research Provenance Visibility

When the domain uses research:

- note ids, domains, and URLs appear where expected
- provenance is not fabricated when absent

### Comparison-Lane Truthfulness

- benchmark-grounded and heuristic-frontier results remain visibly distinct
- pages do not imply benchmark grounding for heuristic-only outputs

Use the spirit of `docs/testing-chip/cli.py`:

- deterministic checks
- small temporary fixtures
- direct assertions on truth-bearing outputs

---

## Test Categories

Label the final test system using these categories:

- `smoke`
- `unit`
- `integration`
- `truthfulness`
- `manual_optional`

Every test should declare:

- what it is checking
- whether it is deterministic
- whether it requires external data
- whether it is safe for CI

---

## Domain-Specific Testing Gaps

If `{DOMAIN_NAME}` introduces testing problems beyond the current standard, explicitly identify them.

For each true gap, output:

- `gap_name`
- `why_existing_testing_standard_is_insufficient`
- `what_must_be_tested`
- `smallest_clean_extension`
- `can_it_be_unit_tested_or_only_integration_tested`
- `is_it_ci_safe`

Examples of real gaps:

- benchmark requires heavy external data
- evaluation depends on rate-limited sources
- watchtower meaning depends on domain-specific bridge artifacts
- real-world validation requires human review

Do not hide test gaps by pretending everything belongs in unit tests.

---

## Suggested Test Layout

Use a small test layout like:

```text
tests/
  test_manifest_smoke.py
  test_evaluate.py
  test_suggest.py
  test_packets.py
  test_watchtower.py
  test_runtime_integration.py
  test_memory_truthfulness.py
  test_obsidian_truthfulness.py
```

If the chip is still stage-0 or stage-1 maturity, keep the suite smaller and explain what is deferred.

---

## Acceptance Criteria

Do not call the testing system complete unless:

1. there is a repeatable smoke path
2. evaluator logic has unit coverage
3. suggestion logic has unit coverage
4. packet generation has unit or focused integration coverage
5. watchtower generation has unit or focused integration coverage
6. one runtime integration path exists
7. memory-tier correctness is tested
8. watchtower truthfulness is tested
9. benchmark / heuristic separation is tested
10. any remaining manual-only checks are explicitly labeled

---

## Output Format

Return the final testing plan in this order:

1. `Testing Philosophy`
2. `Smoke Test Suite`
3. `Unit Test Suite`
4. `Integration Test Suite`
5. `Truthfulness Test Suite`
6. `Manual Or Heavy Tests`
7. `Testing Gaps`
8. `Recommended File Layout`
9. `Acceptance Criteria`

Success condition:

The result should give `{DOMAIN_NAME}` a small but real testing system that proves the chip bridge, evaluator, packets, memory, and watchtower are working honestly instead of only looking plausible.

