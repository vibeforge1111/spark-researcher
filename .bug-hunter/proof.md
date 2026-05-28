# Bug Hunter Proof

## Before

```python
def search_memory(repo_root, runtime_root, query, *, limit=5, backend="local",
                  goal="minimize", config_path=None):
    sync_memory(repo_root, runtime_root, goal=goal, config_path=config_path)
    docs_root = _documents_root(runtime_root)
    ...
```

## After

```python
def search_memory(repo_root, runtime_root, query, *, limit=5, backend="local",
                  goal="minimize", config_path=None, force_sync=False):
    if force_sync or not _manifest_path(runtime_root).exists():
        sync_memory(repo_root, runtime_root, goal=goal, config_path=config_path)
    docs_root = _documents_root(runtime_root)
    ...
```

## Why

Every call to `search_memory` triggered `sync_memory`, which deletes all memory documents and rebuilds them from scratch. Under concurrent load, one sync deletes documents mid-read in the other call, producing silent data loss. In serial autoresearch, high-frequency searches caused O(N*queries) full rebuilds where one sync per session-boundary would suffice.

The fix makes sync lazy: it only runs on the first call per session (when the manifest is absent) or when `force_sync=True` is explicitly passed. `_manifest_path` is the existing sentinel already used by `_local_manifest` for the same purpose.

## Evidence

| Field | Value |
|---|---|
| PR | [43](https://github.com/vibeforge1111/spark-researcher/pull/43) |
| Repo | vibeforge1111/spark-researcher |
| Severity | high |
| Files changed | `src/spark_researcher/memory.py` |
| Branch | `fix/search-memory-lazy-sync` |
| Validated | pass (0 errors, 0 warnings) |