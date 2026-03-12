# Chip DSPy Method

Use this document when adding DSPy to any Spark domain chip.

The goal is to keep DSPy:

- narrow
- graded
- portable across chips
- optional at runtime

This is not a general "make the chip smarter" recipe.
It is a method for placing DSPy inside an evidence-first chip loop without turning it into a second runtime or a vague reasoning layer.

## Core Rule

DSPy belongs inside a chip pipeline, not above it.

Good placement:

- after source collection
- after packet schema definition
- after benchmark and memory lanes exist
- before full autonomy increases

Bad placement:

- as the main loop
- as the doctrine authority
- as ungraded ideation
- as a replacement for benchmarks or real-world evals

## The Two Best Default Slots

If a chip is early, use only one slot first.

If a chip is more mature, use two.

### Slot 1: Packet Extractor

Task:

- take source material
- extract a structured research packet

Why this is usually the best first slot:

- it improves the quality of what enters memory
- it improves packet-derived suggestions later
- it is easy to define a fixed schema for
- it can be supervised with hand-authored packets

Typical target fields:

- claim
- mechanism
- boundary
- contradiction
- confidence
- promotion status
- optional domain hints for later probes

This slot improves the intake layer.

### Slot 2: Next-Probe Ranker

Task:

- take a fixed candidate set
- rank which probe or probes should run next

Why this is usually the second slot:

- it improves the loop's spending of trials
- it is naturally tied to later outcomes
- it can be judged against benchmark movement, verdicts, and real-world usefulness

Typical inputs:

- grounded doctrine
- weakest boundary
- research packets
- recent failures
- candidate summaries

This slot improves the decision layer.

## Why These Two Transfer Across Chips

These two slots are portable because every serious chip eventually has:

- source material
- a packet schema
- candidate probes or actions
- downstream outcomes

That means the same DSPy pattern can apply to:

- startup
- trading
- content
- coding

What changes by domain is:

- source type
- packet vocabulary
- benchmark shape
- real-world eval shape

What stays stable is the DSPy placement logic.

## Preconditions

Do not add DSPy to a chip until these exist:

1. A source map
2. A packet schema
3. Evidence-lane separation
4. At least one benchmark or fixed evaluator lane
5. Some real-world eval plan, even if small

Without those, DSPy tends to optimize noise.

## Dataset Pattern

Every DSPy slot should have:

### Input

- fixed input shape

### Target

- fixed output shape

### Metric

- explicit grading rule

### Export path

- a reproducible dataset export file in `artifacts/optimizer`

That means every chip should be able to say:

- where the examples come from
- how the examples are graded
- what the outputs are supposed to look like

## Packet Extractor Dataset

Recommended shape:

- near-source notes or raw source markdown/text
- target packet fields

Prefer near-source notes over already-finished packets when possible.
If the input is already a polished packet, the task becomes reconstruction instead of extraction.

Good supervision source:

- hand-authored packets
- reviewed packets
- promoted packets with stable structure

Metric ideas:

- exact or near-exact match on categorical fields
- overlap or rubric match on claim/mechanism/boundary/contradiction

Field-discipline rule:

- keep prose fields freeform
- keep categorical fields bounded and short
- add post-prediction normalization when providers turn schema ids into paragraphs

## Next-Probe Ranker Dataset

Recommended shape:

- fixed candidate set
- reasons available at suggestion time
- current grounded context
- active research context
- later outcome of each candidate

Good supervision source:

- historical suggestion artifacts
- later benchmark/frontier results
- real-world usefulness labels when available

Best practice:

- one row should represent one actual decision batch
- include the full candidate set and the later winner from that batch
- avoid training only on isolated single-probe aftermath rows

Metric ideas:

- whether top-ranked probes later improved benchmark or real-world score
- whether the ranker avoids low-value residue probes

## Runtime Rule

Keep DSPy optional.

The chip should still run if DSPy is absent.

That means:

- no hard dependency in the core loop
- export datasets independently
- keep DSPy runners as side scripts or bounded subroutines

This preserves Spark's lightweight kernel.

## Artifact Rule

Do not trust process-tail output alone for long DSPy runs.

Every stable DSPy slot should:

- write its score or batch result to an artifact file
- emit the artifact path in stdout
- prefer artifact-first truth over terminal-tail truth

This matters because model calls can complete successfully while teardown or thread shutdown remains messy.

A good default is:

- `artifacts/optimizer/<slot>.last_eval.json`
- `artifacts/optimizer/<slot>.predictions.jsonl`
- `artifacts/optimizer/<slot>.last_batch.json`

## Documentation Pattern

Each chip using DSPy should have:

- one chip-specific DSPy plan doc
- one dataset export script
- one runner per slot
- one note explaining how the slot feeds the loop
- one readiness surface showing whether each slot is actually worth optimizing yet

## Acceptance Checks

A chip's DSPy integration is well-formed only if:

1. The slot is narrow.
2. The slot has a dataset.
3. The slot has a metric.
4. The slot can run without changing the core runtime contract.
5. The chip still works when DSPy is unavailable.
6. The slot improves an existing loop stage rather than inventing a parallel loop.
7. The slot has a documented baseline score or an explicit note that no valid baseline exists yet.

## Anti-Patterns

Reject these:

- "DSPy will make the chip smarter in general."
- "Use DSPy for open-ended ideation first."
- "Use DSPy before packet schema and evals exist."
- "Let DSPy replace doctrine promotion."
- "Hide DSPy behavior inside the main runtime without a clear dataset or metric."

## Recommended Rollout Order

1. Packet extractor
2. Probe ranker
3. Only then consider domain-specific extra slots

That order is portable and keeps the methodology stable across chips.
