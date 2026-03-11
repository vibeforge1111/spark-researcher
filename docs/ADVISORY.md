# Advisory

Spark Researcher uses one lightweight intelligence path:

`task -> advisory -> packets -> adapter -> model -> outcome`

## What Each Layer Does

- `packets`
  - reusable beliefs, failures, rules, and domain packets exported into local memory
- `advisory`
  - selects the smallest useful packet set for a task and marks the evidence status for the task
- `adapter`
  - injects the advisory into a specific model surface
- `outcome`
  - logs whether the advice helped

## Evidence Status

Advisory now includes a small epistemic layer:

- `grounded`
  - packets and boundaries are present, so bounded claims are reasonable
- `partial`
  - some evidence exists, but the answer should surface uncertainty and often ask clarifying questions
- `under_supported`
  - the task lacks enough local evidence, so the system should ask questions, retrieve more, or research before making strong claims

This is meant to reduce confident overreach without growing a heavy agent runtime.

## Failure Priorities

Advisory also carries the current surprise-priority view from the failure registry.

This is a lightweight way to bias attention toward:

- recent failures
- repeated failures
- failures that show up across more than one novelty key

Use `spark-researcher failures --limit 10` to inspect the current ranked failure surfaces directly.

## Commands

```powershell
spark-researcher advisory adapters
spark-researcher advisory build --task "draft a content belief packet" --model claude
spark-researcher advisory execute --task "draft a content belief packet" --model claude
spark-researcher advisory execute --task "draft a content belief packet" --model claude --dry-run --command "my-wrapper {system_prompt_path} {user_prompt_path} {response_path}"
spark-researcher advisory providers
```

## Verifier Loop

`advisory execute` now uses a bounded verifier loop by default:

1. draft an answer
2. critique it against packets, boundaries, evidence status, failure surfaces, and any available research-note ids
3. approve, revise once, return `needs_verification`, or escalate to `research_needed` for time-sensitive web-backed tasks
4. if `research_needed` is returned, run one bounded web-notes pass and retry once with dated notes

That research retry is deliberately bounded:

- one query
- one lightweight web-notes pass
- one follow-up verifier run

If the follow-up still lacks support, Spark stops and returns the remaining uncertainty instead of looping.

Research-backed follow-ups return compact `citations`. The verifier expects those note ids to be used and prefers the ids that best match the answer's concrete claims. Missing citations or clearly weaker note choices are downgraded to `revise`.

Use `--no-verify` to bypass this loop when you explicitly want the raw single-pass model output.

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
