param(
  [string]$Rom = "",
  [ValidateSet("SDL2", "OpenGL", "GLFW", "null")]
  [string]$Window = "SDL2",
  [ValidateSet("manual", "wander", "right_scout", "menu_mash", "edge_scan", "start_then_wander")]
  [string]$Agent = "",
  [string]$SpeedrunTask = "",
  [string]$TaskId = "intro_boot",
  [string]$BenchmarkProfile = "",
  [int]$Steps = 0
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$args = @()
if ($Rom) { $args += @("--rom", $Rom) }
$args += @("--window", $Window)
if ($Agent) { $args += @("--agent", $Agent) }
if ($SpeedrunTask) {
  $args += @("--speedrun-task", $SpeedrunTask)
} else {
  $args += @("--task-id", $TaskId)
}
if ($BenchmarkProfile) { $args += @("--benchmark-profile", $BenchmarkProfile) }
if ($Steps -gt 0) { $args += @("--steps", "$Steps") }

python -m domain_chip_pokemon_player.play @args
