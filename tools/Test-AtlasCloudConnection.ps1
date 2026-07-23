[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "AtlasCloud.Common.ps1")

$apiKey = $null
try {
    $projectRoot = Split-Path -Parent $PSScriptRoot
    $null = Initialize-AtlasCloudWorkspace -ProjectRoot $projectRoot
    $apiKey = Get-AtlasCloudApiKey -ProjectRoot $projectRoot
    $headers = @{ Authorization = "Bearer $apiKey" }
    $response = Invoke-RestMethod -Method Get -Uri "https://api.atlascloud.ai/api/v1/models" -Headers $headers -TimeoutSec 30

    $models = @($response.data)
    if ($models.Count -eq 0) {
        throw "Atlas Cloud returned no models; the API response format was unexpected."
    }

    $modelIds = @($models | ForEach-Object { $_.model })
    $requiredModels = @(
        "black-forest-labs/flux-2-pro/text-to-image",
        "black-forest-labs/flux-2-flex/edit"
    )

    Write-Host "Atlas Cloud connection succeeded. Available models: $($models.Count)."
    foreach ($modelId in $requiredModels) {
        if ($modelIds -contains $modelId) {
            Write-Host "  OK  $modelId"
        }
        else {
            Write-Warning "  Not listed for this account: $modelId"
        }
    }

    Write-Host "No image or video generation was submitted."
}
catch {
    $statusCode = $null
    $responseProperty = $_.Exception.PSObject.Properties["Response"]
    if ($null -ne $responseProperty -and $null -ne $responseProperty.Value) {
        $statusCode = [int]$responseProperty.Value.StatusCode
    }

    if ($statusCode -in 401, 403) {
        Write-Host "Atlas Cloud rejected the API key (HTTP $statusCode). Run SET_ATLAS_CLOUD_API_KEY.bat again or check the key in Atlas Cloud." -ForegroundColor Red
    }
    else {
        Write-Host "Atlas Cloud connection test failed: $($_.Exception.Message)" -ForegroundColor Red
    }
    exit 1
}
finally {
    Remove-Item Variable:apiKey -ErrorAction SilentlyContinue
    Remove-Item Variable:headers -ErrorAction SilentlyContinue
}
