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
spark-researcher packets status
spark-researcher packets search "proof quality"
spark-researcher advisory adapters
spark-researcher advisory providers
spark-researcher advisory build --task "draft a content belief packet" --model claude
spark-researcher advisory execute --task "draft a content belief packet" --model claude --dry-run --command "my-wrapper {system_prompt_path} {user_prompt_path} {response_path}"
spark-researcher advisory execute --task "draft a content belief packet" --model claude
spark-researcher advisory log --task "draft a content belief packet" --model claude --status ok --packet-id belief-run-...
spark-researcher advisory review
spark-researcher optimizer status
spark-researcher optimizer export-advisory-dataset
```

## Verifier Loop

`advisory execute` now uses a bounded verifier loop by default:

1. draft an answer
2. critique that draft against the current packets, boundaries, evidence status, and top surprise-priority failure surfaces
3. either approve, revise once, return `needs_verification`, or escalate to `research_needed` when the task is time-sensitive and the mission allows fresh web research
4. if `research_needed` is returned, Spark now runs one bounded web-notes pass, saves the dated notes as an artifact, and feeds those notes back through the same verifier loop once

If the advisory is already marked `under_supported`, Spark returns `needs_verification` before making a model call.

When the verifier spots one of the active failure surfaces in a draft, it now names that implicated surface in the critique and trace so the operator can see which failure class the answer was trying to avoid.

If the verifier concludes that the missing support is likely fresh or time-sensitive and the current intent includes the `web` resource, Spark now returns a `research_needed` packet with a suggested query and research targets instead of a generic `needs_verification` stop.

That research retry is deliberately bounded:

- one query
- one lightweight web-notes pass
- one follow-up verifier run

If the follow-up still lacks support, Spark stops and returns the remaining uncertainty instead of looping.

When that retry succeeds, Spark now returns a small `citations` list derived from the bounded research artifact so the operator can see which dated notes were in play.

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
