<#
.SYNOPSIS
    Lenovo ThinkPad BIOS WMI Hotkey & FnLock Configuration Tool.
.DESCRIPTION
    Directly queries and modifies the ThinkPad Embedded Controller / BIOS settings
    via root\wmi:Lenovo_BiosSetting to ensure FnKeyAsPrimary persists across reboots.
.PARAMETER Action
    Query, Enable, or Disable.
#>
param(
    [ValidateSet("Query", "Enable", "Disable")]
    [string]$Action = "Query"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Lenovo ThinkPad WMI BIOS Hotkey Configuration Manager" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

try {
    $settings = Get-CimInstance -Namespace root\wmi -ClassName Lenovo_BiosSetting -ErrorAction Stop
    $fnSetting = $settings | Where-Object { $_.CurrentSetting -like "*FnKeyAsPrimary*" }
    
    if (-not $fnSetting) {
        Write-Warning "Lenovo_BiosSetting 'FnKeyAsPrimary' not found on this machine."
        exit 1
    }

    Write-Host "[+] Current Setting: $($fnSetting.CurrentSetting)" -ForegroundColor Yellow

    if ($Action -eq "Query") {
        exit 0
    }

    $targetVal = if ($Action -eq "Enable") { "FnKeyAsPrimary,Enable" } else { "FnKeyAsPrimary,Disable" }
    Write-Host "[*] Applying BIOS configuration: $targetVal..." -ForegroundColor Cyan

    $setResult = Invoke-CimMethod -Namespace root\wmi -ClassName Lenovo_SetBiosSetting -MethodName SetBiosSetting -Arguments @{ Parameter = $targetVal }
    Write-Host "[+] SetBiosSetting Result: $($setResult.return)" -ForegroundColor Green

    $saveResult = Invoke-CimMethod -Namespace root\wmi -ClassName Lenovo_SaveBiosSettings -MethodName SaveBiosSettings
    Write-Host "[+] SaveBiosSettings Result: $($saveResult.return)" -ForegroundColor Green

    # Re-verify
    $verify = (Get-CimInstance -Namespace root\wmi -ClassName Lenovo_BiosSetting | Where-Object { $_.CurrentSetting -like "*FnKeyAsPrimary*" }).CurrentSetting
    Write-Host "[✓] Verified Persistent State: $verify" -ForegroundColor Green

} catch {
    Write-Error "WMI Error: $_"
    exit 1
}
