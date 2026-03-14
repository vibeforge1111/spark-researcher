# Vibe Vibe Futarchy And Governance

This document defines a bounded futarchy system for `veSPARK`.

Goal:

- reward informed governance participants
- keep governance tied to measurable venture outcomes
- avoid turning Spark into a public prediction-market venue

## Design Thesis

Use Robin Hanson's `vote on values, bet on beliefs` idea in a restricted incubator context.

Inside Spark:

- `veSPARK` holders vote on values and KPI sets
- approved participants forecast which actions best improve those KPIs
- rewards flow to useful forecasters and contributors, not passive holders

## Bounded Futarchy

Spark should not run raw open-ended public futarchy in v1.

Instead:

- only approved proposal types may enter the system
- only objective settlement metrics may be used
- no leverage
- no public order book
- no external trading venue for forecast positions
- no governance over legal, compliance, or emergency decisions

## Values Layer

`veSPARK` votes on:

- batch success metrics
- project graduation criteria
- support reserve allocation criteria
- project spotlight criteria
- token readiness thresholds

Example value sets:

- retained users after 30 days
- weekly revenue
- customer conversation velocity
- reusable asset creation
- contributor retention

## Beliefs Layer

Participants forecast whether a specific action will improve the chosen value set.

Example forecast questions:

- will project `X` hit `100` retained users if it receives a support reserve boost
- will batch theme `Y` outperform theme `Z` on paid validation
- will treasury buyback support improve contributor retention for project `A`

## Allowed Futarchy Decision Types

- project support reserve deployment
- project spotlight promotion
- curriculum and batch mechanic experiments
- contributor reward policy experiments
- treasury support for reusable asset programs

## Excluded Decision Types

- legal or regulatory interpretation
- sanctions or AML decisions
- founder disputes
- emergency security incidents
- final project token classification
- custody or treasury key decisions

## Proposed Flow

1. proposal is submitted
2. `veSPARK` approves whether it is eligible for futarchy
3. metric set and settlement window are locked
4. evidence packet is attached
5. participants forecast outcomes
6. proposal executes if governance rules allow it
7. metrics settle after the review window
8. forecasters and contributors are rewarded or downgraded

## Forecast Rewards

Recommended reward outputs:

- governance reputation score
- Genesis Credits
- `SPARK` rewards from treasury if policy allows
- curation privileges
- batch access boosts

Do not make rewards purely financial in v1.

## Forecast Penalties

Recommended penalties:

- loss of forecast reputation
- lower governance multiplier
- reduced allocation in future forecast rounds

Avoid wiping core `SPARK` balances for forecast mistakes in v1.

## Evidence Requirement

Every forecast proposal should include:

- objective metric definition
- settlement window
- baseline state
- claim being tested
- supporting evidence
- known failure modes

This is important because uninformed token-weight voting creates noise.

## Abuse Controls

- minimum lock period for forecast eligibility
- identity and sybil friction for high-impact rounds
- per-round stake caps
- no self-settling metrics
- no retroactive metric edits
- conflict disclosures for project insiders

## Clean Governance Flywheel

1. `SPARK` is locked into `veSPARK`
2. `veSPARK` sets values and governance thresholds
3. participants forecast support and batch decisions
4. correct useful forecasters gain more influence and rewards
5. better support decisions improve projects
6. stronger projects improve treasury and ecosystem value

## Anti-Patterns

- open gambling-style positioning
- subjective settlement
- forecast markets on crisis decisions
- whales deciding all support actions without evidence
- confusing futarchy with full autonomous treasury control
