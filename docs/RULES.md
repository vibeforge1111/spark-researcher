# Rules

## Lightweight Rules

- Keep the fixed evaluator outside the mutable loop.
- Keep mutations file-local and reviewable.
- Keep the ledger raw and append-only.
- Keep narrative in docs, not in the source-of-truth record.

## Recursive Rules

- One mutation, one hypothesis.
- Reject complexity growth without measured gain.
- Switch axes after plateaus instead of endlessly retuning the same knob.
- Treat self-edit as proposal generation, not autonomous authority.

## Safety Rules

- Self-edit proposals run in a copied workspace.
- Apply requires an explicit owner command.
- Mutable targets must be declared in config.
- Blocked command fragments are rejected before self-edit execution.

