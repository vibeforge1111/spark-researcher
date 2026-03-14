# Vibe Vibe Token Stack

This document defines the clean token architecture for the vibe startup incubator.

It is optimized for:

- utility and governance before speculation
- quote-asset revenue for Spark treasury
- project-level upside flowing through contribution and governance rails
- incubator-first branding rather than launchpad-first branding

This is an operating design document, not legal advice.

## Core Principles

- Spark should earn in `ETH` / `USDT`, not depend on receiving project tokens as fees.
- Spark should look like an incubator OS, proof engine, and governance layer.
- Project trading should happen on external Uniswap-based rails, not inside the Spark site.
- Spark holders should not receive automatic passive volume-yield messaging in v1.
- Project token exposure should flow through active contribution, governance, and treasury policy.

## Token Layers

### 1. `SPARK`

Base ecosystem token.

Use it for:

- governance entry
- access and status
- batch perks
- fee discounts
- curation eligibility

Do not treat raw `SPARK` as a passive income right.

### 2. `veSPARK`

`veSPARK` is vote-escrowed `SPARK`.
Users lock `SPARK` for a chosen duration and receive non-transferable governance weight.

Use `veSPARK` for:

- treasury allocation votes
- batch theme and promotion votes
- support reserve deployment votes
- bounded futarchy participation
- incubator parameter tuning

### 3. `Project Genesis Credits`

Non-transferable project-specific contribution credits earned before a project token launch.

Use them for:

- proving early support
- rewarding testers, contributors, growth helpers, and reviewers
- ranking contributors for future claim rights

These should not be freely tradable.

### 4. `Project Claim Rights`

A gated right to claim a future project token allocation if the project graduates.

Claim rights should exist only after:

- utility is live
- token readiness review passes
- project disclosures are ready
- launch parameters are approved

### 5. `Project Utility / Governance Token`

The startup's own token.

It should launch only after:

- product utility exists
- governance scope is explicit
- treasury and fee routing are clear
- the project has real users or real usage

## Fee Flow

Recommended fee flow:

1. trading activity occurs on external Uniswap rails with Spark hook logic
2. Spark fee share lands in quote asset such as `ETH` / `USDT`
3. Spark treasury routes those assets into budget buckets

Recommended treasury buckets:

- operating treasury
- security and incident reserve
- founder support reserve
- project support reserve
- ecosystem contributor rewards

## Project Support Reserve

Spark can support the best graduated projects without promising passive yield.

Recommended policy:

- reserve accumulates in quote asset
- governance may deploy a capped portion into secondary-market buybacks of selected graduated project tokens
- those bought tokens go to active ecosystem programs, not passive holder streaming

Examples:

- contributor reward pools
- project-specific quest pools
- ecosystem grants
- founder support programs
- strategic treasury inventory

## What Spark Should Avoid

- automatic fee pass-through to passive holders
- promising project-token upside as the main reason to hold `SPARK`
- mixing incubator governance with direct investment language
- forcing every startup to tokenize before product utility exists

## Clean Version Of The Flywheel

1. founders build inside the incubator
2. projects produce proof, traction, and utility
3. external Uniswap rails generate fee flow
4. Spark treasury earns in quote asset
5. `veSPARK` governs treasury use and support routing
6. top projects receive governance-approved support
7. contributors and builders capture project upside through claim-right and contribution systems

## Anti-Goals

- "hold token, earn volume" as the main value proposition
- low-utility project token launches
- incubator branding collapsing into launchpad branding
- unclear treasury rights
- distributing weak project tokens as incentives just because they exist
