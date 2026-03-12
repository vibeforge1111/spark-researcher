# Obsidian

The Obsidian vault is the watchtower, not the source of truth.

## Generated Notes

- `Home.md`
- `00-Intent/System Intent.md`
- `05-Runtime/Run Ledger.md`
- `05-Runtime/Trainer State.md`
- `05-Runtime/Memory Index.md`
- `05-Runtime/Working Memory.md`
- `05-Runtime/Episode Memory.md`
- `05-Runtime/Outcome State.md`
- `05-Runtime/Research Signals.md`
- `05-Runtime/Self Edit Queue.md`
- `06-References/*.md`

## Rule

Canonical docs stay in `docs/`. The vault is rebuilt from those docs and runtime artifacts so operators can browse the current system state quickly.

The vault reflects the tiered memory model:

- `05-Runtime/Working Memory.md` is the current state snapshot
- `05-Runtime/Memory Index.md` now shows memory-tier counts as well as kind counts
- domain pages should treat grounded doctrine and grounded boundaries as the operator surface
- exploratory frontier pages remain visible, but they are not benchmark-grounded truth

```mermaid
flowchart LR
    A["Ledger + chip result"] --> B["memory sync"]
    B --> C["Working Memory"]
    B --> D["Memory Index"]
    B --> E["Chip packet docs"]
    E --> F["Grounded doctrine pages"]
    E --> G["Exploratory frontier pages"]
    C --> H["Obsidian runtime pages"]
    D --> H
    F --> H
    G --> H
```

`05-Runtime/Research Signals.md` now includes bounded research provenance when available, including note ids, source domains, and URLs surfaced from the retry path. It also shows verifier draft-selection events and advisory packet-selection events so you can see which packet ids were active, which candidate won, and what issue pushed revision or caution.

`Home.md` also summarizes belief quality with durable/provisional counts and active contradiction count so memory health is visible at a glance.

`Home.md` now also shows the current queued frontier count, derived from `artifacts/frontier/queue.json`, so operators can distinguish the stable project spec from pending generated exploration.

Packet semantics shown in the reference docs also carry into the vault because `docs/*.md` is copied into `06-References/`. That includes the current `research_outcome` contract: these entries are bounded evidence-only packets from the `research` command, not promoted doctrine or belief packets, and they should rank below doctrine or belief when both match.

`05-Runtime/Memory Index.md` will also show `research_outcome` in the kind counts once those packets exist locally. The runtime vault does not currently render a separate packet-schema page for those fields; the field contract lives in the copied reference docs and the packet-search surface.

When `research_outcome` packets are present, the field contract surfaced through the vault is:

- `kind`
  - `research_outcome`
- `claim`
  - bounded statement of the current research-suite result
- `mechanism`
  - explicit note that the row comes from the research ledger as evidence-only support
- `boundary`
  - explicit limit that the row is a single recorded research outcome and not doctrine
