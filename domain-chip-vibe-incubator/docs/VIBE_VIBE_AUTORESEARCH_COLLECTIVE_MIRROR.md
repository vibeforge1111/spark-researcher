# Vibe Vibe Autoresearch Collective Mirror

This document extracts the real interface grammar from the `Autoresearch Collective` repo and maps it into `Vibe Vibe`.

Goal:

- keep the shell and interaction discipline almost `1:1`
- change the domain objects from repos and runs to batches, ventures, quests, contributions, and governance
- make the result even more data-visual for incubation operations

## Source Files Reviewed

Direct repo sources:

- `..\autoresearch-collective\dashboard\src\App.tsx`
- `..\autoresearch-collective\dashboard\src\App.css`
- `..\autoresearch-collective\dashboard\src\index.css`
- `..\autoresearch-collective\dashboard\src\components\ViewIntro.tsx`
- `..\autoresearch-collective\dashboard\src\components\RepoGridView.tsx`
- `..\autoresearch-collective\dashboard\src\components\RunsGridView.tsx`
- `..\autoresearch-collective\dashboard\src\components\InsightsGridView.tsx`
- `..\autoresearch-collective\dashboard\src\components\StatusView.tsx`
- `..\autoresearch-collective\dashboard\src\components\NetworkGraph.tsx`
- `..\autoresearch-collective\dashboard\src\components\SkillTree.tsx`
- `..\autoresearch-collective\dashboard\src\components\StartupLivePane.tsx`
- `..\autoresearch-collective\dashboard\src\components\XpSystemView.tsx`

## Exact Shell To Mirror

`Autoresearch Collective` uses a terminal-like app shell:

- `160px` left activity rail
- flexible main work surface
- `414px` right detail sidebar
- `24px` bottom status bar
- full-viewport height
- inner scrolling only

`Vibe Vibe` should mirror this almost exactly.

## Interaction Grammar To Mirror

### Left Rail

The Collective treats navigation as command modes, not as a content sitemap.

`Vibe Vibe` should do the same.

Map it like this:

- `Repos` -> `Batches`
- `Runs` -> `Ventures`
- `Insights` -> `Proof`
- `Connect` -> `Apply`
- `Status` -> `Operator`
- `Graph` -> `Network`
- `Skill Tree` -> `Contribution Map`
- `XP` -> `Genesis`
- `Activity` -> `Feed`
- `Live Loop` -> `Autoloop`
- `Guides` -> `Curriculum`
- `Terminal` -> `Ops`

### Main Surface

The Collective always renders one dominant view at a time.

`Vibe Vibe` should keep that:

- no split marketing layouts
- no dashboard soup
- one mode, one primary working surface

### Right Sidebar

The Collective uses collapsible context panes.

`Vibe Vibe` should keep the same structure:

- selected batch or venture
- selected proof artifact
- current action queue
- autoloop summary
- system and treasury state

### Bottom Status Bar

Keep the persistent strip.

It should show:

- current batch
- active ventures
- queued reviews
- autoloop state
- trust alerts
- treasury state
- signed-in operator status

## Visual System To Mirror

### Typography

The repo uses:

- `Geist Mono`
- `JetBrains Mono`
- `IBM Plex Mono`
- `Fira Code`

`Vibe Vibe` should keep the same monospace-first posture for:

- metrics
- cards
- proof logs
- governance state
- contribution ledgers

### Color System

The repo uses:

- warm off-white light theme
- blue-black dark theme
- navy/ink accent
- muted semantic green, amber, cyan, red

`Vibe Vibe` should preserve this color philosophy.

Do not switch to:

- meme gradients
- purple neon
- finance-terminal green/red dominance

### Surface System

The Collective uses:

- hard-edged panels
- thin borders
- compact shadows
- small badges and chips
- dense cards with small spacing

`Vibe Vibe` should keep this exact surface logic.

## Component Mappings

### Grid Views

Collective grid patterns:

- `RepoGridView` for indexed units
- `RunsGridView` for time-sequenced execution records
- `InsightsGridView` for promoted learnings

`Vibe Vibe` equivalents:

- `BatchGridView`
- `VentureGridView`
- `ProofGridView`
- `QuestGridView`
- `GovernanceGridView`

Keep the same structure:

- top filter/search toolbar
- dense cards
- compact metadata
- chips for tags and status

### Status View

The Collective status view uses large metric cards plus system checks.

`Vibe Vibe` should mirror this with:

- ventures
- proofs
- contributors
- queued reviews
- capital-ready projects
- system checks for trust, governance, treasury, and loop health

### Graph View

The Collective graph is a pan/zoom/hover canvas with force layout and typed nodes.

`Vibe Vibe` should keep the same interaction model but change the graph semantics:

- batch nodes
- venture nodes
- contributor nodes
- reusable asset nodes
- token readiness nodes
- treasury support edges
- contribution lineage edges

### Skill Tree

The Collective skill tree is a second canvas view that visualizes growth hierarchy.

`Vibe Vibe` should repurpose this into:

- contributor progression map
- founder progression map
- batch quest unlock tree

### Live Loop

The Collective live pane is one of the strongest references.

`Vibe Vibe` should mirror it closely:

- hero loop state
- current pass status
- recent proof events
- recommended next move
- structured collapsible sections
- recent accepted and rejected items

For `Vibe Vibe`, this becomes:

- batch autoloop pulse
- venture recommendations
- admissions decisions
- proof routing
- governance actions pending
- support reserve actions pending

## Where Vibe Vibe Should Be More Visual

This is the key deviation.

Keep the Collective shell, but make the incubation domain more visual in these places:

### Cohort Heatmap

Show every venture in the batch across:

- shipping velocity
- customer proof
- revenue proof
- contribution energy
- token readiness
- trust posture

### Proof Timeline

Every venture should have a visual timeline of:

- launches
- demos
- customer calls
- paid signals
- build requests
- governance milestones

### Contribution Sankey

Visualize:

- contributor source
- quest worked
- proof generated
- Genesis Credits earned
- claim-right outcome

### Venture Network Map

Extend the graph view so it shows:

- shared contributors
- shared reusable assets
- support reserve exposure
- governance attention
- customer overlap

### Token Readiness Radar

Use a radar or polygon chart for:

- product utility
- retention proof
- governance clarity
- trust/compliance hygiene
- contribution quality
- treasury readiness

### Treasury Allocation Board

A visual allocation surface should show:

- quote-asset treasury balance
- support reserve distribution
- buyback candidates
- governance proposals
- realized vs pending support

## Non-Negotiable Product Constraint

Even when token data is present:

- proof comes before price
- venture health comes before token chart
- contribution value comes before speculation
- external swap routes stay visually secondary

## Implementation Rule

If there is a choice between:

- a new custom layout
- and a direct adaptation of an existing Collective surface

prefer the direct adaptation unless the incubator domain clearly needs a stronger data visualization.
