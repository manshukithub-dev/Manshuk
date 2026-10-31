param(
    [ValidateSet("all", "backend", "frontend")]
    [string]$Target = "all"
)

$ErrorActionPreference = "SilentlyContinue"

function Stop-ByPort([int]$Port, [string]$Label) {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) {
        Write-Host "[INFO] $Label (port $Port) is already stopped." -ForegroundColor DarkGray
        return
    }
    $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        $parentId = (Get-CimInstance Win32_Process -Filter "ProcessId = $procId").ParentProcessId
        if ($parentId) {
            $parentProc = Get-CimInstance Win32_Process -Filter "ProcessId = $parentId"
            if ($parentProc -and $parentProc.CommandLine -match "start_(backend|frontend)\.ps1") {
                Stop-Process -Id $parentId -Force -ErrorAction SilentlyContinue
            }
        }
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Write-Host "[STOPPED] $Label stopped (Port: $Port, PID: $procId)." -ForegroundColor Yellow
    }
}

if ($Target -in @("all", "backend")) {
    Stop-ByPort -Port 8000 -Label "Backend (FastAPI)"
}
if ($Target -in @("all", "frontend")) {
    Stop-ByPort -Port 5173 -Label "Frontend (Vite)"
}
