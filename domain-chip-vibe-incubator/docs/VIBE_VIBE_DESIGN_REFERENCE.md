# Vibe Vibe Design Reference

This document captures the visual and interaction direction for `Vibe Vibe`.

Base the product on the live `Autoresearch Collective` design language, not on generic launchpad or crypto-dashboard tropes.

## Core Visual Thesis

`Vibe Vibe` should feel like:

- a research and operating system
- a serious collective workspace
- an evidence-heavy founder network
- a calm but sharp control surface

It should not feel like:

- a casino
- a pump board
- a neon meme terminal
- a generic accelerator landing page

## Reference Signals From Autoresearch Collective

The repo confirms a much stricter system than a generic dashboard.

Direct source references:

- `..\autoresearch-collective\dashboard\src\App.tsx`
- `..\autoresearch-collective\dashboard\src\App.css`
- `..\autoresearch-collective\dashboard\src\index.css`
- `..\autoresearch-collective\dashboard\src\components\RepoGridView.tsx`
- `..\autoresearch-collective\dashboard\src\components\RunsGridView.tsx`
- `..\autoresearch-collective\dashboard\src\components\InsightsGridView.tsx`
- `..\autoresearch-collective\dashboard\src\components\NetworkGraph.tsx`
- `..\autoresearch-collective\dashboard\src\components\StartupLivePane.tsx`
- `..\autoresearch-collective\dashboard\src\components\ViewIntro.tsx`

The strongest patterns worth keeping:

- fixed three-zone shell instead of fluid marketing-page composition
- persistent bottom status bar
- left navigation as mode switches, not decorative sidebar links
- right detail rail built from collapsible sections
- grid and card views treated as operational datasets
- graph and live views treated as first-class modes, not novelty widgets
- intros per view to explain the operating purpose of each mode
- monospace-first typography with restrained color usage

## Typography

Use a typography split:

- monospace-first for data, proofs, logs, metrics, run surfaces
- restrained sans-serif support for brand, intros, and selected display elements

Tone:

- compact
- legible
- information-dense
- not playful for its own sake

## Color Direction

Use the same general philosophy as the Collective:

- warm off-white light mode instead of pure white
- deep charcoal / blue-black dark mode instead of pure black
- navy / ink accent instead of high-saturation crypto neon
- semantic colors only for state, not as decoration

Suggested behavior:

- green means validated or healthy
- amber means review needed
- red means trust or operational risk
- accent color should signal structure, not hype

## Layout System

Use a three-zone application shell:

1. activity rail
2. primary work surface
3. contextual detail sidebar

This is a better fit than a marketing-site layout because `Vibe Vibe` is an operating environment first.

The exact shell should stay close to the Collective:

- left rail around `160px`
- detail sidebar around `414px`
- bottom status strip around `24px`
- central surface fills remaining width
- full-height app shell with no scroll on the outer frame
- inner panes own their own scrolling

## Surface Types

Required surface families:

- proof pages
- cohort dashboards
- founder workspaces
- contributor quest boards
- treasury and governance views
- token readiness views
- portfolio learning views
- live loop and operational status views

## Interaction Style

- keyboard-friendly
- obvious hierarchy
- minimal ornamental motion
- dense data without clutter
- clean details / summary patterns for secondary controls

Prefer:

- tabs, cards, and drawers
- graphs when topology matters
- timelines when sequences matter
- panels when operator context matters
- hover tooltips, filters, and persistent chips for dense data review
- canvas-based visualizations when topology or progression matters

Avoid:

- giant hero-first layouts
- oversized token charts as the primary object
- decorative glassmorphism
- noisy launchpad gradients

## Brand Direction

`Vibe Vibe` should present as:

- founder collective
- startup operating system
- proof-to-genesis network

Do not lead with "launchpad."
Lead with:

- build
- proof
- contribute
- govern

## Naming Direction

Visible product name:

- `Vibe Vibe`

Legacy repo and package names may remain temporarily until the runtime rename pass.

## Immediate Design Rules

- keep the app shell and panel discipline from `Autoresearch Collective`
- keep the status bar, collapsible right rail, and view intro pattern
- port the calm tone, not the exact copy
- keep data-first navigation
- make proof pages the primary public object
- keep trade flows visually secondary and external
