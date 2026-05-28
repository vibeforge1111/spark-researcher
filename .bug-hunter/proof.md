# Bug Hunter Proof

## Before

```python
path = _working_path(runtime_root)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

## After

```python
path = _working_path(runtime_root)
with locked_file(path):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

## Why

bare path.write_text() has no lock. When research.py and runner.py both call write_working_memory concurrently, one write silently overwrites the other with no error. locked_file is the same spinlock used by append_jsonl in runner.py for all ledger writes.

## Evidence

| Field | Value |
|---|---|
| PR | [38](https://github.com/vibeforge1111/spark-researcher/pull/38) |
| Repo | vibeforge1111/spark-researcher |
| Severity | medium |
| Files changed | `src/spark_researcher/memory.py` |
| Branch | `fix/write-working-memory-lock` |
| Validated | pass (0 errors, 0 warnings) |