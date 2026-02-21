# Guía de Migraciones — Django

Explica qué son las migraciones, por qué `makemigrations` no está en el startup
del contenedor, y cómo gestionar el ciclo completo correctamente.

---

## El problema que viste

Al correr `docker-compose up`, el log dice:

```
[2/4] Running migrations...
  No migrations to apply.
  Your models in app(s): 'audit', 'users' have changes that are not yet
  reflected in a migration, and so won't be applied.
  Run 'manage.py makemigrations' to make new migrations, and then re-run
  'manage.py migrate' to apply them.
```

Esto pasa cuando **modificás un modelo pero no generaste el archivo de migración**
antes de commitear.

---

## `migrate` vs `makemigrations` — la diferencia clave

```
makemigrations          migrate
──────────────          ───────
Lee tus models.py   →   Lee los archivos de
y GENERA archivos       migración y los APLICA
.py en migrations/      en la base de datos

Acción de dev           Acción de infraestructura
Se commitea al repo     Corre en cada entorno (dev, prod, CI)
```

Dicho de otra forma:

- `makemigrations` es como hacer `git add` — preparás el cambio en código
- `migrate` es como hacer `git checkout` — aplicás los cambios al entorno

---

## ¿Por qué `makemigrations` NO está en el startup del contenedor?

El script `start_dev.sh` solo corre `migrate`, nunca `makemigrations`. Esto es correcto y deliberado por tres razones:

### 1. Genera archivos de código que deben vivir en el repo

```
apps/
└── users/
    └── migrations/
        ├── 0001_initial.py           ← generado con makemigrations
        ├── 0002_add_token_version.py ← generado con makemigrations
        └── 0003_alter_user.py        ← generado con makemigrations
```

Estos archivos son **código fuente**. Sin ellos, otro developer que clona el repo
no puede aplicar el historial de cambios del schema.

### 2. Corriendo en contenedor generaría migraciones con diferente estado

Si el contenedor corre `makemigrations` al arrancar y hay cambios no committeados,
genera una migración nueva **en cada máquina de cada developer**, produciendo
migraciones duplicadas o conflictivas en el repositorio.

### 3. En producción es directamente peligroso

```
CI/CD pipeline             Producción
──────────────             ──────────
git pull latest            git pull latest
docker build               docker build
migrate          ✅         migrate          ✅
makemigrations   ⛔         makemigrations   ⛔ ← genera schema distinto al dev
```

Un `makemigrations` automático en producción podría generar una migración vacía
o incorrecta e intentar aplicarla, corrompiendo el schema real.

---

## Flujo correcto cuando cambiás un modelo

### Paso a paso

```
┌─────────────────────────────────────────────────────────┐
│  1. Modificás models.py                                 │
│     (nuevo campo, nuevo model, cambio de tipo, índice)  │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  2. Generás la migración                                │
│                                                         │
│  Windows:  .\scripts\host\dev.ps1 -Mode migrate         │
│  Linux:    bash scripts/host/migrate.sh --make          │
│                                                         │
│  → Crea apps/<app>/migrations/000X_descripcion.py       │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  3. Revisás el archivo generado                         │
│                                                         │
│  - Verificá que la migración hace lo que esperás        │
│  - Nunca editarla manualmente salvo casos especiales    │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  4. Committeás la migración junto al modelo             │
│                                                         │
│  git add apps/<app>/migrations/                         │
│  git add apps/<app>/models.py                           │
│  git commit -m "feat(users): add token_version field"   │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  5. Cualquier entorno que haga `migrate` aplica el      │
│     cambio automáticamente al siguiente `up`            │
│                                                         │
│  dev  → start_dev.sh  lo aplica en el próximo `up`      │
│  CI   → start_test.sh lo aplica antes de correr tests   │
│  prod → start_prod.sh lo aplica en el próximo deploy    │
└─────────────────────────────────────────────────────────┘
```

---

## Comandos de referencia rápida

### Windows PowerShell (contenedor activo)

```powershell
# Generar + aplicar (flujo más común tras cambiar un modelo)
.\scripts\host\dev.ps1 -Mode migrate

# Ver estado actual de todas las migraciones
docker-compose -f docker-compose.dev.yaml exec web python manage.py showmigrations

# Crear superusuario (necesario una sola vez por entorno)
docker-compose -f docker-compose.dev.yaml exec web python manage.py createsuperuser
```

### Linux / macOS (bash)

```bash
# Generar + aplicar
bash scripts/host/migrate.sh --make

# Solo aplicar (después de git pull con migraciones nuevas)
bash scripts/host/migrate.sh

# Ver estado
bash scripts/host/migrate.sh --show
```

### Directo en el contenedor (cualquier OS)

```bash
docker-compose -f docker-compose.dev.yaml exec web python manage.py makemigrations
docker-compose -f docker-compose.dev.yaml exec web python manage.py migrate
docker-compose -f docker-compose.dev.yaml exec web python manage.py showmigrations
```

---

## Escenarios frecuentes

### "Modificué un modelo y el contenedor dice que hay cambios sin migrar"

```powershell
.\scripts\host\dev.ps1 -Mode migrate
git add apps/*/migrations/
git commit -m "feat: migration for ..."
```

### "Me bajé un PR y el startup dice que hay migraciones pendientes"

No hay nada que hacer — el startup ya tiene `migrate` automático. La próxima
vez que hagas `.\scripts\host\dev.ps1` las aplica solo.

Si el contenedor ya está corriendo:

```powershell
docker-compose -f docker-compose.dev.yaml exec web python manage.py migrate
```

### "Quiero ver qué migraciones están pendientes antes de aplicar"

```powershell
docker-compose -f docker-compose.dev.yaml exec web python manage.py showmigrations
# [ ] = pendiente     [X] = aplicada
```

### "Cree una migración vacía sin querer"

```bash
# Borrar el archivo generado
rm apps/<app>/migrations/000X_auto_YYYYMMDD.py

# Si ya la aplicaste, hacer rollback primero:
python manage.py migrate <app> <migration_anterior>
# Luego borrar el archivo
```

### "Dos developers generaron migraciones en la misma app al mismo tiempo"

Django detecta conflictos automáticamente al correr `migrate`. La solución es:

```bash
python manage.py makemigrations --merge
```

Esto genera una migración de merge que reconcilia ambas ramas. Committeala.

---

## Historial de migraciones del proyecto

| App | Migración | Qué hace |
|-----|-----------|----------|
| `users` | `0001_initial` | Crea tabla `users_user` |
| `users` | `0002_*` | Agrega campo `token_version` |
| `users` | `0003_*` | Ajuste de campos |
| `users` | `0004_alter_user_managers` | Registra `UserManager` personalizado (email como USERNAME_FIELD) |
| `audit` | `0001_initial` | Crea tabla `audit_auditlog` con índices |
| `audit` | `0002_rename_*_act_res_idx` | Renombra índice que superaba 30 caracteres (límite de Django) |
| `authorization` | `0001_initial` | Crea tablas `Role`, `Permission`, `UserRole`, `RolePermission` |
