# Reliability Test Plan

Use this guide when you want to assess whether Spark Researcher is behaving like a small, honest, evidence-aware intelligence rather than just producing plausible output.

This is more detailed than [CHECKLOOP](C:\Users\USER\Desktop\spark-researcher\docs\CHECKLOOP.md). `CHECKLOOP` proves the repo still runs. This plan checks whether the architecture is reliable one subsystem at a time.

## Test Goal

Prove these claims, in order:

1. Spark does not bluff when evidence is weak.
2. Spark prefers stronger memory over weaker memory.
3. Spark can compare answer candidates instead of trusting the first draft.
4. Spark can escalate to bounded research when freshness matters.
5. Spark cites and traces what it used.
6. Spark keeps memory lightweight and contradiction-aware.
7. Obsidian reflects the real runtime state rather than a cleaned-up story.

## How To Score

Use this simple rubric for every section:

- `pass`
  - the expected behavior happened cleanly
- `warn`
  - behavior was directionally right, but weak, brittle, or incomplete
- `fail`
  - behavior contradicted the design goal or produced misleading output

For every `warn` or `fail`, record:

- what command you ran
- what artifact or trace you inspected
- what you expected
- what actually happened
- whether the problem is runtime logic, memory quality, tracing, or watchtower display

## Recommended Order

Run the sections in this order:

1. baseline sanity
2. advisory honesty
3. packet retrieval quality
4. verifier quality
5. research grounding
6. belief durability and contradiction handling
7. watchtower truthfulness
8. full-system spot check

## Baseline Sanity

### Purpose

Make sure you are testing a runnable repo before judging intelligence behavior.

### Commands

```powershell
cd C:\Users\USER\Desktop\spark-researcher
python -m pip install -e .
python -m compileall src\spark_researcher
spark-researcher line-budget --limit 11000
spark-researcher summary --config spark-researcher.project.json
```

### Expected

- compile passes
- line budget stays under `11000`
- summary returns `ledger` and `traces`
- no crash before any intelligence-specific testing starts

### Inspect

- terminal output
- `artifacts/traces/index.jsonl` if present

### Fail Conditions

- compile error
- line budget exceeded
- summary command crash

## Advisory Honesty

### Purpose

Verify that Spark distinguishes `grounded`, `partial`, and `under_supported` instead of pretending everything is answerable.

### Commands

```powershell
spark-researcher advisory build --task "summarize the strongest current learning rate rule" --model generic
spark-researcher advisory build --task "what is the latest model release right now" --model generic
spark-researcher advisory build --task "give a permanent doctrine from no local evidence at all" --model generic
```

### What To Check

- `epistemic_status.status`
- `epistemic_status.missing_evidence`
- `epistemic_status.clarifying_questions`
- `packet_stability`
- `selected_packet_ids`

### Expected

- grounded tasks have selected packets plus boundaries
- provisional-only belief support tends to downgrade to `partial`
- weak tasks ask clarifying questions or mark missing evidence
- time-sensitive tasks should feel research-pressured, not overconfident

### Reliability Questions

- Does advisory ever claim `grounded` when all belief support is provisional?
- Does it surface contradiction pressure in `missing_evidence`?
- Are clarifying questions actually useful, or generic filler?

### Pass Criteria

- no obviously weak task is labeled `grounded`
- provisional-only support is visible in packet stability
- advisory output would make a cautious operator slow down

## Packet Retrieval Quality

### Purpose

Verify that packet search prefers durable beliefs over provisional ones without hiding weaker local evidence.

### Commands

```powershell
spark-researcher packets search "learning rate"
spark-researcher packets search "weight decay"
spark-researcher packets status
spark-researcher beliefs build
```

### What To Check

- packet ordering
- `kind`
- `memory_status`
- `contradiction_count`
- `confidence`

### Expected

- durable beliefs rank above provisional beliefs on the same topic
- contradictory beliefs are still visible, but slightly lower
- non-belief packets can still appear if they are the best match

### Reliability Questions

- Are durable beliefs actually being preferred?
- Are contradictory beliefs still discoverable?
- Does packet search accidentally overfit to belief docs and ignore useful non-belief packets?

### Pass Criteria

- durable beats provisional when both match
- contradiction count affects ranking but does not erase visibility
- results still look semantically relevant, not just metadata-biased

## Verifier Quality

### Purpose

Verify that Spark compares bounded candidates and can stop, revise, or escalate instead of blindly approving the first draft.

### Commands

```powershell
spark-researcher advisory execute --task "draft a startup doctrine update" --model claude --dry-run --command "my-wrapper {system_prompt_path} {user_prompt_path} {response_path}"
spark-researcher summary --config spark-researcher.project.json
```

If you have a working provider command configured, also run:

```powershell
spark-researcher advisory execute --task "draft a startup doctrine update" --model claude
```

### What To Check

- dry-run steps should include `draft_a`, `draft_b`, `select`, `optional_revise`
- runtime traces should include `selected_candidate`
- watchtower should show verifier selection count and top issues

### Expected

- verifier chooses one draft explicitly
- revision operates on the chosen draft, not an arbitrary one
- under-supported cases return `needs_verification` or `research_needed`

### Reliability Questions

- Does the verifier ever approve a weak answer with obvious missing evidence?
- Does it select one candidate consistently, or look random?
- Do top issues in traces match the actual weaknesses in the answer?

### Pass Criteria

- selection is explicit and traceable
- weak evidence leads to caution, not bluffing
- revision path appears coherent

## Research Grounding

### Purpose

Verify that Spark escalates to one bounded research pass when freshness matters and carries real source provenance forward.

### Commands

Use a time-sensitive prompt with web enabled in project intent if available:

```powershell
spark-researcher advisory execute --task "what is the latest current release of X and what changed" --model claude
spark-researcher summary --config spark-researcher.project.json
```

### What To Check

- `research_needed` path appears when appropriate
- bounded retry happens once
- returned `citations` include:
  - `note_id`
  - `domain`
  - `url`
  - `collected_at`
- `research_context.attempted` prevents recursive looping

### Inspect

- `artifacts/advisory/research/*.json`
- `artifacts/traces/*.jsonl`
- `obsidian-vault/05-Runtime/Research Signals.md`

### Expected

- time-sensitive misses escalate to research
- stale or weak support does not get disguised as current truth
- one retry only

### Pass Criteria

- no infinite research loop
- provenance survives into returned citations
- watchtower shows domains and URLs that match the artifact

## Citation Discipline

### Purpose

Verify that research-backed answers actually cite the notes they use and prefer the most relevant notes.

### Commands

Run a research-backed advisory task, then inspect:

```powershell
spark-researcher summary --config spark-researcher.project.json
spark-researcher obsidian build --config spark-researcher.project.json
```

### What To Check

- citation checks occur
- citation mismatches are counted
- relevant note ids are recorded
- answer does not get approved when it ignores available notes

### Expected

- uncited research-backed draft gets revised
- weak or unrelated note choice gets revised
- best matching note ids appear in traces

### Pass Criteria

- approval requires citation use on research-backed tasks
- mismatch count increases only when there is a real mismatch

## Belief Durability And Contradictions

### Purpose

Verify that Spark does not silently store competing lessons as if they are equally settled.

### Commands

```powershell
spark-researcher beliefs build
```

### Inspect

- [docs/beliefs/manifest.json](C:\Users\USER\Desktop\spark-researcher\docs\beliefs\manifest.json)
- [docs/beliefs/INDEX.md](C:\Users\USER\Desktop\spark-researcher\docs\beliefs\INDEX.md)
- [docs/beliefs/CONTRADICTIONS.md](C:\Users\USER\Desktop\spark-researcher\docs\beliefs\CONTRADICTIONS.md)

### What To Check

- `durable_belief_count`
- `provisional_belief_count`
- `contradiction_count`
- each belief doc’s `belief_status`
- contradiction summaries name the conflicting belief ids and fields

### Expected

- replicated lessons with no active contradiction become `durable`
- conflicting promoted lessons become `provisional`
- contradiction report is readable, not hidden in raw JSON only

### Pass Criteria

- memory status reflects evidence quality
- contradictions are visible and not silently flattened

## Watchtower Truthfulness

### Purpose

Verify that Obsidian mirrors runtime truth rather than a cleaned-up summary.

### Commands

```powershell
spark-researcher obsidian build --config spark-researcher.project.json
```

### Inspect

- `obsidian-vault/Home.md`
- `obsidian-vault/05-Runtime/Research Signals.md`

### What To Check In Home

- durable belief count
- provisional belief count
- active contradiction count
- research retry count
- citation mismatch count

### What To Check In Research Signals

- trace ids
- selected packet ids
- packet stability
- verifier selection events
- note ids
- domains
- URLs
- top issue

### Expected

- watchtower counters match `summary`
- signal entries carry the same ids seen in trace artifacts
- no obvious mismatch between trace files and Obsidian rendering

### Pass Criteria

- operator can reconstruct what Spark used, selected, and doubted from the watchtower alone

## Full-System Spot Check

### Purpose

Run the main paths together and judge whether the system behaves like the architecture claims.

### Commands

```powershell
spark-researcher trainers run
spark-researcher memory sync
spark-researcher beliefs build
spark-researcher packets search "learning rate"
spark-researcher advisory build --task "summarize the strongest current learning rate rule" --model generic
spark-researcher summary --config spark-researcher.project.json
spark-researcher obsidian build --config spark-researcher.project.json
```

### Final Questions

- Does Spark separate strong evidence from weak evidence?
- Does it remember cautiously?
- Does it compare candidates instead of trusting the first one?
- Does it escalate to research only when needed?
- Does it preserve provenance?
- Does the watchtower tell the truth?

### Final Verdict Template

Use this template after the run:

```md
# Reliability Verdict

- overall: pass|warn|fail
- advisory honesty: pass|warn|fail
- packet retrieval: pass|warn|fail
- verifier quality: pass|warn|fail
- research grounding: pass|warn|fail
- citation discipline: pass|warn|fail
- belief durability: pass|warn|fail
- watchtower truthfulness: pass|warn|fail

## Top Failures

- issue:
  evidence:
  likely layer:
  next fix:

## Trust Boundary

- what Spark is currently reliable for:
- what still needs operator caution:
```

## Priority Of Findings

If multiple things fail, fix them in this order:

1. bluffing or false confidence
2. broken research provenance
3. bad verifier selection or false approval
4. contradiction-blind memory promotion
5. watchtower mismatches
6. ranking quality or ergonomics

## Rule

Do not call the system reliable just because commands run.

Call it reliable only if:

- the runtime behaves cautiously when it should
- evidence quality changes the answer behavior
- the traces match the watchtower
- memory promotion reflects actual support, not narrative confidence
