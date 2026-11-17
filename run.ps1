# run.ps1 — Levanta Docker Compose con HTTPS + IP local para acceder desde otros dispositivos

$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.InterfaceAlias -notmatch "Loopback|Virtual|Hyper-V|WSL|vEthernet" -and
    $_.IPAddress -notmatch "^169\.254\." -and
    $_.IPAddress -notmatch "^127\."
} | Select-Object -First 1).IPAddress

if (-not $ip) {
    Write-Host "No se pudo detectar la IP local. Usando localhost." -ForegroundColor Yellow
    $ip = "localhost"
}

Write-Host ""
Write-Host "IP detectada: " -NoNewline
Write-Host $ip -ForegroundColor Cyan
Write-Host ""

docker compose down

docker compose build backend frontend

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al buildear los servicios." -ForegroundColor Red
    exit 1
}

$env:CERT_HOST = $ip
docker compose up -d
Remove-Item Env:\CERT_HOST -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== ACCESO DESDE EL PC ===" -ForegroundColor Yellow
Write-Host "  URL:   " -NoNewline
Write-Host "http://localhost" -ForegroundColor Green
Write-Host "  (En el PC, localhost funciona como contexto seguro sin advertencia de certificado)" -ForegroundColor DarkGray
Write-Host "  HTTPS opcional: https://localhost (requiere confiar en la CA de desarrollo)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "=== ACCESO DESDE EL CELULAR ===" -ForegroundColor Yellow
Write-Host "  URL:   " -NoNewline
Write-Host "https://${ip}:443" -ForegroundColor Green
Write-Host ""
Write-Host "  PASO 1 (solo la primera vez): Instalar el certificado CA" -ForegroundColor DarkYellow
Write-Host "    1. En Chrome del celular, abri:  " -NoNewline
Write-Host "https://${ip}:443/ca.crt" -ForegroundColor Cyan
Write-Host "    2. Android descargara el certificado. Abri Configuracion >" -NoNewline
Write-Host ""
Write-Host "    3. Busca 'Instalar certificados' o'Encripcion y credenciales'" -NoNewline
Write-Host ""
Write-Host "    4. Selecciona 'Instalar certificado CA'" -NoNewline
Write-Host ""
Write-Host "    5. Elige el archivo descargado" -NoNewline
Write-Host ""
Write-Host "    6. Vuelve a abrir la URL de la app" -NoNewline
Write-Host ""

Write-Host "  En Windows, para confiar en la CA para HTTPS:" -ForegroundColor DarkYellow
Write-Host "    1. Abre https://${ip}:443/ca.crt y continua de forma temporal" -NoNewline
Write-Host ""
Write-Host "    2. Guarda el archivo y abre certmgr.msc" -NoNewline
Write-Host ""
Write-Host "    3. Importalo en Entidades de certificacion raiz de confianza" -NoNewline
Write-Host ""

Write-Host ""
Write-Host "  PASO 2: Abrir la app" -ForegroundColor DarkYellow
Write-Host "    Ahora abri: " -NoNewline
Write-Host "https://${ip}:443" -ForegroundColor Green
Write-Host "    El boton 'Instalar aplicacion' ahora abrira el dialogo nativo de PWA."
Write-Host ""
Write-Host "Logs:  docker compose logs -f" -ForegroundColor DarkGray
Write-Host "Stop: docker compose down    " -ForegroundColor DarkGray
