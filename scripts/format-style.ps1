param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $FormatterArgs
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Formatter = Join-Path $PSScriptRoot "format-style.py"

$Python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $Python) {
    $Python = Get-Command py -ErrorAction SilentlyContinue
}

if ($null -eq $Python) {
    Write-Error "Python was not found. Install Python or add it to PATH to run the C++ style formatter."
}

Push-Location $ProjectRoot
try {
    & $Python.Source $Formatter --quiet @FormatterArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
