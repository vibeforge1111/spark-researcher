# Advisory

Spark Researcher uses one lightweight intelligence path:

`task -> advisory -> packets -> adapter -> model -> outcome`

## What Each Layer Does

- `packets`
  - reusable beliefs, failures, rules, and domain packets exported into local memory
- `advisory`
  - selects the smallest useful packet set for a task
- `adapter`
  - injects the advisory into a specific model surface
- `outcome`
  - logs whether the advice helped

## Commands

```powershell
spark-researcher packets status
spark-researcher packets search "proof quality"
spark-researcher advisory adapters
spark-researcher advisory build --task "draft a content belief packet" --model claude
spark-researcher advisory log --task "draft a content belief packet" --model claude --status ok --packet-id belief-run-...
spark-researcher optimizer status
```

## Adapter Policy

- `claude`
  - uses a native prehook-style request shape
- `codex`
  - uses a wrapper preamble because Spark cannot rely on a native pretool hook
- `openclaw`
  - currently uses the same wrapper pattern as generic adapters
- `generic`
  - fallback adapter for any other model surface

## DSPy Policy

DSPy is optional.

Spark should run perfectly without it.

Only use DSPy to optimize measurable subroutines such as:

- packet ranking
- advisory compression
- belief extraction
- contradiction extraction

Do not make DSPy the core runtime.
