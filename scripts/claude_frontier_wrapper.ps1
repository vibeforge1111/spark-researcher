param(
  [Parameter(Mandatory = $true)][string]$SystemPromptPath,
  [Parameter(Mandatory = $true)][string]$UserPromptPath,
  [Parameter(Mandatory = $true)][string]$ResponsePath,
  [string]$Model = "opus"
)

$systemPrompt = Get-Content -Raw -Encoding UTF8 $SystemPromptPath
$userPrompt = Get-Content -Raw -Encoding UTF8 $UserPromptPath
$combinedPrompt = (($systemPrompt.Trim()) + "`n`n" + ($userPrompt.Trim())).Trim()
$responseText = & claude -p --output-format text --model $Model $combinedPrompt
$payload = @{ raw_response = ($responseText | Out-String).Trim() }
$payload | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $ResponsePath
