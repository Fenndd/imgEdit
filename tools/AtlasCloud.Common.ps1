Set-StrictMode -Version Latest

function Get-AtlasCloudHome {
    param(
        [Parameter(Mandatory)]
        [string]$ProjectRoot
    )

    return Join-Path $ProjectRoot "AtlasCloud"
}

function Get-AtlasCloudSecretPath {
    param(
        [Parameter(Mandatory)]
        [string]$ProjectRoot
    )

    return Join-Path (Get-AtlasCloudHome -ProjectRoot $ProjectRoot) "secrets\atlascloud_api_key.dpapi"
}

function Initialize-AtlasCloudWorkspace {
    param(
        [Parameter(Mandatory)]
        [string]$ProjectRoot
    )

    $atlasHome = Get-AtlasCloudHome -ProjectRoot $ProjectRoot
    $directories = @(
        $atlasHome,
        (Join-Path $atlasHome "custom_nodes"),
        (Join-Path $atlasHome "input"),
        (Join-Path $atlasHome "output"),
        (Join-Path $atlasHome "temp"),
        (Join-Path $atlasHome "user"),
        (Join-Path $atlasHome "models"),
        (Join-Path $atlasHome "logs"),
        (Join-Path $atlasHome "secrets")
    )

    foreach ($directory in $directories) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }

    $nodeInit = Join-Path $atlasHome "custom_nodes\atlascloud_comfyui\__init__.py"
    if (-not (Test-Path -LiteralPath $nodeInit -PathType Leaf)) {
        throw "Atlas Cloud nodes were not found at $nodeInit. Restore the pinned package before starting Atlas Cloud."
    }

    $templateDirectory = Join-Path $atlasHome "workflows"
    $workflowDirectory = Join-Path $atlasHome "user\default\workflows\ATLAS_CLOUD"
    if (-not (Test-Path -LiteralPath $templateDirectory -PathType Container)) {
        throw "Atlas Cloud workflow templates were not found at $templateDirectory."
    }

    New-Item -ItemType Directory -Force -Path $workflowDirectory | Out-Null
    Get-ChildItem -LiteralPath $templateDirectory -Filter "*.json" -File | ForEach-Object {
        $destination = Join-Path $workflowDirectory $_.Name
        if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) {
            Copy-Item -LiteralPath $_.FullName -Destination $destination
        }
    }

    return $atlasHome
}

function Get-AtlasCloudApiKey {
    param(
        [Parameter(Mandatory)]
        [string]$ProjectRoot
    )

    $secretPath = Get-AtlasCloudSecretPath -ProjectRoot $ProjectRoot
    if (-not (Test-Path -LiteralPath $secretPath -PathType Leaf)) {
        throw "Atlas Cloud API key is not configured. Run SET_ATLAS_CLOUD_API_KEY.bat first."
    }

    $protectedValue = [System.IO.File]::ReadAllText($secretPath, [System.Text.UTF8Encoding]::new($false)).Trim()
    if ([string]::IsNullOrWhiteSpace($protectedValue)) {
        throw "The stored Atlas Cloud API key is empty. Run SET_ATLAS_CLOUD_API_KEY.bat again."
    }

    try {
        $secureKey = ConvertTo-SecureString -String $protectedValue
        $keyPointer = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
        try {
            $apiKey = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
        }
        finally {
            [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
        }
    }
    catch {
        throw "The stored Atlas Cloud API key cannot be decrypted for this Windows account. Run SET_ATLAS_CLOUD_API_KEY.bat again."
    }

    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        throw "The stored Atlas Cloud API key is empty. Run SET_ATLAS_CLOUD_API_KEY.bat again."
    }

    return $apiKey
}
