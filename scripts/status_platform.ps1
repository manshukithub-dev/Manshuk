$ErrorActionPreference = "SilentlyContinue"

function Check-Service([string]$Name, [int]$Port, [string]$Url) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    $procId = if ($conn) { $conn.OwningProcess } else { $null }
    $httpCode = "OFFLINE"
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        $httpCode = "HTTP $($resp.StatusCode)"
    } catch {
        if ($_.Exception.Response) {
            $httpCode = "HTTP $([int]$_.Exception.Response.StatusCode)"
        }
    }
    $pidDisplay = if ($procId) { "$procId" } else { "-" }
    $color = if ($httpCode -eq "HTTP 200") { "Green" } else { "Red" }
    Write-Host ("{0,-22} | Port: {1,-5} | PID: {2,-7} | Status: {3} | {4}" -f $Name, $Port, $pidDisplay, $httpCode, $Url) -ForegroundColor $color
}

Write-Host "--------------------------------------------------------------------------------------"
Check-Service -Name "Frontend (Vite SPA)" -Port 5173 -Url "http://127.0.0.1:5173/"
Check-Service -Name "Backend (FastAPI)"   -Port 8000 -Url "http://127.0.0.1:8000/api/health"
Write-Host "--------------------------------------------------------------------------------------"
