param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $LinterArgs
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Linter = Join-Path $PSScriptRoot "cpp_style_lint.py"

$Python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $Python) {
    $Python = Get-Command py -ErrorAction SilentlyContinue
}

if ($null -eq $Python) {
    Write-Error "Python was not found. Install Python or add it to PATH to run the C++ style linter."
}

Push-Location $ProjectRoot
try {
    & $Python.Source $Linter @LinterArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
