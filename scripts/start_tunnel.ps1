param(
    [switch]$Watchdog
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$LogsDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

$CandidateNodeDirs = @(
    "$HOME\.local\tools\node-v22.14.0-win-x64",
    "$HOME\.local\bin",
    "C:\Program Files\nodejs",
    "$env:LOCALAPPDATA\Programs\nodejs",
    "$env:APPDATA\npm"
)
foreach ($dir in $CandidateNodeDirs) {
    if (Test-Path $dir) {
        $env:PATH = "$dir;$env:PATH"
    }
}

# Ensure Backend (8000) and Frontend (5173) are running before opening tunnel
$beListening = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$feListening = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $beListening -or -not $feListening) {
    Write-Host "[INFO] Starting local Backend (8000) & Frontend (5173) first..." -ForegroundColor Cyan
    & (Join-Path $ProjectRoot "start_platform.ps1")
}

$CfCmd = Get-Command cloudflared.cmd -ErrorAction SilentlyContinue
if (-not $CfCmd) {
    $CfCmd = Get-Command cloudflared -ErrorAction SilentlyContinue
}
if (-not $CfCmd) {
    throw "Cloudflare Tunnel ('cloudflared') not found. Run 'npm install -g cloudflared' first."
}

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " QAZAQ LOC QA - Password-Free Global HTTPS Tunnel (Cloudflare)" -ForegroundColor Green
Write-Host " Opens directly on ANY computer & phone with ZERO password!" -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Cyan

do {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [TUNNEL] Opening Cloudflare HTTPS tunnel -> http://127.0.0.1:5173 ..." -ForegroundColor Magenta
    & $CfCmd.Source tunnel --url http://127.0.0.1:5173 --no-autoupdate
    $exitCode = $LASTEXITCODE
    if (-not $Watchdog) {
        break
    }
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [TUNNEL] Tunnel exited (code=$exitCode). Reconnecting in 2s..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
} while ($true)
