# run-cloudflare.ps1 - Levanta la app y el Cloudflare Tunnel remoto.

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $projectRoot ".env"

if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Host "No existe el archivo .env en la raiz del proyecto." -ForegroundColor Red
    Write-Host "Crea .env con: CLOUDFLARE_TUNNEL_TOKEN=tu_token_nuevo" -ForegroundColor Yellow
    exit 1
}

$hasToken = $false
foreach ($line in (Get-Content -LiteralPath $envFile)) {
    if ($line -match '^\s*CLOUDFLARE_TUNNEL_TOKEN\s*=\s*[^#\s].*$') {
        $hasToken = $true
        break
    }
}

if (-not $hasToken) {
    Write-Host "Falta CLOUDFLARE_TUNNEL_TOKEN en .env." -ForegroundColor Red
    Write-Host "Genera un token nuevo desde Cloudflare Zero Trust > Networks > Tunnels." -ForegroundColor Yellow
    exit 1
}

Push-Location $projectRoot
try {
    Write-Host "Deteniendo servicios anteriores..." -ForegroundColor Cyan
    docker compose --profile cloudflare down
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron detener los servicios." }

    Write-Host "Construyendo backend y frontend..." -ForegroundColor Cyan
    docker compose build backend frontend
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron construir los servicios." }

    Write-Host "Levantando app + Cloudflare Tunnel..." -ForegroundColor Cyan
    docker compose --profile cloudflare up -d backend frontend lsch_tunnel
    if ($LASTEXITCODE -ne 0) { throw "No se pudo iniciar Cloudflare Tunnel." }

    Write-Host ""
    Write-Host "=== PUENTE LSCh CON CLOUDFLARE ===" -ForegroundColor Green
    Write-Host "La URL publica es la configurada en Cloudflare Zero Trust > Tunnels > Routes." -ForegroundColor Yellow
    Write-Host "Origen configurado en Cloudflare: http://frontend:80" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Estado:" -ForegroundColor Cyan
    docker compose --profile cloudflare ps
    Write-Host ""
    Write-Host "Logs del tunel: docker compose logs -f lsch_tunnel" -ForegroundColor DarkGray
    Write-Host "Detener: docker compose --profile cloudflare down" -ForegroundColor DarkGray
}
finally {
    Pop-Location
}
