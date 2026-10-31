param(
    [switch]$Watchdog,
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot "frontend"

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

$NodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $NodeCmd) {
    throw "Node.js executable not found in PATH or standard directories."
}

$ViteCli = Join-Path $FrontendDir "node_modules\vite\bin\vite.js"
if (-not (Test-Path $ViteCli)) {
    throw "Vite CLI not found at: $ViteCli. Run 'npm --prefix frontend install' first."
}

Set-Location $FrontendDir
$DistIndex = Join-Path $FrontendDir "dist\index.html"

do {
    if (-not $Dev -and (Test-Path $DistIndex)) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [FRONTEND] Starting Vite Production Preview on http://127.0.0.1:5173 ..." -ForegroundColor Magenta
        & $NodeCmd.Source $ViteCli preview --host 127.0.0.1 --port 5173 --strictPort
    } else {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [FRONTEND] Starting Vite Dev SPA on http://127.0.0.1:5173 ..." -ForegroundColor Magenta
        & $NodeCmd.Source $ViteCli --host 127.0.0.1 --port 5173 --strictPort
    }
    $exitCode = $LASTEXITCODE
    if (-not $Watchdog -or $exitCode -eq 0) {
        break
    }
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [FRONTEND] Vite exited (code=$exitCode). Auto-restarting in 2s..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
} while ($true)
