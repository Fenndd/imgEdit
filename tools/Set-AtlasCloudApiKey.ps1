[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "AtlasCloud.Common.ps1")

try {
    $projectRoot = Split-Path -Parent $PSScriptRoot
    $atlasHome = Get-AtlasCloudHome -ProjectRoot $projectRoot
    $secretDirectory = Join-Path $atlasHome "secrets"
    $secretPath = Get-AtlasCloudSecretPath -ProjectRoot $projectRoot

    New-Item -ItemType Directory -Force -Path $secretDirectory | Out-Null
    $secureKey = Read-Host "Paste Atlas Cloud API key" -AsSecureString
    if ($secureKey.Length -eq 0) {
        throw "No API key was entered."
    }

    $protectedValue = ConvertFrom-SecureString -SecureString $secureKey
    [System.IO.File]::WriteAllText($secretPath, $protectedValue, [System.Text.UTF8Encoding]::new($false))
    Write-Host "Atlas Cloud API key was encrypted for this Windows account."
}
catch {
    Write-Host "Could not store the Atlas Cloud API key: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
