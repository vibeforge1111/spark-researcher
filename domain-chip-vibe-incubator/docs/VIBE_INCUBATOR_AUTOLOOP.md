# Vibe Vibe Autoloop

This chip now has two bounded loop surfaces.

## Research Loop

Use `research` when the incubator is deciding what venture play to run next.

It answers:

- which startup motion deserves attention
- what the current bottleneck is
- which next probe should enter the frontier queue

Run it with:

```powershell
$env:PYTHONPATH = "src"
python -m spark_researcher.cli autoloop --config domain-chip-vibe-incubator/spark-researcher.project.json --command research --rounds 2 --suggest-limit 3
```

## Ops Loop

Use `ops` when the incubator needs to run itself as an explicit control plane.

Each `ops` tick:

- bootstraps or refreshes `artifacts/incubator_os/state.json`
- scores the current operating loop
- writes `latest_tick.json`
- writes `queue_snapshot.json`
- writes `office_hours_packets.json`
- writes `decision_packets.json`

Run it with:

```powershell
$env:PYTHONPATH = "src"
python -m spark_researcher.cli run --config domain-chip-vibe-incubator/spark-researcher.project.json --command ops --candidate-id ops-tight-three-lane
python -m spark_researcher.cli autoloop --config domain-chip-vibe-incubator/spark-researcher.project.json --command ops --rounds 2 --suggest-limit 3
```

## Why Two Loops

Keep venture selection and incubator operations separate.

- `research` decides what to build or validate
- `ops` decides whether the incubator itself is focused, fresh, trustworthy, and learnable

If those are mixed together, the system will confuse exciting venture ideas with healthy incubator operations.

## Boundary

This is still a bounded autoloop, not a hidden daemon.

- Spark owns loop execution
- queue state stays in runtime artifacts
- human gates still own admissions, legal, equity, trust escalation, and reputation-sensitive investor moves
