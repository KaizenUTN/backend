# Backend API

API REST modular construida con Django 6 y Django REST Framework. Orientada a entornos semi-críticos donde la separación de responsabilidades, la trazabilidad y la cobertura de tests son requisitos, no opcionales.

---

## Índice

1. [Descripción del Proyecto](#1-descripción-del-proyecto)
2. [Requisitos](#2-requisitos)
3. [Arquitectura General](#3-arquitectura-general)
4. [Entornos](#4-entornos)
5. [Levantar el entorno de desarrollo](#5-levantar-el-entorno-de-desarrollo)
6. [Base de Datos](#6-base-de-datos)
7. [Testing](#7-testing)
8. [Estructura del Proyecto](#8-estructura-del-proyecto)
9. [Buenas Prácticas](#9-buenas-prácticas)
10. [Flujo de Desarrollo](#10-flujo-de-desarrollo)
11. [Variables de Entorno](#11-variables-de-entorno)
12. [Producción](#12-producción)

---

## 1. Descripción del Proyecto

Backend API REST con autenticación JWT, control de acceso basado en roles (RBAC), administración de usuarios y auditoría extensible.

**Stack técnico:**

| Componente | Tecnología |
|-----------|------------|
| Lenguaje | Python 3.12 |
| Framework | Django 6.0 + DRF 3.16 |
| Autenticación | SimpleJWT + Argon2 |
| Base de datos | PostgreSQL 16 |
| Contenedores | Docker + Docker Compose |
| Tests | pytest + pytest-cov |
| Documentación | drf-spectacular (OpenAPI 3) |
| Filtros | django-filter |

**Principios de diseño:**

- **Modular**: cada dominio de negocio es una app Django independiente.
- **Desacoplado**: `users` (identity) no importa desde `authorization`; la dependencia va en la dirección contraria.
- **Thin views**: las vistas solo validan y delegan. Toda la lógica vive en `services.py`.
- **Separación lectura/escritura**: `selectors.py` para queries, `services.py` para mutaciones.
- **Fail-closed**: cualquier decisión de autorización no resuelta devuelve `403`.

---

## 2. Requisitos

> ⚠️ Este proyecto **requiere Docker**. No se soporta ejecución directa con `python manage.py runserver` fuera de Docker para entornos compartidos.

| Herramienta | Versión mínima |
|-------------|---------------|
| Docker | 24+ |
| Docker Compose | v2 (incluido en Docker Desktop) |
| Git | cualquier versión reciente |

No se requiere Python, pip ni PostgreSQL instalados localmente. Todo corre dentro del contenedor.

---

## 3. Arquitectura General

### Separación por módulos

```
apps/
├── users/          Identity — autenticación, perfil, JWT, admin de usuarios
├── authorization/  RBAC — roles, permisos, guards DRF
├── audit/          Auditoría — registro inmutable de eventos del sistema
└── playground/     Endpoints de prueba para validar RBAC
```

Cada módulo sigue la misma estructura interna:

```
<módulo>/
├── models.py       Modelo de datos
├── serializers.py  Validación de entrada y salida (sin lógica de negocio)
├── services.py     Lógica de negocio (@transaction.atomic donde corresponde)
├── selectors.py    Consultas de lectura (sin mutaciones, select_related)
├── views.py        Thin views — validan, llaman al servicio, devuelven respuesta
├── urls.py         Rutas
├── filters.py      FilterSets (django-filter)
├── permissions.py  Guards DRF personalizados
└── tests/
    ├── unit/       Tests de modelos, serializers, services, selectors
    ├── api/        Tests de endpoints HTTP
    └── factories/  Factories (factory_boy) para fixtures reutilizables
```

### Separación de capas

```
Request → View → Serializer (validación) → Service (lógica) → DB
                                          → Selector (lectura)
Response ← View ← Serializer (output) ← Service/Selector
```

Las vistas **no** toman decisiones de negocio. Los servicios **no** conocen HTTP.

---

## 4. Entornos

| Entorno | Compose file | Settings | Uso |
|---------|-------------|----------|-----|
| `dev` | `docker-compose.dev.yaml` | `config.settings.dev` | Desarrollo local con hot-reload |
| `test` | `docker-compose.test.yaml` | `config.settings.test` | Suite pytest aislada |
| `prod` | `docker-compose.prod.yaml` | `config.settings.prod` | Imagen optimizada, Gunicorn |

Cada entorno tiene su propio archivo `.env`:

```
.env.dev    # desarrollo local
.env.test   # suite de tests
.env.prod   # producción (nunca al repositorio)
```

Los settings heredan de `config/settings/base.py` y sobreescriben solo lo necesario.

---

## 5. Levantar el entorno de desarrollo

### Usando el script helper (recomendado)

```powershell
# Windows
.\scripts\host\dev.ps1

# En background
.\scripts\host\dev.ps1 -Mode bg
```

```bash
# Linux / macOS / CI
bash scripts/host/dev.sh

# En background
bash scripts/host/dev.sh -d
```

### Directamente con Docker Compose

```bash
docker compose -f docker-compose.dev.yaml up --build
```

**Servicios que se levantan:**

| Servicio | Descripción | Puerto |
|----------|-------------|--------|
| `web` | Django dev server | `8000` |
| `db` | PostgreSQL 16 | `5433` (externo) |

El entrypoint del contenedor (`scripts/container/start_dev.sh`) ejecuta automáticamente:
1. Espera a que PostgreSQL esté listo
2. `migrate`
3. `seed` de roles y permisos
4. `runserver 0.0.0.0:8000`

**Verificar que funciona:**

```bash
curl http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123"}'
```

**Documentación interactiva (Swagger):**

```
http://localhost:8000/api/docs/      # Swagger UI
http://localhost:8000/api/redoc/     # ReDoc
http://localhost:8000/api/schema/    # OpenAPI 3 en JSON/YAML
```

---

## 6. Base de Datos

### Migraciones

Las migraciones se ejecutan automáticamente al levantar el entorno. Para correrlas manualmente:

```bash
# Dentro del contenedor
docker compose -f docker-compose.dev.yaml exec web python manage.py migrate

# Crear nueva migración
docker compose -f docker-compose.dev.yaml exec web python manage.py makemigrations
```

### Seed de datos iniciales

El seed crea los roles (`Operador`, `Administrador`) y sus permisos base:

```bash
docker compose -f docker-compose.dev.yaml exec web \
  python manage.py seed_authorization
```

### Acceso directo a la DB

```bash
docker compose -f docker-compose.dev.yaml exec db \
  psql -U dev_user -d db_dev
```

---

## 7. Testing

### Ejecutar la suite

```powershell
# Windows
.\scripts\host\test.ps1

# En Docker
.\scripts\host\test.ps1 -Mode docker
```

```bash
# Linux / macOS / CI
bash scripts/host/test.sh

# En Docker
bash scripts/host/test.sh --docker
```

### Configuración de pytest

El proyecto usa `pytest.ini` con las siguientes opciones activadas por defecto:

```ini
addopts =
    --nomigrations          # DB de test sin migraciones (más rápido)
    --cov=apps              # cobertura de toda la carpeta apps/
    --cov-report=html       # reporte HTML en htmlcov/
    --cov-report=term-missing
    --strict-markers        # falla si se usa un marker no declarado
    -ra                     # muestra razón de cada fallo/skip
```

### Markers disponibles

```bash
pytest -m unit          # solo tests unitarios
pytest -m api           # solo tests de endpoints
pytest -m integration   # solo tests de integración
pytest -m "unit and not slow"
```

### Ejemplo de reporte de cobertura

```
Name                               Stmts   Miss  Cover   Missing
----------------------------------------------------------------
apps/users/models.py                  20      0   100%
apps/users/services.py                57      2    96%   39-40
apps/users/selectors.py                7      0   100%
apps/users/filters.py                 10      0   100%
apps/users/views.py                  166      6    96%
apps/audit/models.py                  30      0   100%
apps/audit/services.py                45      0   100%
apps/audit/selectors.py               10      0   100%
apps/audit/views.py                   55      2    96%
----------------------------------------------------------------
TOTAL                                810    130    84%
```

**La cobertura de código es obligatoria.** Todo código nuevo debe incluir tests.

---

## 8. Estructura del Proyecto

```
.
├── apps/
│   ├── users/                  Identity, autenticación JWT, admin de usuarios
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── filters.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── authentication.py   CustomJWTAuthentication (valida token_version)
│   │   └── tests/
│   │       ├── unit/
│   │       ├── api/
│   │       └── factories/
│   ├── authorization/          RBAC — roles, permisos, guards
│   │   ├── models.py           Role, Permission
│   │   ├── services.py         user_has_permission()
│   │   ├── permissions.py      HasPermission (factory DRF)
│   │   └── management/
│   │       └── commands/
│   │           └── seed_authorization.py
│   ├── audit/                  Auditoría extensible (OCP)
│   │   ├── models.py           BaseAuditLog (abstract) + AuditLog
│   │   ├── services.py         log_action() / log_failure() — fail-silent
│   │   ├── selectors.py        Consultas de lectura
│   │   ├── serializers.py      AuditLogSerializer (solo lectura)
│   │   ├── filters.py          Filtros: action, resource, status, user_id, fecha, correlation_id
│   │   ├── views.py            AuditLogListView / AuditLogDetailView
│   │   ├── urls.py             GET /api/audit/logs/ + GET /api/audit/logs/{id}/
│   │   └── tests/
│   │       ├── unit/           test_models.py, test_services.py
│   │       └── api/            test_audit_logs.py
│   └── playground/             Endpoints de ejemplo para validar RBAC
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   ├── test.py
│   │   └── prod.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── scripts/
│   ├── container/              Entrypoints que corren dentro de Docker
│   │   ├── start_dev.sh
│   │   ├── start_prod.sh
│   │   └── start_test.sh
│   ├── host/                   Scripts ejecutados desde la máquina host
│   │   ├── dev.sh / dev.ps1
│   │   ├── test.sh / test.ps1
│   │   └── prod.sh / prod.ps1
│   └── tools/
├── docs/                       Documentación técnica de módulos y endpoints
│   └── scripts/                Referencia técnica y guías de scripts
│       ├── scripts-internos.md
│       └── guia-migraciones.md
├── postman/                    Colección Postman lista para importar
├── docker-compose.dev.yaml
├── docker-compose.test.yaml
├── docker-compose.prod.yaml
├── Dockerfile.dev
├── Dockerfile.prod
├── requirements.txt
└── pytest.ini
```

---

## 9. Buenas Prácticas

### Sin lógica en views

Las vistas validan la request con un serializer y delegan al servicio. No toman decisiones de negocio.

```python
# ✅ correcto
def post(self, request: Request) -> Response:
    serializer = AdminCreateUserSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    user = create_user(**serializer.validated_data)
    return Response(AdminUserSerializer(user).data, status=201)

# ❌ incorrecto — lógica de negocio en la vista
def post(self, request: Request) -> Response:
    if User.objects.filter(email=request.data['email']).exists():
        ...
```

### Services atómicos

Toda mutación que toque más de una tabla o estado usa `@transaction.atomic`.

```python
@transaction.atomic
def deactivate_user(*, user: User) -> User:
    user.is_active = False
    user.token_version += 1
    user.save(update_fields=['is_active', 'token_version', 'updated_at'])
    return user
```

### Separación lectura / escritura

- `selectors.py` — solo queries, `select_related` para evitar N+1, sin efectos secundarios.
- `services.py` — solo mutaciones, siempre `@transaction.atomic` si hay riesgo de inconsistencia.

### No mezclar Identity con Authorization

`apps/users` no importa desde `apps.authorization`. La dependencia va en una sola dirección:

```
authorization → users   ✅
users → authorization   ❌  (solo lazy import permitido para asignar rol en registro)
```

### Invalidación de tokens sin blacklist completa

El modelo `User` tiene un campo `token_version`. `CustomJWTAuthentication` valida que el valor en el payload del token coincida con el de la DB. Al desactivar un usuario o resetear su contraseña, `token_version` se incrementa, invalidando todos sus JWTs activos de forma inmediata.

---

## 10. Flujo de Desarrollo

```bash
# 1. Crear rama desde main
git checkout main && git pull
git checkout -b feature/nombre-de-la-feature

# 2. Levantar entorno de desarrollo
.\scripts\host\dev.ps1        # Windows
bash scripts/host/dev.sh      # Linux

# 3. Escribir tests primero (TDD recomendado)
# apps/<módulo>/tests/unit/test_<componente>.py
# apps/<módulo>/tests/api/test_<endpoint>.py

# 4. Implementar la feature

# 5. Verificar cobertura
.\scripts\host\test.ps1
# o
bash scripts/host/test.sh

# 6. Confirmar que el total de tests pasa
python -m pytest --no-cov -q

# 7. Crear Pull Request hacia main
```

**Criterios de merge:**

- Todos los tests pasan.
- La cobertura del módulo modificado no baja.
- No hay lógica de negocio en views ni serializers.
- Los nuevos endpoints tienen `@extend_schema` completo (Swagger).

---

## 11. Variables de Entorno

Cada archivo `.env.*` se mapea al entorno correspondiente. **Nunca subir archivos `.env` con credenciales reales al repositorio.**

### `.env.dev` — ejemplo

```env
# Django
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=dev-secret-key-change-in-prod
DEBUG=True

# PostgreSQL
USE_POSTGRES=True
POSTGRES_DB=db_dev
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_password
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

### `.env.prod` — variables requeridas

```env
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=<clave-larga-y-aleatoria>
DEBUG=False
ALLOWED_HOSTS=api.tudominio.com
USE_POSTGRES=True
POSTGRES_DB=db_prod
POSTGRES_USER=prod_user
POSTGRES_PASSWORD=<contraseña-segura>
POSTGRES_HOST=db
POSTGRES_PORT=5432
CORS_ALLOWED_ORIGINS=https://app.tudominio.com
```

> Generar `SECRET_KEY` segura:
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

---

## 12. Producción

### Diferencias con desarrollo

| Aspecto | Dev | Prod |
|---------|-----|------|
| Servidor | `runserver` | Gunicorn |
| `DEBUG` | `True` | `False` |
| Archivos estáticos | Servidos por Django | WhiteNoise / nginx |
| Base de datos | Volumen local | Instancia gestionada |
| Imagen Docker | `Dockerfile.dev` | `Dockerfile.prod` |

### Levantar producción

```bash
# Windows
.\scripts\host\prod.ps1

# Linux
bash scripts/host/prod.sh
```

O directamente:

```bash
docker compose -f docker-compose.prod.yaml up --build -d
```

El entrypoint de producción (`scripts/container/start_prod.sh`) ejecuta `collectstatic` automáticamente antes de iniciar Gunicorn.

> ⚠️ En producción, colocar un reverse proxy (nginx, Caddy) delante de Gunicorn para TLS y compresión.

---

## Documentación adicional

| Documento | Contenido |
|-----------|-----------|
| [`docs/product-overview.md`](docs/product-overview.md) | **Visión general del producto** — qué hace la plataforma, sin tecnicismos |
| [`docs/authentication-api.md`](docs/authentication-api.md) | Endpoints de autenticación JWT |
| [`docs/users-admin-api.md`](docs/users-admin-api.md) | Panel de administración de usuarios |
| [`docs/authentication-module-summary.md`](docs/authentication-module-summary.md) | Estado del módulo users |
| [`docs/frontend-integration-guide.md`](docs/frontend-integration-guide.md) | Guía de integración para frontend |
| [`docs/scripts/scripts-internos.md`](docs/scripts/scripts-internos.md) | Referencia técnica de todos los scripts del proyecto |



## 🚀 Inicio Rápido

### Opción 1: Local (sin Docker)

```bash
# Clonar el repositorio
git clone <your-repo-url>
cd Cliente

# Crear y activar ambiente virtual
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# source venv/bin/activate    # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env.dev

# Ejecutar migraciones
python manage.py migrate --settings=config.settings.dev

# Crear superusuario
python manage.py createsuperuser --settings=config.settings.dev

# Iniciar servidor
python manage.py runserver --settings=config.settings.dev
```

### Opción 2: Con Docker

```bash
# Desarrollo
docker-compose -f docker-compose.dev.yaml up --build

# Testing
docker-compose -f docker-compose.test.yaml up --build

# Producción
docker-compose -f docker-compose.prod.yaml up -d --build
```


