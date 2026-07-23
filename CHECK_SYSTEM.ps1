[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference = 'Stop'

$os = $null
$computer = $null
$cpu = $null
$drives = @()
$pagefiles = @()

try {
    $os = Get-CimInstance Win32_OperatingSystem
    $computer = Get-CimInstance Win32_ComputerSystem
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $drives = @(Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3")
    $pagefiles = @(Get-CimInstance Win32_PageFileSetting)
} catch {
    Write-Warning "CIM/WMI diagnostics unavailable: $($_.Exception.Message)"
    Write-Warning "GPU, package versions and commits above remain valid; run from a normal Windows session for RAM/pagefile diagnostics."
}

if ($null -ne $os -and $null -ne $computer -and $null -ne $cpu) {
    [PSCustomObject]@{
        OS = "$($os.Caption) ($($os.BuildNumber))"
        CPU = "$($cpu.Name) | $($cpu.NumberOfCores) cores / $($cpu.NumberOfLogicalProcessors) threads"
        TotalRAMGiB = [math]::Round($computer.TotalPhysicalMemory / 1GB, 2)
        FreeRAMGiB = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
        CommitLimitGiB = [math]::Round($os.TotalVirtualMemorySize / 1MB, 2)
        CommitInUseGiB = [math]::Round(($os.TotalVirtualMemorySize - $os.FreeVirtualMemory) / 1MB, 2)
        Pagefile = ($pagefiles | ForEach-Object { "$($_.Name): initial $($_.InitialSize) MB, maximum $($_.MaximumSize) MB" }) -join '; '
    } | Format-List
}

if ($drives.Count -gt 0) {
    $drives | ForEach-Object {
        [PSCustomObject]@{
            Drive = $_.DeviceID
            Label = $_.VolumeName
            SizeGiB = [math]::Round($_.Size / 1GB, 2)
            FreeGiB = [math]::Round($_.FreeSpace / 1GB, 2)
        }
    } | Format-Table -AutoSize
} else {
    Get-PSDrive -PSProvider FileSystem | ForEach-Object {
        [PSCustomObject]@{
            Drive = $_.Root
            Label = 'FileSystem fallback'
            SizeGiB = if ($_.Used -ne $null -and $_.Free -ne $null) { [math]::Round(($_.Used + $_.Free) / 1GB, 2) } else { $null }
            FreeGiB = if ($_.Free -ne $null) { [math]::Round($_.Free / 1GB, 2) } else { $null }
        }
    } | Format-Table -AutoSize
}
