# ─────────────────────────────────────────────────────────────────
# dev.ps1 — Levanta el entorno de desarrollo completo desde cero.
#
# Uso:
#   .\scripts\host\dev.ps1             # build + start (foreground con logs)
#   .\scripts\host\dev.ps1 -Mode bg    # build + start en background
#   .\scripts\host\dev.ps1 -Mode down  # detiene y elimina contenedores
#
# El contenedor ejecuta automáticamente:
#   migrate → seed_authorization → runserver
# ─────────────────────────────────────────────────────────────────
param(
    [ValidateSet("fg", "bg", "down")]
    [string]$Mode = "fg"
)

$ComposeFile = "docker-compose.dev.yaml"

switch ($Mode) {
    "down" {
        Write-Host "[DEV] Stopping environment..." -ForegroundColor Yellow
        docker-compose -f $ComposeFile down
    }
    "bg" {
        Write-Host "[DEV] Building and starting in background..." -ForegroundColor Cyan
        docker-compose -f $ComposeFile up --build -d
        Write-Host ""
        Write-Host "[DEV] Done. Useful commands:" -ForegroundColor Green
        Write-Host "  Logs:   docker-compose -f $ComposeFile logs -f"
        Write-Host "  Stop:   .\scripts\host\dev.ps1 -Mode down"
        Write-Host "  Shell:  docker-compose -f $ComposeFile exec web bash"
    }
    default {
        Write-Host "[DEV] Building and starting (foreground)..." -ForegroundColor Cyan
        docker-compose -f $ComposeFile up --build
    }
}
