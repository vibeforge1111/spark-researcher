param(
  [Parameter(Mandatory = $true)][string]$SystemPromptPath,
  [Parameter(Mandatory = $true)][string]$UserPromptPath,
  [Parameter(Mandatory = $true)][string]$ResponsePath,
  [string]$WorkingDirectory = ".",
  [int]$TimeoutSeconds = 45
)

$systemPrompt = [System.IO.File]::ReadAllText($SystemPromptPath, [System.Text.Encoding]::UTF8)
$userPrompt = [System.IO.File]::ReadAllText($UserPromptPath, [System.Text.Encoding]::UTF8)
$combinedPrompt = (($systemPrompt.Trim()) + "`n`n" + ($userPrompt.Trim())).Trim()
$messagePath = [System.IO.Path]::GetTempFileName()
$promptPath = [System.IO.Path]::GetTempFileName()
$stdoutPath = [System.IO.Path]::GetTempFileName()
$stderrPath = [System.IO.Path]::GetTempFileName()

try {
  [System.IO.File]::WriteAllText($promptPath, $combinedPrompt, [System.Text.Encoding]::UTF8)
  $cmdLine = 'type "{0}" | "C:\Users\USER\.npm-global\codex.cmd" exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check --ephemeral --color never -C "{1}" -o "{2}" - > "{3}" 2> "{4}"' -f $promptPath, $WorkingDirectory, $messagePath, $stdoutPath, $stderrPath
  $process = Start-Process -FilePath "cmd.exe" -ArgumentList "/d", "/c", $cmdLine -PassThru -WindowStyle Hidden
  if (-not ($process.WaitForExit($TimeoutSeconds * 1000))) {
    taskkill /pid $process.Id /t /f *> $null
    throw "Codex wrapper timed out after $TimeoutSeconds seconds."
  }
  if ($process.ExitCode -ne 0) {
    $stderrText = ""
    if (Test-Path $stderrPath) {
      $stderrText = [System.IO.File]::ReadAllText($stderrPath, [System.Text.Encoding]::UTF8).Trim()
    }
    throw "Codex wrapper failed with exit code $($process.ExitCode). $stderrText".Trim()
  }

  $responseText = ""
  if (Test-Path $messagePath) {
    $responseText = [System.IO.File]::ReadAllText($messagePath, [System.Text.Encoding]::UTF8)
    $responseText = $responseText.Trim()
  }
  $payload = @{ raw_response = $responseText }
  $payload | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $ResponsePath
}
finally {
  foreach ($path in @($messagePath, $promptPath, $stdoutPath, $stderrPath)) {
    if (Test-Path $path) {
      Remove-Item $path -Force -ErrorAction SilentlyContinue
    }
  }
}
