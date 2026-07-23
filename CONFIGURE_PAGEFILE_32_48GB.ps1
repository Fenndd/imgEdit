[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z]:$')]
    [string]$DriveLetter = 'C:',
    [ValidateRange(32768, 49152)]
    [int]$InitialSizeMB = 32768,
    [ValidateRange(32768, 65536)]
    [int]$MaximumSizeMB = 49152
)

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference = 'Stop'

if ($MaximumSizeMB -lt $InitialSizeMB) {
    throw 'MaximumSizeMB must be greater than or equal to InitialSizeMB.'
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from an elevated PowerShell window (Run as administrator). No settings were changed.'
}

$volume = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$DriveLetter'"
if ($null -eq $volume) {
    throw "Drive $DriveLetter was not found. No settings were changed."
}

$driveName = $DriveLetter.TrimEnd(':')
try {
    $selectedDisk = Get-Partition -DriveLetter $driveName -ErrorAction Stop | Get-Disk -ErrorAction Stop
} catch {
    throw "Could not map drive $DriveLetter to its physical disk. Select an SSD/NVMe drive and try again. No settings were changed."
}

if (($selectedDisk.MediaType -ne 'SSD') -and ($selectedDisk.BusType -ne 'NVMe')) {
    throw ("Drive {0} maps to {1} (MediaType: {2}; BusType: {3}), not an SSD/NVMe disk. Select an SSD/NVMe drive. No settings were changed." -f $DriveLetter, $selectedDisk.FriendlyName, $selectedDisk.MediaType, $selectedDisk.BusType)
}

$requiredFreeBytes = 60GB
if ($volume.FreeSpace -lt $requiredFreeBytes) {
    throw ("Drive {0} has only {1:N1} GiB free; at least 60 GiB are required for a safe 32-48 GiB pagefile." -f $DriveLetter, ($volume.FreeSpace / 1GB))
}

$physicalDisks = Get-PhysicalDisk -ErrorAction SilentlyContinue |
    Select-Object FriendlyName, MediaType, BusType, Size, HealthStatus
if ($physicalDisks) {
    Write-Host 'Detected physical disks (prefer SSD/NVMe):'
    $physicalDisks | Format-Table -AutoSize | Out-Host
}

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupPath = Join-Path $PSScriptRoot "pagefile_configuration_before_$timestamp.json"
$computerSystem = Get-CimInstance Win32_ComputerSystem
$oldSettings = @(Get-CimInstance Win32_PageFileSetting | Select-Object Name, InitialSize, MaximumSize)
@{
    CapturedAt = (Get-Date).ToString('o')
    AutomaticManagedPagefile = $computerSystem.AutomaticManagedPagefile
    PagefileSettings = $oldSettings
    RequestedDrive = $DriveLetter
    RequestedInitialSizeMB = $InitialSizeMB
    RequestedMaximumSizeMB = $MaximumSizeMB
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $backupPath -Encoding utf8

if ($computerSystem.AutomaticManagedPagefile) {
    Set-CimInstance -InputObject $computerSystem -Property @{ AutomaticManagedPagefile = $false } | Out-Null
}

$pagefilePath = "$DriveLetter\pagefile.sys"
$existing = Get-CimInstance Win32_PageFileSetting | Where-Object { $_.Name -eq $pagefilePath }
if ($existing) {
    Set-CimInstance -InputObject $existing -Property @{ InitialSize = $InitialSizeMB; MaximumSize = $MaximumSizeMB } | Out-Null
} else {
    New-CimInstance -ClassName Win32_PageFileSetting -Property @{
        Name = $pagefilePath
        InitialSize = $InitialSizeMB
        MaximumSize = $MaximumSizeMB
    } | Out-Null
}

Write-Host "Configured ${pagefilePath}: $InitialSizeMB-$MaximumSizeMB MB."
Write-Host "Previous configuration saved to: $backupPath"
Write-Host 'Restart Windows before relying on the new pagefile size.'
