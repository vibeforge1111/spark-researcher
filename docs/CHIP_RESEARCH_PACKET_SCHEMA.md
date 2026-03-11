# Chip Research Packet Schema

Use this schema when a chip starts turning external source material into reusable intelligence.

The goal is to keep the packet small, portable, and strict enough that another chip can reuse the same shape without inheriting startup-specific assumptions.

## Purpose

A research packet is the bridge between:

- source material
- chip memory
- doctrine promotion
- benchmark or real-world testing

It should capture the useful part of a source without turning the memory system into a quote dump.

## Minimal Packet Fields

Required fields:

- `packet_id`
- `domain`
- `source_id`
- `source_type`
- `author`
- `claim`
- `mechanism`
- `boundary`
- `contradiction`
- `confidence`
- `evidence_lane`
- `promotion_status`

Optional but recommended fields:

- `source_title`
- `source_url`
- `quoted_excerpt`
- `tags`
- `benchmark_link`
- `realworld_link`
- `notes`

## Field Meaning

`packet_id`

- stable unique identifier

`domain`

- chip domain such as `startup`, `trading`, `content`, or `coding`

`source_id`

- stable local handle for the source

`source_type`

- examples: `essay`, `talk`, `postmortem`, `dataset`, `benchmark_case`, `interview`

`author`

- source author or organization

`claim`

- the compact lesson or thesis extracted from the source

`mechanism`

- why the claim is supposed to work

`boundary`

- where the claim breaks, weakens, or stops transferring

`contradiction`

- strongest counterexample, dissent, or unresolved tension

`confidence`

- one of:
  - `low`
  - `medium`
  - `high`

`evidence_lane`

- one of:
  - `research_grounded`
  - `benchmark_grounded`
  - `realworld_validated`
  - `exploratory_frontier`

`promotion_status`

- one of:
  - `exploratory`
  - `candidate_doctrine`
  - `promoted_doctrine`
  - `boundary_only`
  - `rejected`

## Rules

- `claim` must be shorter than the source and more reusable than the source wording
- `mechanism` must explain causality, not just restate the claim
- `boundary` must be explicit; if none is known, say that it is still unknown
- `contradiction` must not be silently dropped just because the claim is attractive
- `evidence_lane` and `promotion_status` must not be inferred from tone alone

## Lightweight JSON Shape

```json
{
  "packet_id": "startup-research-yc-essay-founder-market-fit",
  "domain": "startup",
  "source_id": "yc-essay-founder-market-fit",
  "source_type": "essay",
  "author": "Example Author",
  "claim": "Founders who deeply understand the problem space can move faster through ambiguity.",
  "mechanism": "Deep domain understanding improves product judgment and reduces wasted iteration.",
  "boundary": "This weakens when the market is too small or the founder confuses familiarity with demand.",
  "contradiction": "Some outsider founders still win by learning quickly and pairing with strong distribution.",
  "confidence": "medium",
  "evidence_lane": "research_grounded",
  "promotion_status": "candidate_doctrine"
}
```

## Promotion Guidance

Packets do not become doctrine just because they exist.

Suggested rule:

- one packet can justify exploration
- multiple aligned packets can justify `candidate_doctrine`
- doctrine promotion should usually require benchmark support, real-world support, or both

## DSPy Guidance

If DSPy is added, use it to improve one packet-making subroutine at a time, such as:

- mechanism extraction
- boundary extraction
- contradiction extraction
- packet ranking for doctrine promotion

Do not use DSPy first for open-ended ideation.
