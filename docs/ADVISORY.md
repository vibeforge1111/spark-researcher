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
spark-researcher advisory providers
spark-researcher advisory build --task "draft a content belief packet" --model claude
spark-researcher advisory execute --task "draft a content belief packet" --model claude --dry-run --command "my-wrapper {system_prompt_path} {user_prompt_path} {response_path}"
spark-researcher advisory log --task "draft a content belief packet" --model claude --status ok --packet-id belief-run-...
spark-researcher advisory review
spark-researcher optimizer status
spark-researcher optimizer export-advisory-dataset
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

## Provider Execution

Spark can execute advisory-backed model calls through lightweight command templates.

Set one of these environment variables:

- `SPARK_RESEARCHER_ADAPTER_CLAUDE_COMMAND`
- `SPARK_RESEARCHER_ADAPTER_CODEX_COMMAND`
- `SPARK_RESEARCHER_ADAPTER_OPENCLAW_COMMAND`
- `SPARK_RESEARCHER_ADAPTER_GENERIC_COMMAND`

Supported placeholders:

- `{system_prompt_path}`
- `{user_prompt_path}`
- `{request_path}`
- `{response_path}`

Windows Claude Opus example:

```powershell
$env:SPARK_RESEARCHER_ADAPTER_CLAUDE_COMMAND='powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\USER\Desktop\spark-researcher\scripts\claude_frontier_wrapper.ps1 {system_prompt_path} {user_prompt_path} {response_path} -Model opus'
```

This keeps provider execution outside the core logic while still letting Spark prepare the right request shape for each model family.
