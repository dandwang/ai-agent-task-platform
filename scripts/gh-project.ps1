param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$GhArguments
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$env:GH_CONFIG_DIR = Join-Path $projectRoot ".local\gh"
New-Item -ItemType Directory -Force -Path $env:GH_CONFIG_DIR | Out-Null

$ghCommand = Get-Command gh -ErrorAction Stop
& $ghCommand.Source @GhArguments
exit $LASTEXITCODE
