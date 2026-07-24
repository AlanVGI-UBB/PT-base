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

# Reconstruir frontend con URLs vacías (relativas) + pasar IP para el certificado
docker compose build frontend

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al buildear el frontend." -ForegroundColor Red
    exit 1
}

# Pasar la IP como CERT_HOST para el certificado autofirmado
$env:CERT_HOST = $ip
docker compose up -d
Remove-Item Env:\CERT_HOST -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Abrí en este PC:    " -NoNewline
Write-Host "https://localhost:443" -ForegroundColor Green
Write-Host "  (aceptá la advertencia de seguridad del certificado)"
Write-Host ""
Write-Host "Abrí en el celular:  " -NoNewline
Write-Host "https://${ip}:443" -ForegroundColor Green
Write-Host "  (aceptá la advertencia de seguridad del certificado)"
Write-Host ""
Write-Host "Para ver logs:" -ForegroundColor DarkGray
Write-Host "  docker compose logs -f" -ForegroundColor DarkGray