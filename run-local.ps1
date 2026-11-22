# run-local.ps1 — Levanta backend (FastAPI) y frontend (Vite) en local, sin Docker.
# Ideal cuando se busca menor consumo de RAM y acceso directo a GPU CUDA en Windows.
#
# Ejemplos de uso:
#   .\run-local.ps1                  # Whisper real (modelo small, GPU CUDA/CPU auto)
#   .\run-local.ps1 -Provider stub   # Modo liviano sin cargar Whisper (minima RAM)
#   .\run-local.ps1 -Seed            # Re-siembra la base de datos antes de iniciar
#   .\run-local.ps1 -Open            # Abre http://localhost:5173 en tu navegador

param(
    [ValidateSet("whisper", "stub")]
    [string]$Provider = "whisper",
    [string]$Model = "small",
    [string]$Device = "auto",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [switch]$Seed,
    [switch]$Open
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$pythonExe = Join-Path $backendDir "venv\Scripts\python.exe"
$uvicornExe = Join-Path $backendDir "venv\Scripts\uvicorn.exe"
$dbDefault = Join-Path $backendDir "app\data\glosario.db"
$dbAlt = Join-Path $backendDir "data\glosario.db"

function Test-PortInUse {
    param([int]$Port)

    $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listening) {
        return $true
    }

    $listener = $null
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $false
    }
    catch {
        return $true
    }
    finally {
        if ($listener) { $listener.Stop() }
    }
}

function Find-FreePort {
    param([int]$StartPort, [int]$MaxAttempts = 15)

    for ($port = $StartPort; $port -lt ($StartPort + $MaxAttempts); $port++) {
        if (-not (Test-PortInUse -Port $port)) {
            return $port
        }
    }
    throw "No se encontro un puerto libre entre $StartPort y $($StartPort + $MaxAttempts - 1)."
}

function Stop-ProcessTree {
    param($Proc)
    if ($null -eq $Proc) { return }
    try {
        if (-not $Proc.HasExited) {
            & taskkill.exe /PID $Proc.Id /T /F 2>$null | Out-Null
        }
    }
    catch {
        # Ignorar si el proceso ya termino.
    }
}

if (-not (Test-Path -LiteralPath $uvicornExe)) {
    Write-Host "No se encontro el entorno virtual del backend en: $uvicornExe" -ForegroundColor Red
    Write-Host "Ejecuta una vez:" -ForegroundColor Yellow
    Write-Host "  cd backend"
    Write-Host "  python -m venv venv"
    Write-Host "  .\venv\Scripts\activate"
    Write-Host "  pip install -r requirements.txt"
    Write-Host "  python -m spacy download es_core_news_md"
    exit 1
}

$pnpmCmd = Get-Command pnpm.cmd, pnpm.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $pnpmCmd) {
    Write-Host "No se encontro pnpm en el PATH. Instalalo con 'corepack enable' o 'npm i -g pnpm'." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules"))) {
    Write-Host "Instalando dependencias del frontend con pnpm..." -ForegroundColor Cyan
    Push-Location $frontendDir
    try {
        & $pnpmCmd.Source install
        if ($LASTEXITCODE -ne 0) { throw "Error al ejecutar pnpm install." }
    }
    finally {
        Pop-Location
    }
}

$dbExists = (Test-Path -LiteralPath $dbDefault) -or (Test-Path -LiteralPath $dbAlt)
if ($Seed -or -not $dbExists) {
    Write-Host "Sembrando base de datos local..." -ForegroundColor Cyan
    Push-Location $backendDir
    try {
        & $pythonExe (Join-Path $backendDir "scripts\seed_glosario.py")
        if ($LASTEXITCODE -ne 0) { throw "Error al sembrar la base de datos." }
    }
    finally {
        Pop-Location
    }
}

$resolvedBackendPort = Find-FreePort -StartPort $BackendPort
if ($resolvedBackendPort -ne $BackendPort) {
    Write-Host "Puerto $BackendPort ocupado; usando puerto $resolvedBackendPort para el backend." -ForegroundColor Yellow
}

$resolvedFrontendPort = Find-FreePort -StartPort $FrontendPort
if ($resolvedFrontendPort -ne $FrontendPort) {
    Write-Host "Puerto $FrontendPort ocupado; usando puerto $resolvedFrontendPort para el frontend." -ForegroundColor Yellow
}

$envVarsToManage = @(
    "ASR_PROVIDER",
    "WHISPER_MODEL",
    "WHISPER_DEVICE",
    "CORS_ORIGINS",
    "VITE_API_URL",
    "VITE_WS_URL"
)
$savedEnv = @{}
foreach ($name in $envVarsToManage) {
    $savedEnv[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
}

$backendProc = $null
$frontendProc = $null

try {
    $env:ASR_PROVIDER = $Provider
    $env:WHISPER_MODEL = $Model
    $env:WHISPER_DEVICE = $Device
    $env:CORS_ORIGINS = "http://localhost:$resolvedFrontendPort,http://127.0.0.1:$resolvedFrontendPort"

    Write-Host ""
    Write-Host "=== PUENTE LSCh (MODO LOCAL SIN DOCKER) ===" -ForegroundColor Green
    Write-Host "  App:      http://localhost:$resolvedFrontendPort" -ForegroundColor Cyan
    Write-Host "  Backend:  http://127.0.0.1:$resolvedBackendPort" -ForegroundColor Cyan
    if ($Provider -eq "whisper") {
        Write-Host "  ASR:      faster-whisper (modelo=$Model, dispositivo=$Device)" -ForegroundColor DarkGray
    }
    else {
        Write-Host "  ASR:      stub (simulado, bajo consumo de RAM)" -ForegroundColor DarkGray
    }
    Write-Host "  Usuarios: 12345678-5 (emisor) / 9876543-3 (oyente) · clave: test123" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Presiona Ctrl + C para detener ambos servidores y liberar la RAM." -ForegroundColor Yellow
    Write-Host ""

    $backendProc = Start-Process `
        -FilePath $uvicornExe `
        -ArgumentList @("app.main:app", "--host", "127.0.0.1", "--port", "$resolvedBackendPort") `
        -WorkingDirectory $backendDir `
        -NoNewWindow `
        -PassThru

    $env:VITE_API_URL = "http://127.0.0.1:$resolvedBackendPort"
    $env:VITE_WS_URL = "ws://127.0.0.1:$resolvedBackendPort"

    $frontendProc = Start-Process `
        -FilePath "cmd.exe" `
        -ArgumentList @("/c", "`"$($pnpmCmd.Source)`" dev --host --port $resolvedFrontendPort") `
        -WorkingDirectory $frontendDir `
        -NoNewWindow `
        -PassThru

    if ($Open) {
        Start-Sleep -Seconds 2
        Start-Process "http://localhost:$resolvedFrontendPort"
    }

    while (-not $backendProc.HasExited -and -not $frontendProc.HasExited) {
        Start-Sleep -Milliseconds 500
    }

    if ($backendProc.HasExited) {
        Write-Host "El backend se detuvo (codigo $($backendProc.ExitCode)). Cerrando frontend..." -ForegroundColor Yellow
    }
    elseif ($frontendProc.HasExited) {
        Write-Host "El frontend se detuvo (codigo $($frontendProc.ExitCode)). Cerrando backend..." -ForegroundColor Yellow
    }
}
finally {
    Stop-ProcessTree -Proc $frontendProc
    Stop-ProcessTree -Proc $backendProc

    foreach ($name in $envVarsToManage) {
        if ($null -eq $savedEnv[$name]) {
            Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        }
        else {
            [Environment]::SetEnvironmentVariable($name, $savedEnv[$name], "Process")
        }
    }

    Write-Host ""
    Write-Host "Servidores locales detenidos." -ForegroundColor Green
}
