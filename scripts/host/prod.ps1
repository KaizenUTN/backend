# ─────────────────────────────────────────────────────────────────
# prod.ps1 — Levanta el entorno de producción desde cero.
#
# Uso:
#   .\scripts\host\prod.ps1              # build + start (background)
#   .\scripts\host\prod.ps1 -Mode down   # detiene y elimina contenedores
#   .\scripts\host\prod.ps1 -Mode logs   # muestra logs en tiempo real
#
# El contenedor ejecuta automáticamente:
#   migrate → seed_authorization → collectstatic → gunicorn
#
# IMPORTANTE: asegurarse de tener .env.prod configurado antes de correr.
# ─────────────────────────────────────────────────────────────────
param(
    [ValidateSet("start", "down", "logs")]
    [string]$Mode = "start"
)

$ComposeFile = "docker-compose.prod.yaml"

if (-not (Test-Path ".env.prod")) {
    Write-Host "ERROR: .env.prod not found. Copy .env.example and configure it first." -ForegroundColor Red
    exit 1
}

switch ($Mode) {
    "down" {
        Write-Host "[PROD] Stopping environment..." -ForegroundColor Yellow
        docker-compose -f $ComposeFile down
    }
    "logs" {
        docker-compose -f $ComposeFile logs -f
    }
    default {
        Write-Host "[PROD] Building and starting production environment..." -ForegroundColor Yellow
        docker-compose -f $ComposeFile up --build -d
        Write-Host ""
        Write-Host "[PROD] Production environment started ✓" -ForegroundColor Green
        Write-Host ""
        Write-Host "Useful commands:"
        Write-Host "  Logs:   .\scripts\host\prod.ps1 -Mode logs"
        Write-Host "  Stop:   .\scripts\host\prod.ps1 -Mode down"
        Write-Host "  Shell:  docker-compose -f $ComposeFile exec web bash"
    }
}
