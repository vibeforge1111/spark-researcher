# Chip Remediation Prompts

Use these prompts in the chip repos themselves, in separate terminals rooted at each chip repository.

These prompts assume:

- Spark core work continues in `spark-researcher`
- chip repos should only make chip-local fixes
- each chip agent should commit often in small coherent batches
- each chip agent should verify its own work with Spark-facing commands where possible

## Operating Rule

Do not fix chip problems by editing `spark-researcher` from inside a chip repo.

Each chip prompt below is written to:

- keep domain logic inside the chip
- make the chip more truthful and portable
- align the chip with the Spark contract that is being hardened in core

## Recommended Execution Order

Run these first:

1. `domain-chip-trading-crypto`
2. `domain-chip-spark-private`
3. `domain-chip-pokemon-red`
4. `domain-chip-agentic-marketing`
5. `domain-chip-startup-yc`

## Prompt: domain-chip-trading-crypto

```text
You are in the `domain-chip-trading-crypto` repo on Desktop.

Objective:
Fix this chip so it matches Spark Researcher's intended chip contract instead of only looking valid on paper.

You must keep all changes chip-local. Do not edit `spark-researcher`.

Current audited problems to fix:
- `spark-chip.json` declares frontier fields like `allowed_mutations`, `field_patterns`, and `open_mutation_fields` at top level instead of under `frontier`
- `packets()` is using `payload["candidate"]` and rescoring local mutations instead of deriving documents from Spark-provided `ledger_rows` and `outcomes`
- packet output is therefore not representing actual benchmark winners or real contradiction surfaces
- the watchtower is rich, but the benchmark-to-promotion bridge still needs clearer "why not ready" surfaces

Required work:
1. Fix the manifest so all frontier config lives under a proper `frontier` object.
2. Rewrite `packets()` to use Spark's actual packet payload:
   - `ledger_rows`
   - `outcomes`
   - `documents_root`
3. Make packet output derive from real top candidate rows, not from a fabricated or absent `candidate`.
4. Emit truthful packet kinds for:
   - benchmark evidence
   - grounded doctrine candidates
   - grounded boundaries / contradiction surfaces
5. Add an explicit operator-facing explanation for why a row is not paper-trade-ready yet.
6. Add tests for:
   - manifest structure
   - packet generation from fixture `ledger_rows`
   - packet output changing when the best row changes
7. Update README and/or docs to explain:
   - benchmark lane
   - contradiction lane
   - paper-trade promotion gate

Constraints:
- keep the chip benchmark-first
- do not move trading logic into Spark core
- do not add hidden services
- keep the diff reviewable

Verification:
- run chip-local tests
- run `python -m spark_researcher.cli chips validate --config <path-to-config>` from Spark if available
- run `python -m spark_researcher.cli memory sync --config <path-to-config>` from Spark if available
- confirm packet outputs are ledger-derived

Commit often:
- one commit for manifest + contract cleanup
- one commit for packet rewrite + tests
- one commit for docs/watchtower clarification if needed

Final output:
- summarize what changed
- list commands run
- mention any remaining Spark-core dependency that still blocks perfect behavior
```

## Prompt: domain-chip-spark-private

```text
You are in the `domain-chip-spark-private` repo on Desktop.

Objective:
Make this chip portable and runnable through Spark's isolated workflow without losing its bounded Spark-ops doctrine.

You must keep all changes chip-local. Do not edit `spark-researcher`.

Current audited problems to fix:
- Spark `run --command research` fails before hook execution because the repo contains deeply nested live local state under `localhost/paperclip-control-plane/.paperclip-data/...`
- the chip mixes portable chip logic with live embedded ops state
- packet output also shows duplicate document surfaces for repeated winners

Required work:
1. Separate portable chip state from local live runtime state.
2. Make bounded chip evaluation work without requiring embedded Paperclip runtime residue in the repo tree.
3. Move, externalize, or gate local service state so the Spark workspace copy model can succeed on Windows.
4. Add an explicit degraded-mode or bounded-mode path for evaluation if local integrations are absent.
5. Make packeting idempotent and reduce duplicate doc emission where practical.
6. Add documentation explaining:
   - what is portable chip content
   - what is local control-plane state
   - how to reattach local integrations after clone/copy
7. Add tests or smoke checks for:
   - isolated evaluation mode
   - packet generation
   - local integration detection

Constraints:
- keep Spark Researcher as the bounded kernel
- do not hide stateful requirements
- do not silently depend on untracked local residue
- preserve useful ops doctrine/watchtower surfaces

Verification:
- run chip-local tests or smoke checks
- verify a bounded evaluation path works from a clean copy
- if possible, re-run Spark-facing `run`, `memory sync`, and `obsidian build`

Commit often:
- one commit for state separation and portability plumbing
- one commit for bounded-mode evaluation or startup detection
- one commit for docs/tests cleanup

Final output:
- summarize how portability was improved
- specify what still requires local services
- list exact verification commands and outcomes
```

## Prompt: domain-chip-pokemon-red

```text
You are in the `domain-chip-pokemon-red` repo on Desktop.

Objective:
Keep the chip exploratory and powerful, but stop disconnected heuristic scaffold output from being surfaced as if it were grounded benchmark evidence.

You must keep all changes chip-local. Do not edit `spark-researcher`.

Current audited problems to fix:
- when the emulator or ROM is absent, `deterministic_scaffold()` still emits meaningful scores
- packeting and watchtower fallback logic can treat high-scoring disconnected runs too much like real benchmark evidence
- autolearn already has a stricter productivity gate, but Spark-facing memory/watchtower truth surfaces need to match that discipline

Required work:
1. Tighten packeting so grounded doctrine and best-run evidence require real emulator-connected proof.
2. Keep disconnected scaffold output in exploratory frontier only.
3. Make watchtower explicitly show:
   - ROM configured or not
   - emulator connected or not
   - task state loaded or not
   - whether current "best" is grounded or only heuristic
4. Reuse or align with existing stricter gates in autolearn/autopilot where appropriate.
5. Add tests proving:
   - disconnected scaffold rows do not become grounded doctrine packets
   - emulator-connected rows can still produce grounded benchmark evidence
6. Update docs to explain:
   - scaffold versus emulator truth
   - what counts as benchmark proof
   - what remains exploratory

Constraints:
- preserve the emulator-connected path
- do not delete exploratory value
- do not fake grounded evidence
- keep lane distinctions explicit

Verification:
- run chip-local tests
- run packet/watchtower fixture tests
- if possible, run Spark-facing `memory sync` and `obsidian build`

Commit often:
- one commit for packet truth-lane gating
- one commit for watchtower/status clarity
- one commit for tests/docs

Final output:
- summarize the truth-lane changes
- say exactly what now requires emulator connection
- list verification commands run
```

## Prompt: domain-chip-agentic-marketing

```text
You are in the `domain-chip-agentic-marketing` repo on Desktop.

Objective:
Keep this chip as a strong reference for Spark integration while fixing packet slug collisions and duplicate memory surfaces.

You must keep all changes chip-local. Do not edit `spark-researcher`.

Current audited problems to fix:
- packet slugs can collide after truncation
- repeated winners can emit duplicate logical documents that land on the same file path
- the chip is otherwise well integrated and should stay small and coherent

Required work:
1. Make packet slugs collision-safe and stable.
2. Ensure repeated benchmark evidence updates are idempotent where possible.
3. Avoid emitting duplicate logical docs for the same winner unless the content meaningfully changed.
4. Add tests for:
   - unique document slug generation
   - no accidental path collision across similar long labels
5. Add brief docs for:
   - benchmark evidence packets
   - pilot bridge packets
   - what makes a candidate benchmark-grounded versus exploratory

Constraints:
- do not bloat the chip
- preserve current benchmark/pilot bridge semantics
- keep it a clean Spark reference chip

Verification:
- run chip-local tests
- if possible, run Spark-facing `memory sync` and inspect emitted doc paths

Commit often:
- one commit for slug/id stability
- one commit for tests/docs

Final output:
- summarize dedupe and slug changes
- list verification commands and whether packet paths remained unique
```

## Prompt: domain-chip-startup-yc

```text
You are in the `domain-chip-startup-yc` repo on Desktop.

Objective:
Turn this chip into the clean benchmark-reference chip for Spark while making its external benchmark dependency explicit and portable.

You must keep all changes chip-local. Do not edit `spark-researcher`.

Current audited problems to fix:
- the chip is strong, but it depends on a sibling `startup-bench` repo discovered dynamically
- that dependency is real, but not clearly declared as part of the chip contract
- the watchtower/memory surface is large and should highlight current doctrine more clearly

Required work:
1. Make the `startup-bench` dependency explicit in docs and startup checks.
2. Add clear degraded-mode behavior when `startup-bench` is unavailable.
3. Fail or downgrade honestly when benchmark mode cannot run.
4. Add a small operator-facing summary layer that emphasizes:
   - strongest grounded doctrine
   - weakest grounded track
   - next benchmark queue
5. Add tests for:
   - dependency detection
   - degraded-mode truthfulness
   - benchmark packet/watchtower summary behavior where feasible
6. Update docs to explain:
   - external benchmark adapter contract
   - frontier heuristic lane versus benchmark-grounded lane

Constraints:
- keep this chip the benchmark-first reference design
- do not smuggle benchmark logic into Spark core
- preserve the separation between factor frontier and benchmark doctrine

Verification:
- run chip-local tests
- verify behavior with and without `startup-bench` available
- if possible, run Spark-facing `run`, `memory sync`, and `obsidian build`

Commit often:
- one commit for dependency declaration and degraded-mode handling
- one commit for operator summary improvements
- one commit for docs/tests

Final output:
- summarize portability and benchmark-contract improvements
- list exact verification commands and outcomes
```

## Optional Operator Wrapper Prompt

Use this if you want a shorter universal preamble before pasting a chip-specific prompt:

```text
Read the repo first, make the smallest coherent fixes, keep all logic chip-local, add tests for each bug fixed, verify with Spark-facing commands where possible, and commit often in small reviewable batches. Do not edit `spark-researcher` from this repo.
```
