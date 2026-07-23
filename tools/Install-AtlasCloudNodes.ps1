[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repository = "https://github.com/AtlasCloudAI/atlascloud_comfyui.git"
$commit = "0a918a839af0d74d99c747a84c65b048411c940e"
$projectRoot = Split-Path -Parent $PSScriptRoot
$targetDirectory = Join-Path $projectRoot "AtlasCloud\custom_nodes\atlascloud_comfyui"
$parentDirectory = Split-Path -Parent $targetDirectory
$pythonPath = Join-Path $projectRoot "python_embeded\python.exe"
$safeDirectory = $targetDirectory.Replace("\", "/")

try {
    if (Test-Path -LiteralPath $targetDirectory) {
        $installedCommitOutput = & git -c "safe.directory=$safeDirectory" -C $targetDirectory rev-parse HEAD
        if ($LASTEXITCODE -ne 0) {
            throw "The existing Atlas node directory is not a readable Git checkout: $targetDirectory"
        }
        $installedCommit = ([string]($installedCommitOutput | Select-Object -Last 1)).Trim()
        if ([string]::IsNullOrWhiteSpace($installedCommit)) {
            throw "The existing Atlas node directory did not report an installed revision: $targetDirectory"
        }
        if ($installedCommit -eq $commit) {
            Write-Host "Pinned Atlas Cloud node package is already installed."
            exit 0
        }
        throw "An Atlas node package already exists at $targetDirectory with a different revision. Back it up or remove it deliberately before restoring the pinned package."
    }

    New-Item -ItemType Directory -Force -Path $parentDirectory | Out-Null
    & git clone $repository $targetDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Git could not clone the official Atlas Cloud node package."
    }

    & git -c "safe.directory=$safeDirectory" -C $targetDirectory checkout --detach $commit
    if ($LASTEXITCODE -ne 0) {
        throw "Git could not check out the pinned Atlas Cloud node revision."
    }

    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "Portable Python was not found at $pythonPath."
    }
    & $pythonPath -c "import requests, numpy, PIL"
    if ($LASTEXITCODE -ne 0) {
        throw "The bundled Python runtime is missing an Atlas Cloud node dependency."
    }

    Write-Host "Pinned Atlas Cloud node package was installed successfully."
}
catch {
    Write-Host "Could not install the Atlas Cloud node package: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
