# Scripts Internos — Referencia Técnica

Documentación detallada de cada script del proyecto, qué hace internamente y cuándo usarlo.

---

## Estructura

```
scripts/
├── container/          ← Se ejecutan DENTRO del contenedor Docker
│   ├── start_dev.sh
│   ├── start_prod.sh
│   └── start_test.sh
│
├── host/               ← Se ejecutan desde tu máquina (fuera de Docker)
│   ├── dev.sh / dev.ps1
│   ├── prod.sh / prod.ps1
│   ├── test.sh / test.ps1
│   └── migrate.sh
│
└── tools/              ← Utilidades sueltas
    └── test_auth_api.py
```

---

## `scripts/container/` — Entrypoints del contenedor

Estos scripts son el `command:` de cada servicio en el `docker-compose` correspondiente.
Docker los ejecuta automáticamente al hacer `up` — no se llaman manualmente.

---

### `start_dev.sh`

**Cuándo se ejecuta:** Lo lanza Docker al correr `docker-compose.dev.yaml`.

**Pasos internos:**

```
[1/4] Waiting for database...
```
- Loop `until pg_isready -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB`
- Reintenta cada 2 segundos hasta que PostgreSQL acepte conexiones
- Sin este paso Django fallaría al intentar conectarse antes de que la DB esté lista

```
[2/4] Running migrations...
```
- `python manage.py migrate --noinput`
- Aplica todas las migraciones pendientes de todos los módulos registrados en `INSTALLED_APPS`
- `--noinput` evita prompts interactivos (necesario en Docker)

```
[3/4] Seeding authorization roles & permissions...
```
- `python manage.py seed_authorization`
- Crea los roles `Operador` y `Administrador` si no existen
- Crea todos los permisos base (`usuarios.view`, `auditoria.view`, etc.)
- Es **idempotente**: si ya existen, no duplica ni falla

```
[4/4] Starting development server at 0.0.0.0:8000
```
- `exec python manage.py runserver 0.0.0.0:8000`
- `exec` reemplaza el proceso bash con el proceso Django (correcto para Docker)
- Escucha en `0.0.0.0` para ser accesible desde el host en `localhost:8000`
- **Solo para desarrollo** — no usar en producción

---

### `start_prod.sh`

**Cuándo se ejecuta:** Lo lanza Docker al correr `docker-compose.prod.yaml`.

**Pasos internos:**

```
[1/5] Waiting for database...
```
- Mismo loop de `pg_isready`

```
[2/5] Running migrations...
```
- `python manage.py migrate --noinput`

```
[3/5] Seeding authorization roles & permissions...
```
- `python manage.py seed_authorization` — igual que dev, idempotente

```
[4/5] Collecting static files...
```
- `python manage.py collectstatic --noinput`
- Copia CSS/JS/imágenes a `STATIC_ROOT` (`staticfiles/`)
- Sin este paso WhiteNoise no puede servir los archivos estáticos de Django Admin

```
[5/5] Starting Gunicorn...
```
- `exec gunicorn config.wsgi:application` con los flags:
  - `--bind 0.0.0.0:8000` — escucha en todas las interfaces
  - `--workers 3` — 3 procesos worker (regla: `2 * núcleos + 1`)
  - `--timeout 60` — mata un worker si no responde en 60s
  - `--access-logfile logs/access.log` — logs HTTP a archivo persistent
  - `--error-logfile logs/error.log` — logs de errores a archivo
  - `--log-level info`

> ⚠️ Gunicorn no sirve archivos estáticos. En producción real va Nginx como reverse proxy delante.

---

### `start_test.sh`

**Cuándo se ejecuta:** Lo lanza Docker al correr `docker-compose.test.yaml`, o directamente si tenés el venv activo.

**Pasos internos:**

```
Running test suite...
```
- `python -m pytest` con los flags:
  - `--ds=config.settings.test` — fuerza el settings de test (SQLite en memoria)
  - `--tb=short` — traceback corto al fallar (más legible en CI)
  - `-q` — output compacto
  - `--cov=apps` — mide cobertura solo del código propio (excluye librerías)
  - `--cov-report=html` — genera reporte visual en `htmlcov/index.html`
  - `--cov-report=term-missing` — muestra en terminal qué líneas exactas no están cubiertas

```
Coverage report: htmlcov/index.html
```
- El reporte HTML queda en `htmlcov/index.html` — abrilo en el browser para navegarlo

---

## `scripts/host/` — Scripts del desarrollador

Se ejecutan desde tu máquina (fuera del contenedor). Orquestan Docker Compose.

---

### `dev.sh` / `dev.ps1`

**Propósito:** Levantar o detener el entorno de desarrollo.

| Comando Linux | Comando Windows | Comportamiento |
|---|---|---|
| `bash scripts/host/dev.sh` | `.\scripts\host\dev.ps1` | Foreground — logs visibles en esta terminal |
| `bash scripts/host/dev.sh -d` | `.\scripts\host\dev.ps1 -Mode bg` | Background — libera la terminal |
| `bash scripts/host/dev.sh --down` | `.\scripts\host\dev.ps1 -Mode down` | Para y elimina los contenedores |

**Qué hace en cada modo:**

```bash
# Foreground (default)
docker-compose -f docker-compose.dev.yaml up --build

# Background (-d / bg)
docker-compose -f docker-compose.dev.yaml up --build -d

# Detener (--down / down)
docker-compose -f docker-compose.dev.yaml down
```

**Servicios que levanta:**
- `web` → Django en `localhost:8000`
- `db` → PostgreSQL en `localhost:5432`

---

### `prod.sh` / `prod.ps1`

**Propósito:** Levantar o gestionar el entorno de producción.

> ⚠️ Requiere que `.env.prod` exista antes de correr — el script falla con error claro si no está.

| Comando Linux | Comando Windows | Comportamiento |
|---|---|---|
| `bash scripts/host/prod.sh` | `.\scripts\host\prod.ps1` | Build + start en **background** |
| `bash scripts/host/prod.sh --down` | `.\scripts\host\prod.ps1 -Mode down` | Para y elimina contenedores |
| `bash scripts/host/prod.sh --logs` | `.\scripts\host\prod.ps1 -Mode logs` | Muestra logs en tiempo real |

**Diferencias clave con dev:**
- Usa `docker-compose.prod.yaml` con imagen multi-stage build (más liviana y segura)
- Gunicorn en lugar de `runserver`
- `collectstatic` automático en el arranque
- El código **no** se monta como volumen — la imagen es inmutable

---

### `test.sh` / `test.ps1`

**Propósito:** Correr la suite de tests completa, en local o en Docker.

| Comando Linux | Comando Windows | Comportamiento |
|---|---|---|
| `bash scripts/host/test.sh` | `.\scripts\host\test.ps1` | Tests locales (requiere venv activo) |
| `bash scripts/host/test.sh --docker` | `.\scripts\host\test.ps1 -Mode docker` | Tests dentro de contenedor Docker |
| `bash scripts/host/test.sh -k login` | `.\scripts\host\test.ps1 -Filter login` | Filtra tests por nombre (solo local) |

**Modo local — qué hace:**
```bash
export DJANGO_SETTINGS_MODULE=config.settings.test
python -m pytest \
  --ds=config.settings.test \
  --tb=short -q \
  --cov=apps \
  --cov-report=html \
  --cov-report=term-missing \
  "$@"   # pasa argumentos extra (ej: -k, -v, --no-cov)
```

**Modo Docker — qué hace:**
```bash
docker-compose -f docker-compose.test.yaml up --build --abort-on-container-exit
# Captura el exit code del contenedor
docker-compose -f docker-compose.test.yaml down
exit $EXIT_CODE   # 0 = todos pasan, 1 = alguno falla
```

> La DB de test es **SQLite en memoria** — no necesita Postgres corriendo.

---

### `migrate.sh`

**Propósito:** Ejecutar migraciones manualmente con el settings correcto.

**Uso:**
```bash
bash scripts/host/migrate.sh         # ambiente dev (default)
bash scripts/host/migrate.sh prod    # ambiente prod
bash scripts/host/migrate.sh test    # ambiente test
```

**Qué hace internamente:**
```bash
ENVIRONMENT=${1:-dev}
export DJANGO_SETTINGS_MODULE=config.settings.$ENVIRONMENT
python manage.py migrate
```

**Cuándo usarlo:**
- Después de crear o modificar un modelo (`makemigrations` + este script)
- Después de `git pull` con migraciones nuevas en el repo
- Sin necesidad de reiniciar el servidor (si ya está corriendo)

> Para correr `makemigrations` dentro del contenedor activo:
> ```bash
> docker-compose -f docker-compose.dev.yaml exec web python manage.py makemigrations
> ```

---

## `scripts/tools/` — Utilidades

### `test_auth_api.py`

**Propósito:** Smoke test manual del flujo completo de autenticación vía HTTP real.

**Cómo ejecutarlo:**
```bash
# Con el servidor corriendo en localhost:8000
python scripts/tools/test_auth_api.py
```

**Qué hace internamente, paso a paso:**

```
PASO 1: Registrar nuevo usuario
```
- `POST /api/auth/register/` con `test@example.com` / `TestPassword123!`
- Si el usuario ya existe (409), automáticamente intenta login con esas mismas credenciales

```
PASO 2: Obtener perfil de usuario
```
- `GET /api/auth/profile/` con el `access_token` obtenido en el paso anterior

```
PASO 3: Actualizar perfil
```
- `PATCH /api/auth/profile/` — cambia `first_name` y `last_name`

```
PASO 4: Cambiar contraseña
```
- `POST /api/auth/change-password/` — requiere la contraseña actual + nueva + confirmación

```
PASO 5: Refresh token
```
- `POST /api/auth/refresh/` — intercambia el `refresh_token` por un nuevo `access_token`
- Continúa el flujo con el nuevo token

```
PASO 6: Logout
```
- `POST /api/auth/logout/` — invalida el `refresh_token` en la blacklist

**Cuándo usarlo:**
- Después de un deploy para verificar que la API responde correctamente
- Para debuggear problemas de conectividad o configuración JWT
- Como smoke test rápido antes de correr la suite completa de pytest

---

## Orden de ejecución recomendado

### Primera vez (onboarding)

```bash
# 1. Configurar variables de entorno
cp .env.example .env.dev   # editar con tus valores

# 2. Levantar dev (migrate + seed automático incluidos)
.\scripts\host\dev.ps1           # Windows
bash scripts/host/dev.sh          # Linux/macOS

# 3. Verificar que el flujo de auth funciona
python scripts/tools/test_auth_api.py
```

### Flujo diario de desarrollo

```bash
# Levantar entorno
.\scripts\host\dev.ps1

# Después de modificar modelos: generar + aplicar migración
docker-compose -f docker-compose.dev.yaml exec web python manage.py makemigrations
bash scripts/host/migrate.sh

# Correr tests antes de hacer commit
.\scripts\host\test.ps1
```

### Antes de un PR

```bash
# Suite completa con cobertura
.\scripts\host\test.ps1

# Verificar que no hay errores de sistema
python manage.py check
```

### Deploy a producción

```bash
# Asegurarse de tener .env.prod
cp .env.example .env.prod   # configurar valores reales

# Build + start
bash scripts/host/prod.sh

# Ver logs para confirmar arranque correcto
bash scripts/host/prod.sh --logs
```

---

## Variables de entorno usadas por los scripts

| Variable | Usada en | Descripción | Default |
|----------|----------|-------------|---------|
| `POSTGRES_HOST` | `start_*.sh` | Host de PostgreSQL | `db` |
| `POSTGRES_PORT` | `start_*.sh` | Puerto de PostgreSQL | `5432` |
| `POSTGRES_USER` | `start_*.sh` | Usuario de PostgreSQL | `postgres` |
| `POSTGRES_DB` | `start_*.sh` | Nombre de la base de datos | `postgres` |
| `DJANGO_SETTINGS_MODULE` | todos | Settings a usar | `config.settings.dev` |
| `DJANGO_SECRET_KEY` | `start_prod.sh` | Clave secreta de Django | *(requerido en prod)* |
