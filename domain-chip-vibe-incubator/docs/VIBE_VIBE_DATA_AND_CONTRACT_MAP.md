# Vibe Vibe Data And Contract Map

This document defines the minimum data model and contract modules for implementation.

## Core Product Entities

### User

- `user_id`
- `display_name`
- `wallets`
- `roles`
- `reputation_score`
- `geo_policy_state`

### Founder

- `founder_id`
- `user_id`
- `venture_ids`
- `batch_ids`
- `status`

### Venture

- `venture_id`
- `founder_id`
- `batch_id`
- `label`
- `stage`
- `bottleneck`
- `token_readiness_state`
- `proof_page_slug`

### Batch

- `batch_id`
- `label`
- `season`
- `status`
- `theme`
- `cohort_metrics`

### Quest

- `quest_id`
- `venture_id`
- `type`
- `difficulty`
- `evidence_requirements`
- `status`

### Contribution

- `contribution_id`
- `quest_id`
- `user_id`
- `evidence_links`
- `review_state`
- `impact_score`

### Genesis Credit Ledger Entry

- `entry_id`
- `venture_id`
- `user_id`
- `reason`
- `amount`
- `pending_amount`
- `status`

### Claim Right

- `claim_right_id`
- `venture_id`
- `user_id`
- `genesis_credit_basis`
- `cap`
- `vesting_policy`
- `status`

### Governance Proposal

- `proposal_id`
- `scope`
- `metric_set`
- `settlement_window`
- `state`

### Forecast Position

- `position_id`
- `proposal_id`
- `user_id`
- `signal`
- `weight`
- `evidence_packet`
- `settlement_state`

### Treasury Action

- `treasury_action_id`
- `scope`
- `asset`
- `amount`
- `destination`
- `approval_state`

## Public Product Modules

- proof feed
- batch pages
- project pages
- contributor profiles
- governance views
- treasury reports

## Member Product Modules

- founder workspace
- quest board
- contribution review
- claim-right dashboard
- token readiness dashboard
- governance participation

## Smart Contract Modules

### `SPARK`

Base token.

### `veSPARK`

Locking and governance weight module.

### `GenesisCreditsRegistry`

Non-transferable registry for project-specific Genesis Credits.

### `ClaimRightsRegistry`

Stores project-specific capped claim rights.

### `ProjectReadinessRegistry`

Tracks which projects are approved for launch routing.

### `SupportReserveController`

Treasury-controlled support reserve deployment logic.

### `GovernanceModule`

Proposal creation, voting, bounded futarchy eligibility, settlement references.

### `UniswapHookConfigRegistry`

Stores project hook configuration metadata and approved route details.

## Offchain Services

- auth and session
- quest scoring
- evidence storage
- sybil and abuse detection
- metric settlement
- treasury reporting
- route and policy checks

## Critical Boundaries

- no on-site swap execution in v1
- no custody assumptions in app logic
- no token launch until readiness gate passes
- no Genesis Credit transferability
- no passive fee-yield contract surface in v1

## Implementation Rule

Start with boring data structures.
Only move logic onchain when it needs:

- verifiable ownership
- verifiable locking
- verifiable claim rights
- governance enforcement
