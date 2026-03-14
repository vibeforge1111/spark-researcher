$env:OPENAI_API_KEY = "sk-cp-2ts9V4kwwA-eevaYyOuMExLe6oubukS3HntHscft9d7dh1HC7trEYfnN9P5hHjYnYzSMinlGqKOOv0pNrkuE8BiNx8jw6fv1WyouvrRmgloNuQy9bo4el1o"
$env:OPENAI_BASE_URL = "https://api.minimax.io/v1"
$env:SPARK_STARTUP_DSPY_MODEL = "openai/MiniMax-M2.5"
$env:SPARK_STARTUP_BENCH_ROOT = "C:\Users\USER\Desktop\startup-bench"
$env:SPARK_STARTUP_YC_LOCAL_FRONTIER = "1"
$env:SPARK_STARTUP_DSPY_SLOT1_AUTORUN = "1"
# Backlog limit now defaults to 5 in code (was 2). No override needed.
$env:SPARK_STARTUP_DOCTRINE_ONLY = "1"
$env:PYTHONPATH = "C:\Users\USER\Desktop\spark-researcher\src;C:\Users\USER\Desktop\domain-chip-startup-yc\src"
$env:PYTHONUNBUFFERED = "1"

Write-Host "=== Startup Autoloop Environment ==="
Write-Host "DSPY_MODEL: $env:SPARK_STARTUP_DSPY_MODEL"
Write-Host "SLOT1_AUTORUN: $env:SPARK_STARTUP_DSPY_SLOT1_AUTORUN"
Write-Host "SLOT1_BACKLOG_LIMIT: 5 (code default)"
Write-Host "DOCTRINE_ONLY: $env:SPARK_STARTUP_DOCTRINE_ONLY"
Write-Host "LOCAL_FRONTIER: $env:SPARK_STARTUP_YC_LOCAL_FRONTIER"
Write-Host "====================================="

Set-Location "C:\Users\USER\Desktop\domain-chip-startup-yc"
& python -u -m spark_researcher.cli autoloop --command research --continuous --rounds 6 --suggest-limit 3 --pause-seconds 300
