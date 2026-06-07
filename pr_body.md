## Summary

Three `subprocess.run()` calls in `self_edit.py` have no `timeout` parameter:

1. `run_git_status()` — `git status` can hang on NFS/network mounts
2. `_git()` — git operations can hang on large repos or network issues
3. `propose()` — runs **arbitrary LLM-generated commands** with no timeout

`propose()` is the highest risk: if the LLM generates a command that blocks (infinite loop, waiting for stdin, network hang), the entire process hangs forever.

## Fix

```python
# run_git_status: timeout=30
# _git: timeout=60
# propose: timeout=300 (5 minutes for arbitrary commands)
```

## CWE

CWE-400: Uncontrolled Resource Consumption

<details>

```json
{"packet_version":"spark-compete-hotfix-v1","team_details":{"team_name":"Bug Hunters","team_lead_telegram":"@drophub_sir","members":[{"name":"Sampson","telegram":"@drophub_sir","github":"esc1200"},{"name":"ZakJan","telegram":"@Daraking2612","github":"ZakJan777"},{"name":"Saleem","telegram":"@Saleemkhan114","github":"dara917"}]},"issue":{"type":"bug","severity":"HIGH","cwe":"CWE-400","title":"subprocess.run without timeout in self_edit.propose runs arbitrary commands indefinitely","affected_file":"src/spark_researcher/self_edit.py","affected_line_or_symbol":"336","owner_surface":"researcher","evidence_types":["reproduction_steps","test_patch"],"reproduction_steps":"1. LLM generates a command that blocks (e.g., 'cat' with no input) 2. propose() runs it via subprocess.run with no timeout 3. Process hangs forever","smoke_test":"N/A — timeout parameter addition"},"pr":{"url":"PLACEHOLDER","body_must_include":"CWE-400"}}
```

</details>
