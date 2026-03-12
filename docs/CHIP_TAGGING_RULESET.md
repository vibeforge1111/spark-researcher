# Chip Tagging Ruleset

Use this guide when a chip starts turning packet prose into reusable tags.

The goal is to make tags useful for:

- memory retrieval
- packet clustering
- probe generation
- benchmark promotion
- boundary tracking

Tags should help the system remember patterns, not just decorate documents.

## What A Good Tag Is

A good tag is:

- short
- stable
- reusable
- easy to understand
- broad enough to recur
- narrow enough to mean something specific

Examples:

- `weak_user_demand`
- `distribution_dependency`
- `capital_intensity_mismatch`
- `category_only`

## What A Bad Tag Is

A bad tag is:

- too long
- too specific to one source
- emotionally worded
- redundant with the full prose
- likely to be rewritten every week

Examples:

- `the-founder-is-kind-of-right-but-users-dont-care-yet`
- `paul-graham-essay-about-doing-unscalable-work`
- `this-product-only-worked-because-the-market-was-hot-in-2021`

## Main Tag Classes

Use a small number of tag families first.

Recommended families:

- `contradiction_mode`
- `doctrine_tag`
- `factor`
- `operator_function`
- `distribution_mode`
- `benchmark_profile`
- `realworld_task`

The most important early family is usually `contradiction_mode`, because it tells the system how a lesson fails.

## Contradiction Tags

Contradiction tags should answer:

- what kind of weakness is this?
- what condition is missing?
- why would the lesson break or transfer badly?

Examples:

- `retention_without_distribution`
- `category_only`
- `false_pmf_signal`
- `enterprise_complexity_hidden`
- `too_early_for_market`

## Rules For Tag Creation

1. Prefer pattern tags over source tags.

- good: `distribution_dependency`
- bad: `sam_altman_distribution_take`

2. Prefer failure shape over commentary.

- good: `capital_intensity_mismatch`
- bad: `this_seems_too_expensive`

3. Keep tags lowercase and underscore-separated.

4. Avoid synonyms unless there is a real distinction.

Pick one:

- `weak_user_demand`

Avoid keeping all of:

- `weak_user_demand`
- `low_demand`
- `no_real_demand`

5. A tag should survive across many packets.

If it only fits one packet and never appears again, it probably belongs in prose, not in the tag set.

## How Tags Are Used

Tags are not just metadata.

They power:

- retrieval:
  - find packets and runs with the same failure shape
- grouping:
  - cluster similar doctrines and boundaries
- suggestion generation:
  - create probes that pressure-test a known weakness
- promotion:
  - avoid over-promoting doctrine that keeps failing in the same tagged way
- outer validation:
  - send doctrines with important contradiction tags to real-world checks

## Required vs Optional Packet Metadata

For richer chips, separate:

- required structural metadata
- optional inference metadata

Recommended required fields:

- `coverage_areas`
- `doctrine_tags`
- `doctrine_richness`
- `doctrine_richness_score`

Recommended optional fields:

- `factor_hint`
- `quality_signal_hint`
- `transfer_check_hint`
- `contradiction_mode_hint`

The required fields should be fully populated across the packet corpus.

The optional fields should improve over time, but should not be forced with weak guesses just to make a packet look complete.

## DSPy Policy

DSPy should help with tags, but should not define the tag system.

Recommended approach:

1. define the tag set by hand
2. let DSPy extract the rich prose first
3. let DSPy suggest tags from the allowed set
4. use light rule-based post-processing where the mapping is obvious
5. review new or unstable tag suggestions before expanding the registry

This keeps the tags stable while still benefiting from model help.

## Recommended Workflow

1. write or extract:
   - claim
   - mechanism
   - boundary
   - contradiction
2. assign tags from a fixed registry
3. only add a new tag if multiple packets clearly need it
4. document every new stable tag in the chip registry

## Promotion Rule For New Tags

Do not create a new stable tag because one packet used unusual wording.

A new tag should usually require:

- at least two or three packets that need the same pattern
- no existing tag that already fits
- a clear future use in retrieval or evaluation

## Relationship To Packet Schema

The packet schema defines the fields.

This tagging guide defines how short reusable pattern labels should be created from those fields.

See also:

- [C:\Users\USER\Desktop\spark-researcher\docs\CHIP_RESEARCH_PACKET_SCHEMA.md](C:/Users/USER/Desktop/spark-researcher/docs/CHIP_RESEARCH_PACKET_SCHEMA.md)
- [C:\Users\USER\Desktop\spark-researcher\docs\CHIP_DSPY_METHOD.md](C:/Users/USER/Desktop/spark-researcher/docs/CHIP_DSPY_METHOD.md)
