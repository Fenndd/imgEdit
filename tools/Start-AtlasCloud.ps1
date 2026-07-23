[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "AtlasCloud.Common.ps1")

$exitCode = 1
$logPath = $null

try {
    $projectRoot = Split-Path -Parent $PSScriptRoot
    $atlasHome = Initialize-AtlasCloudWorkspace -ProjectRoot $projectRoot
    $apiKey = Get-AtlasCloudApiKey -ProjectRoot $projectRoot
    $pythonPath = Join-Path $projectRoot "python_embeded\python.exe"
    $mainPath = Join-Path $projectRoot "ComfyUI\main.py"
    $logPath = Join-Path $atlasHome "logs\START_ATLAS_CLOUD.log"
    $userDirectory = Join-Path $atlasHome "user"
    $modelsDirectory = Join-Path $atlasHome "models"
    $inputDirectory = Join-Path $atlasHome "input"
    $outputDirectory = Join-Path $atlasHome "output"
    $databasePath = (Join-Path $userDirectory "comfyui.db").Replace("\", "/")
    $databaseUrl = "sqlite:///$databasePath"

    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "Portable Python was not found at $pythonPath."
    }
    if (-not (Test-Path -LiteralPath $mainPath -PathType Leaf)) {
        throw "ComfyUI was not found at $mainPath."
    }

    Add-Content -LiteralPath $logPath -Value "`n==== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] START_ATLAS_CLOUD ===="
    Write-Host "Starting isolated Atlas Cloud ComfyUI at http://127.0.0.1:8189"
    Write-Host "Local FLUX.2 models and local ComfyUI outputs are not used by this profile."
    Write-Host "Full log: $logPath"

    $env:ATLASCLOUD_API_KEY = $apiKey
    $env:ATLASCLOUD_HISTORY_ENABLED = "0"

    & $pythonPath $mainPath `
        --windows-standalone-build `
        --base-directory $atlasHome `
        --user-directory $userDirectory `
        --models-directory $modelsDirectory `
        --input-directory $inputDirectory `
        --output-directory $outputDirectory `
        --database-url $databaseUrl `
        --listen 127.0.0.1 `
        --port 8189 `
        --auto-launch `
        --cpu `
        --cache-none `
        --disable-metadata `
        --disable-all-custom-nodes `
        --whitelist-custom-nodes atlascloud_comfyui `
        --log-stdout *>> $logPath
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Host "Atlas Cloud could not start: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    Remove-Item Env:ATLASCLOUD_API_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:ATLASCLOUD_HISTORY_ENABLED -ErrorAction SilentlyContinue
    Remove-Item Variable:apiKey -ErrorAction SilentlyContinue
}

if ($null -ne $logPath) {
    Add-Content -LiteralPath $logPath -Value "==== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Atlas Cloud stopped, exit code $exitCode ===="
}
exit $exitCode
