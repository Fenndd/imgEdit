[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "AtlasCloud.Common.ps1")

try {
    $projectRoot = Split-Path -Parent $PSScriptRoot
    $secretPath = Get-AtlasCloudSecretPath -ProjectRoot $projectRoot

    if (-not (Test-Path -LiteralPath $secretPath -PathType Leaf)) {
        Write-Host "No Atlas Cloud API key is stored locally."
        exit 0
    }

    Remove-Item -LiteralPath $secretPath -Force
    Write-Host "The locally encrypted Atlas Cloud API key was removed."
}
catch {
    Write-Host "Could not remove the Atlas Cloud API key: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
