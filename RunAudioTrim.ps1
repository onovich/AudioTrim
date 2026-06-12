param(
    [switch]$DryRun,
    [switch]$SelfTest
)

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$ToolScript = Join-Path $RepoRoot "audio_trim.py"

if (-not (Test-Path -LiteralPath $ToolScript)) {
    throw "AudioTrim script was not found: $ToolScript"
}

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) {
    $PythonCommand = Get-Command py -ErrorAction SilentlyContinue
}

if ($null -eq $PythonCommand) {
    throw "Python was not found on PATH."
}

$PythonExe = $PythonCommand.Source
$Arguments = @($ToolScript)

if ($SelfTest) {
    $Arguments += "--self-test"
} else {
    $Arguments += "--gui"
}

if ($DryRun) {
    Write-Host "AudioTrim root: $RepoRoot"
    Write-Host "Python: $PythonExe"
    Write-Host "Command: $PythonExe $($Arguments -join ' ')"
    exit 0
}

& $PythonExe @Arguments
exit $LASTEXITCODE
