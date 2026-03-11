param(
  [Parameter(Mandatory = $true)][string]$SystemPromptPath,
  [Parameter(Mandatory = $true)][string]$UserPromptPath,
  [Parameter(Mandatory = $true)][string]$ResponsePath,
  [string]$Model = "opus",
  [string]$DisallowedTools = "",
  [switch]$StrictNoMcp
)

$systemPrompt = Get-Content -Raw -Encoding UTF8 $SystemPromptPath
$userPrompt = Get-Content -Raw -Encoding UTF8 $UserPromptPath
$combinedPrompt = (($systemPrompt.Trim()) + "`n`n" + ($userPrompt.Trim())).Trim()
$claudeArgs = @("-p", "--output-format", "text", "--model", $Model)
if ($StrictNoMcp) {
  $mcpConfigPath = Join-Path $env:TEMP "claude-empty-mcp.json"
  [System.IO.File]::WriteAllText($mcpConfigPath, '{"mcpServers":{}}', (New-Object System.Text.UTF8Encoding $false))
  $claudeArgs += @("--strict-mcp-config", "--mcp-config", $mcpConfigPath)
}
if ($DisallowedTools.Trim()) {
  $claudeArgs += "--disallowedTools=$DisallowedTools"
}
$claudeArgs += $combinedPrompt
$responseText = & claude @claudeArgs
$payload = @{ raw_response = ($responseText | Out-String).Trim() }
$payload | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $ResponsePath
