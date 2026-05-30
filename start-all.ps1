$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $Root "sau_frontend"
$PythonExe = Join-Path $Root ".venv\Scripts\python.exe"
$UvExe = Join-Path $Root ".venv\Scripts\uv.exe"
$BackendLog = Join-Path $Root "backend.out.log"
$BackendErr = Join-Path $Root "backend.err.log"
$FrontendLog = Join-Path $Root "frontend.out.log"
$FrontendErr = Join-Path $Root "frontend.err.log"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-ListenProcessId($Port) {
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        return @()
    }
    return @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Get-CommandLine($ProcessId) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
    if ($proc) {
        return [string]$proc.CommandLine
    }
    return ""
}

function Stop-ProjectProcessOnPort($Port) {
    foreach ($processId in (Get-ListenProcessId $Port)) {
        $cmd = Get-CommandLine $processId
        if ($cmd -like "*social-auto-upload*" -or $cmd -like "*sau_backend.py*" -or $cmd -like "*sau_frontend*") {
            Write-Host "Stopping old project process on port $Port (PID $processId)"
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        } else {
            throw "Port $Port is already used by another process (PID $processId): $cmd"
        }
    }
}

function Stop-ProjectFrontendProcesses {
    for ($port = 5173; $port -lt 5193; $port++) {
        foreach ($processId in (Get-ListenProcessId $port)) {
            $cmd = Get-CommandLine $processId
            if ($cmd -like "*social-auto-upload*" -or $cmd -like "*sau_frontend*" -or $cmd -like "*vite.js*") {
                Write-Host "Stopping old frontend process on port $port (PID $processId)"
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Stop-ProjectBackendProcesses {
    $processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*sau_backend.py*" }
    foreach ($proc in $processes) {
        Write-Host "Stopping old backend process (PID $($proc.ProcessId))"
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Find-FreePort($StartPort) {
    for ($port = $StartPort; $port -lt ($StartPort + 20); $port++) {
        if ((Get-ListenProcessId $port).Count -eq 0) {
            return $port
        }
    }
    throw "No free frontend port found from $StartPort to $($StartPort + 19)."
}

function Test-PythonImports {
    if (-not (Test-Path $PythonExe)) {
        return $false
    }
    & $PythonExe -c "import flask, flask_cors, playwright, patchright, requests, qrcode, loguru" 2>$null
    return ($LASTEXITCODE -eq 0)
}

Set-Location $Root

Write-Step "Preparing Python environment"
if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating .venv with uv..."
    python -m pip install uv
    python -m uv venv
}

if (-not (Test-PythonImports)) {
    Write-Host "Installing Python dependencies..."
    python -m uv pip install -e ".[web]"
    python -m uv pip install -r requirements.txt
    & $PythonExe -m playwright install chromium
    & (Join-Path $Root ".venv\Scripts\patchright.exe") install chromium
} else {
    Write-Host "Python dependencies look ready."
}

Write-Step "Preparing config and database"
if (-not (Test-Path (Join-Path $Root "conf.py"))) {
    Copy-Item -LiteralPath (Join-Path $Root "conf.example.py") -Destination (Join-Path $Root "conf.py")
    Write-Host "Created conf.py from conf.example.py"
}

if (-not (Test-Path (Join-Path $Root "db"))) {
    New-Item -ItemType Directory -Path (Join-Path $Root "db") | Out-Null
}
if (-not (Test-Path (Join-Path $Root "videoFile"))) {
    New-Item -ItemType Directory -Path (Join-Path $Root "videoFile") | Out-Null
}
if (-not (Test-Path (Join-Path $Root "cookiesFile"))) {
    New-Item -ItemType Directory -Path (Join-Path $Root "cookiesFile") | Out-Null
}

$DbInit = @'
import sqlite3
from pathlib import Path

db_path = Path("db") / "database.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type INTEGER NOT NULL,
    filePath TEXT NOT NULL,
    userName TEXT NOT NULL,
    status INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS file_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filesize REAL,
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    file_path TEXT
)
""")

conn.commit()
conn.close()
print("database ready")
'@
$DbInit | & $PythonExe -

Write-Step "Preparing frontend dependencies"
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "Installing npm dependencies..."
    Push-Location $FrontendDir
    npm install
    Pop-Location
} else {
    Write-Host "Frontend dependencies look ready."
}

Write-Step "Starting backend"
Stop-ProjectBackendProcesses
Start-Sleep -Seconds 1
Stop-ProjectProcessOnPort 5409
Remove-Item -LiteralPath $BackendLog, $BackendErr -ErrorAction SilentlyContinue
Start-Process -FilePath $PythonExe `
    -ArgumentList @("-u", "sau_backend.py") `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $BackendLog `
    -RedirectStandardError $BackendErr

Start-Sleep -Seconds 3
if ((Get-ListenProcessId 5409).Count -eq 0) {
    Write-Host "Backend failed to start. See backend.err.log:" -ForegroundColor Red
    Get-Content $BackendErr -Tail 80 -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "Backend: http://127.0.0.1:5409"

Write-Step "Starting frontend"
Stop-ProjectFrontendProcesses
Start-Sleep -Seconds 1
$FrontendPort = Find-FreePort 5173
Remove-Item -LiteralPath $FrontendLog, $FrontendErr -ErrorAction SilentlyContinue
Start-Process -FilePath "C:\Program Files\nodejs\npm.cmd" `
    -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$FrontendPort") `
    -WorkingDirectory $FrontendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $FrontendLog `
    -RedirectStandardError $FrontendErr

Start-Sleep -Seconds 5
if ((Get-ListenProcessId $FrontendPort).Count -eq 0) {
    Write-Host "Frontend failed to start. See frontend.err.log:" -ForegroundColor Red
    Get-Content $FrontendErr -Tail 80 -ErrorAction SilentlyContinue
    exit 1
}

$FrontendUrl = "http://127.0.0.1:$FrontendPort/"
Write-Host "Frontend: $FrontendUrl"
Write-Host ""
Write-Host "SAU is running." -ForegroundColor Green
Write-Host "Logs:"
Write-Host "  $BackendLog"
Write-Host "  $BackendErr"
Write-Host "  $FrontendLog"
Write-Host "  $FrontendErr"

Start-Process $FrontendUrl
