param(
    [switch]$Reload,
    [switch]$Watchdog
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    throw "Python virtualenv not found at: $PythonExe"
}

$UvicornArgs = @(
    "-m", "uvicorn", "backend.app.main:app",
    "--host", "127.0.0.1",
    "--port", "8000",
    "--timeout-keep-alive", "30"
)

if ($Reload) {
    # Scope WatchFiles strictly to backend/ and cli/ so .venv, SQLite WAL (.db-wal), and node_modules never trigger restarts
    $UvicornArgs += @("--reload", "--reload-dir", "backend", "--reload-dir", "cli")
}

do {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [BACKEND] Starting FastAPI on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
    & $PythonExe @UvicornArgs
    $exitCode = $LASTEXITCODE
    if (-not $Watchdog -or $exitCode -eq 0) {
        break
    }
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [BACKEND] Uvicorn exited (code=$exitCode). Auto-restarting in 2s..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
} while ($true)
