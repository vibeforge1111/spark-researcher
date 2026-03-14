# Vibe Vibe Product Surfaces

This document locks the first implementation target for the product-facing app.

Base the surface architecture on `Autoresearch Collective`:

- left activity rail for mode and batch navigation
- large central work surface for proof, quests, venture operations, and governance
- right detail sidebar for selected entity context, not modal-heavy flows
- monospace-first data UI with strong borders and calm density
- persistent bottom status strip for loop and system state

## Core Principle

`Vibe Vibe` should look like an operator console for founder proof and venture progress.

It should not look like:

- a generic accelerator landing page
- a memecoin launchpad
- a trading terminal as the primary brand surface

## Primary Product Areas

### Public Surface

- batch index
- venture proof pages
- quest board
- contributor profiles
- public proof feed
- application entry and proof sprint entry

### Founder Surface

- founder home
- venture control panel
- weekly packet review
- experiment board
- build requests
- customer and pipeline board
- token readiness

### Operator Surface

- batch dashboard
- admissions queue
- office hours packets
- trust board
- capital readiness
- portfolio learning
- treasury and governance actions

### Governance Surface

- proposals
- forecast markets
- treasury actions
- batch support votes
- project support reserve decisions

## Shell Layout

Mirror the Collective shell closely:

- left rail: `160px`
- detail sidebar: `414px`
- bottom status bar: `24px`
- app frame owns the viewport
- scroll only inside panels and views

### Left Rail

- product switcher
- current batch
- ventures
- quests
- governance
- treasury
- admissions
- settings

### Main Surface

Render one dense working view at a time:

- proof feed
- venture page
- admissions review board
- quest operations board
- governance proposal view
- treasury allocation board

Use view intros at the top of major modes, matching the Collective pattern.

### Right Sidebar

Use the sidebar for:

- selected founder summary
- selected venture metrics
- risk flags
- action checklist
- linked artifacts
- recent decisions

Build the sidebar from collapsible sections, not freeform stacked cards.

## Screen Priority For Phase 1

Build these first:

1. batch dashboard
2. venture proof page
3. founder workspace
4. quest board
5. admissions queue
6. governance and treasury panel

## Design Constraints

- public proof pages should be primary
- token charts and swap links should be visually secondary
- external market action should never dominate the page hierarchy
- every important page should expose objective proof, tasks, and next actions
- avoid marketing-site hero sections inside the authenticated shell
- prefer direct adaptation of a Collective pattern before inventing a new layout

## Visual Upgrades Beyond The Collective

Keep the shell nearly `1:1`, but add stronger incubator-native visuals:

- cohort health heatmap
- venture proof timeline
- contribution sankey
- token readiness radar
- treasury allocation board
- venture relationship graph

## Implementation Note

Keep the legacy repo and package naming until a later mechanical rename.

The visible product language for the app, docs, and UI should be `Vibe Vibe`.
