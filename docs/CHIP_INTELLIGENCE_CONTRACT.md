# Chip Intelligence Contract

Use this contract when you want a chip to become more intelligent without becoming heavier.

The startup chip is the first proving ground. The goal is not to freeze startup assumptions into core. The goal is to define a portable pattern that other chips can reuse with their own domain sources, benchmarks, and real-world checks.

## Intent

A serious chip should know:

- where to pull the best source material from
- which people and materials deserve more trust than generic web residue
- how to convert source material into reusable doctrine and boundaries
- how to test that doctrine against benchmarks and real work
- where a narrow inference optimizer such as DSPy can help without becoming a theatrical "brain layer"

## Domain-Neutral Structure

Every chip should define the same five surfaces.

1. Source registry

- best people
- best primary materials
- best datasets or benchmark corpora
- best real-world feedback loops

2. Research packet

- `source_id`
- `source_type`
- `author`
- `claim`
- `mechanism`
- `boundary`
- `contradiction`
- `confidence`
- `promotion_status`

3. Evidence lanes

- `research_grounded`
- `benchmark_grounded`
- `realworld_validated`
- `exploratory_frontier`

4. Promotion policy

- what can become doctrine
- what becomes a boundary
- what stays exploratory
- what requires human review

5. Inference slots

- extractor
- ranker
- doctrine drafter
- next-probe selector

These are slots, not requirements to add a framework. If a chip does not have a graded use for a slot yet, leave it empty.

## Separation Rule

Keep the pattern generic and the content domain-specific.

Chip-generic:

- registry structure
- packet schema shape
- evidence-lane names
- promotion rules
- evaluation shape
- watchtower page types

Domain-specific:

- which sources matter
- which people count as canonical
- what counts as a benchmark
- what counts as a real-world task
- what mechanisms and boundaries mean in that domain

Do not promote startup-specific labels into the contract unless another chip truly needs the same abstraction.

## Lightweight Build Order

Use this order.

1. Source map

- define the strongest people, materials, datasets, and feedback loops
- keep this in docs first

2. Research packet schema

- define how external evidence becomes reusable chip memory
- prefer a few stable fields over a long flexible schema

3. Evidence-lane separation

- keep `research_grounded`, `benchmark_grounded`, `realworld_validated`, and `exploratory_frontier` distinct
- do not let them compete as if they were interchangeable

4. Promotion rules

- doctrine requires stronger evidence than exploratory notes
- boundaries require concrete failure or transfer evidence
- real-world promotion requires explicit human review during stabilization

5. DSPy or other optimizer

- only add it to one narrow graded subroutine first
- examples: mechanism extraction, contradiction extraction, doctrine drafting, next-probe ranking
- reject open-ended optimizer use without a grader

6. Real-world eval set

- add a small external task set that proves the chip is helping real work
- examples depend on the chip domain

## Minimum Standard

Before calling a chip "intelligent" in the stronger sense, require:

- one source registry
- one research packet schema
- one benchmark lane or equivalent fixed evaluator lane
- one exploratory lane
- one current working-state summary
- one real-world evaluation surface, even if it is small and partly human-graded

## Anti-Patterns

Treat these as warnings:

- treating scraped quantity as intelligence
- promoting source residue directly into doctrine
- adding DSPy before defining a graded subroutine
- comparing research-grounded, benchmark-grounded, and exploratory scores in one lane
- using the watchtower as truth when the raw artifacts disagree
- creating a new framework layer instead of a small contract plus one proving-ground chip

## Recommended Outputs

Each mature chip should eventually expose:

- a source map doc
- a packet schema doc
- a promotion policy doc
- a real-world eval doc
- watchtower pages that separate grounded doctrine from exploratory work

## Startup First, Then Transfer

Implement the contract concretely in one chip first.

Recommended order:

1. startup
2. one second chip with a different evidence shape
3. only then promote shared patterns into stronger core guidance

That keeps Spark small and forces abstractions to earn their place.

## Related Docs

- `docs/CHIP_RESEARCH_PACKET_SCHEMA.md`
- `docs/CHIP_INTELLIGENCE_ROLLOUT.md`
- `docs/CHIP_BENCHMARK_BRIDGE_GUIDE.md`
