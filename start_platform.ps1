param(
    [switch]$ReloadBackend
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$LogsDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

function Test-PortListening([int]$Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    return ($null -ne $conn)
}

Write-Host "=== QAZAQ LOC QA - Independent Server Launcher ===" -ForegroundColor Cyan

# 1. Independent Backend Process (Port 8000)
if (Test-PortListening -Port 8000) {
    Write-Host "[OK] Backend (127.0.0.1:8000) is already running." -ForegroundColor Green
} else {
    $beScript = Join-Path $Root "scripts\start_backend.ps1"
    $beArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$beScript`"", "-Watchdog")
    if ($ReloadBackend) { $beArgs += "-Reload" }
    $beProc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList $beArgs `
        -WorkingDirectory $Root `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogsDir "backend.out.log") `
        -RedirectStandardError (Join-Path $LogsDir "backend.err.log") `
        -PassThru
    Write-Host "[START] Backend started in isolated process (PID: $($beProc.Id)) -> logs/backend.*.log" -ForegroundColor Cyan
}

# 2. Independent Frontend Process (Port 5173)
if (Test-PortListening -Port 5173) {
    Write-Host "[OK] Frontend (127.0.0.1:5173) is already running." -ForegroundColor Green
} else {
    $feScript = Join-Path $Root "scripts\start_frontend.ps1"
    $feArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$feScript`"", "-Watchdog")
    $feProc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList $feArgs `
        -WorkingDirectory (Join-Path $Root "frontend") `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogsDir "frontend.out.log") `
        -RedirectStandardError (Join-Path $LogsDir "frontend.err.log") `
        -PassThru
    Write-Host "[START] Frontend started in isolated process (PID: $($feProc.Id)) -> logs/frontend.*.log" -ForegroundColor Magenta
}

# Wait up to 12 seconds for HTTP readiness
for ($i = 0; $i -lt 24; $i++) {
    $beOk = $false
    $feOk = $false
    try {
        $r1 = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 1
        if ($r1.StatusCode -eq 200) { $beOk = $true }
    } catch {}
    try {
        $r2 = Invoke-WebRequest -Uri "http://127.0.0.1:5173/" -UseBasicParsing -TimeoutSec 1
        if ($r2.StatusCode -eq 200) { $feOk = $true }
    } catch {}
    if ($beOk -and $feOk) { break }
    Start-Sleep -Milliseconds 500
}

& (Join-Path $Root "scripts\status_platform.ps1")
