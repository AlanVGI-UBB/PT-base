# run.ps1 — Levanta Docker Compose con la IP local para acceder desde otros dispositivos

$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.InterfaceAlias -notmatch "Loopback|Virtual|Hyper-V|WSL|vEthernet" -and
    $_.IPAddress -notmatch "^169\.254\." -and
    $_.IPAddress -notmatch "^127\."
} | Select-Object -First 1).IPAddress

if (-not $ip) {
    Write-Host "No se pudo detectar la IP local. Usando localhost." -ForegroundColor Yellow
    $ip = "localhost"
}

Write-Host "IP detectada: $ip" -ForegroundColor Cyan
Write-Host "Frontend: http://${ip}:5173" -ForegroundColor Green
Write-Host ""

docker compose down

docker compose build `
    --build-arg VITE_API_URL="http://${ip}:8000" `
    --build-arg VITE_WS_URL="ws://${ip}:8000" `
    frontend

if ($?) {
    docker compose up -d
    Write-Host ""
    Write-Host "Abrí en el celular: http://${ip}:5173" -ForegroundColor Green
    Write-Host "Logs:  docker compose logs -f" -ForegroundColor DarkGray
}
