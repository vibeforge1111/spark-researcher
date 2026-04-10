function Import-DspyEnvFile {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    Get-Content $Path | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') {
            return
        }
        $name, $value = $_ -split '=', 2
        Set-Item -Path "Env:$name" -Value $value
    }
}

$previousOpenAiKey = $env:OPENAI_API_KEY
$previousOpenAiBaseUrl = $env:OPENAI_BASE_URL
$hadOpenAiKey = $null -ne (Get-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue)
$hadOpenAiBaseUrl = $null -ne (Get-Item Env:OPENAI_BASE_URL -ErrorAction SilentlyContinue)

try {
    Import-DspyEnvFile (Join-Path $PSScriptRoot ".env.dspy.local")

    if ([string]::IsNullOrWhiteSpace($env:MINIMAX_API_KEY)) {
        throw "MINIMAX_API_KEY is not set in .env.dspy.local."
    }

    if ([string]::IsNullOrWhiteSpace($env:MINIMAX_BASE_URL)) {
        $env:MINIMAX_BASE_URL = "https://api.minimax.io/v1"
    }

    $env:OPENAI_API_KEY = $env:MINIMAX_API_KEY
    $env:OPENAI_BASE_URL = $env:MINIMAX_BASE_URL
    if ([string]::IsNullOrWhiteSpace($env:SPARK_STARTUP_DSPY_MODEL)) {
        $env:SPARK_STARTUP_DSPY_MODEL = "openai/MiniMax-M2.5"
    }
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
}
finally {
    if ($hadOpenAiKey) {
        $env:OPENAI_API_KEY = $previousOpenAiKey
    } else {
        Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
    }
    if ($hadOpenAiBaseUrl) {
        $env:OPENAI_BASE_URL = $previousOpenAiBaseUrl
    } else {
        Remove-Item Env:OPENAI_BASE_URL -ErrorAction SilentlyContinue
    }
}
