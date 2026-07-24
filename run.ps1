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

docker compose build frontend

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al buildear el frontend." -ForegroundColor Red
    exit 1
}

$env:CERT_HOST = $ip
docker compose up -d
Remove-Item Env:\CERT_HOST -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== ACCESO DESDE EL PC ===" -ForegroundColor Yellow
Write-Host "  URL:   " -NoNewline
Write-Host "https://localhost:443" -ForegroundColor Green
Write-Host "  (Acepta la advertencia de seguridad del certificado una sola vez)"
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
Write-Host "    6. РФЕРФ" -NoNewline
Write-Host ""

Write-Host ""
Write-Host "  PASO 2: Abrir la app" -ForegroundColor DarkYellow
Write-Host "    Ahora abri: " -NoNewline
Write-Host "https://${ip}:443" -ForegroundColor Green
Write-Host "    El boton 'Instalar aplicacion' ahora abrira el dialogo nativo de PWA."
Write-Host ""
Write-Host "Logs:  docker compose logs -f" -ForegroundColor DarkGray
Write-Host "Stop: docker compose down    " -ForegroundColor DarkGray