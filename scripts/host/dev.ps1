# ─────────────────────────────────────────────────────────────────
# dev.ps1 — Levanta el entorno de desarrollo completo desde cero.
#
# Uso:
#   .\scripts\host\dev.ps1                # build + start (foreground con logs)
#   .\scripts\host\dev.ps1 -Mode bg       # build + start en background
#   .\scripts\host\dev.ps1 -Mode down     # detiene y elimina contenedores
#   .\scripts\host\dev.ps1 -Mode migrate  # genera + aplica migraciones
#   .\scripts\host\dev.ps1 -Mode shell    # abre bash dentro del contenedor
#
# FLUJO CUANDO CAMBIÁS UN MODELO:
#   1. .\scripts\host\dev.ps1 -Mode migrate   ← genera archivos + aplica
#   2. git add apps/*/migrations/             ← commitear las migraciones
#   3. .\scripts\host\dev.ps1               ← reiniciar con el modelo aplicado
#
# El contenedor ejecuta automáticamente: migrate → seed_authorization → runserver
# ─────────────────────────────────────────────────────────────────
param(
    [ValidateSet("fg", "bg", "down", "migrate", "shell")]
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
        Write-Host "  Logs:      docker-compose -f $ComposeFile logs -f"
        Write-Host "  Stop:      .\scripts\host\dev.ps1 -Mode down"
        Write-Host "  Shell:     .\scripts\host\dev.ps1 -Mode shell"
        Write-Host "  Migrate:   .\scripts\host\dev.ps1 -Mode migrate"
    }
    "migrate" {
        Write-Host "[DEV] Generating and applying migrations..." -ForegroundColor Cyan
        docker-compose -f $ComposeFile exec web python manage.py makemigrations
        docker-compose -f $ComposeFile exec web python manage.py migrate
        Write-Host ""
        Write-Host "[DEV] Done. Commit the generated migration files!" -ForegroundColor Green
    }
    "shell" {
        Write-Host "[DEV] Opening shell in container..." -ForegroundColor Cyan
        docker-compose -f $ComposeFile exec web bash
    }
    default {
        Write-Host "[DEV] Building and starting (foreground)..." -ForegroundColor Cyan
        docker-compose -f $ComposeFile up --build
    }
}
