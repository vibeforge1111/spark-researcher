# Proof Kit — batched missing-timeout fixes (spark-researcher)

This branch consolidates three `missing-timeout` findings into a single PR.
Each commit applies one minimal fix; this proof summarizes all three.

## Why batch

All three findings are the same class — `subprocess.run(...)` called
without `timeout=`, so a stalled peer hangs the caller indefinitely. The
fixes follow the same pattern in three different files. One PR is easier
to review than three identical small ones and lands the entire class fix
atomically.

## Findings included

### #3 · MEDIUM · missing-timeout
- File: `src/spark_researcher/chips.py:428`
- Fix commit: see `add timeout to chip hook subprocess call`
- Behavior: chip hook now fails fast on a wedged peer with `TimeoutExpired`
  instead of blocking the runner queue forever.

### #4 · MEDIUM · missing-timeout
- File: `src/spark_researcher/runner.py:148`
- Fix commit: see `add timeout to run_process subprocess call`
- Behavior: runner's child-process invocation now caps wall time; a hung
  child surfaces as a runner-level error.

### #5 · MEDIUM · missing-timeout
- File: `src/spark_researcher/trainers.py:81`
- Fix commit: see `add timeout to trainer subprocess.run`
- Behavior: trainer subprocess fails fast on hang, so the training queue
  can move past a wedged worker instead of stalling.

## How to verify

For each file, exercise the call against an artificially-sleepy child
process (e.g. inject `time.sleep(timeout_value + 5)` in a fixture). Before
the fix the call hangs forever; after the fix it raises `TimeoutExpired`
within the configured window.
