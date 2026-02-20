# ─────────────────────────────────────────────────────────────────
# test.ps1 — Ejecuta la suite de tests.
#
# Uso:
#   .\scripts\host\test.ps1                     # local (requiere venv activo)
#   .\scripts\host\test.ps1 -Mode docker        # dentro del contenedor Docker
#   .\scripts\host\test.ps1 -Filter test_login  # filtra tests por nombre (local)
#
# El entorno de tests usa SQLite en memoria; no necesita DB externa.
# ─────────────────────────────────────────────────────────────────
param(
    [ValidateSet("local", "docker")]
    [string]$Mode = "local",

    [string]$Filter = ""
)

$ComposeFile = "docker-compose.test.yaml"

if ($Mode -eq "docker") {
    Write-Host "[TEST] Running tests in Docker..." -ForegroundColor Cyan
    docker-compose -f $ComposeFile up --build --abort-on-container-exit
    $exitCode = docker inspect django_test --format='{{.State.ExitCode}}' 2>$null
    docker-compose -f $ComposeFile down
    Write-Host ""
    if ($exitCode -eq "0") {
        Write-Host "All tests passed ✓" -ForegroundColor Green
    } else {
        Write-Host "Tests failed ✗" -ForegroundColor Red
    }
    exit [int]$exitCode
} else {
    Write-Host "[TEST] Running tests locally..." -ForegroundColor Cyan
    $env:DJANGO_SETTINGS_MODULE = "config.settings.test"

    $args = @(
        "-m", "pytest",
        "--ds=config.settings.test",
        "--tb=short",
        "-q",
        "--cov=apps",
        "--cov-report=html",
        "--cov-report=term-missing"
    )
    if ($Filter) { $args += "-k"; $args += $Filter }

    python @args
}
