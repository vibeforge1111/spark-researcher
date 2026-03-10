# Intent

Intent gives a chip or project a persistent mission instead of a generic loop.

## What Intent Controls

- goal: what the system is trying to become good at
- outcome: what practical result that should unlock
- success criteria: what counts as progress
- frontier mode: `bounded`, `relaxed`, or `open`
- resources: which surfaces the loop should actively use

Current resource labels:

- `packets`
- `memory`
- `web`
- `ruvector`
- `dspy`
- `mcp`
- `collective`

## Commands

```powershell
spark-researcher intent show
spark-researcher intent set --goal "Build the strongest startup-understanding agent" --outcome "Create agentic startups from first-principles doctrine" --success-criterion "Find reusable startup doctrines" --success-criterion "Map failure boundaries" --resource web --resource memory --resource ruvector --resource dspy --frontier-mode open
spark-researcher intent clear
```

## Runtime Effect

- advisory briefs include the active mission
- frontier prompts optimize for that mission
- chip `evaluate` and `suggest` hooks receive the intent payload
- memory and packet search can be pulled into frontier prompting
- optional RuVector and DSPy status are surfaced when the intent enables them

## Boundary

Intent makes exploration more directed, not magically omnipotent.

- Spark still uses the chip evaluator as the source of truth
- RuVector is only used when configured and available
- DSPy remains optional
- `mcp` in resources means "allowed if the provider wrapper supports it", not automatic tool installation
