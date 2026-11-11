# Nightly end-to-end testnet runner (Sprint 1 task B2)
# Usage: powershell -File scripts\nightly-e2e.ps1 [--mode testnet|dry-run] [-y]
param (
    [string]$Mode = "testnet",
    [switch]$Yes,
    [switch]$Json,
    [string]$BenignScenario = "benign-hosting",
    [string]$AttackScenario = "attack-morse-lookalike",
    [string]$Llm = "scripted"
)

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location (Join-Path $RepoRoot "agent")

$ArgsList = @("run", "firewall-nightly-e2e", "--mode", $Mode, "--benign-scenario", $BenignScenario, "--attack-scenario", $AttackScenario, "--llm", $Llm)
if ($Yes) { $ArgsList += "-y" }
if ($Json) { $ArgsList += "--json" }

& uv @ArgsList
exit $LASTEXITCODE
