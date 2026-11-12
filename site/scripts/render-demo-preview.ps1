param(
    [string]$Browser = "${env:ProgramFiles(x86)}/Microsoft/Edge/Application/msedge.exe"
)
$ErrorActionPreference = 'Stop'
$assetDir = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../public/demo'))
$sourcePath = Join-Path $assetDir 'numbers-slide.html'
$imagePath = Join-Path $assetDir 'numbers-slide.png'
if (-not (Test-Path -LiteralPath $sourcePath)) { throw 'Generate the numbers slide first.' }
if (-not (Test-Path -LiteralPath $Browser)) { throw 'Pass -Browser with the path to an installed Chromium browser.' }
# A separate temporary profile avoids changing the user's browser session.
$previewProfile = Join-Path ([IO.Path]::GetTempPath()) ('backlogs-e4-preview-' + [Guid]::NewGuid())
$sourceUri = [Uri]::new($sourcePath).AbsoluteUri
$arguments = @('--headless=new', '--disable-gpu', '--no-first-run', '--disable-extensions',
    "--user-data-dir=$previewProfile", '--force-device-scale-factor=1', '--hide-scrollbars',
    '--window-size=1920,1080', '--virtual-time-budget=2500', "--screenshot=$imagePath", $sourceUri)
$startedAt = [DateTime]::UtcNow
& $Browser @arguments | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Browser preview failed: exit $LASTEXITCODE" }
# Some Chromium launchers return before their screenshot process exits.
$deadline = [DateTime]::UtcNow.AddSeconds(20)
while ([DateTime]::UtcNow -lt $deadline) {
    if ((Test-Path -LiteralPath $imagePath) -and (Get-Item -LiteralPath $imagePath).LastWriteTimeUtc -ge $startedAt) { break }
    Start-Sleep -Milliseconds 200
}
if (-not (Test-Path -LiteralPath $imagePath) -or (Get-Item -LiteralPath $imagePath).LastWriteTimeUtc -lt $startedAt) { throw 'Browser did not create a new PNG preview.' }
Write-Output $imagePath
