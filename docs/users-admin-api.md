# API de Administración de Usuarios

## Descripción General

Endpoints para la gestión administrativa de usuarios. Permiten listar, crear, editar, desactivar y resetear contraseñas desde el panel de administración.

Todos los endpoints requieren **autenticación JWT** y el **permiso RBAC** específico de cada operación.

---

## Seguridad

| Operación | Permiso requerido |
|-----------|------------------|
| Listar / Ver | `usuarios.view` |
| Crear | `usuarios.create` |
| Editar | `usuarios.edit` |
| Desactivar | `usuarios.delete` |
| Reset contraseña | `usuarios.edit` |

Los permisos se consultan en DB en cada request — cambiar el rol de un usuario surte efecto inmediato sin renovar tokens.

---

## Endpoints

### 1. Listar usuarios

**GET** `/api/users/`

Retorna la lista paginada de todos los usuarios del sistema.

**Query parameters:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `email` | string | Búsqueda parcial (case-insensitive) |
| `role` | integer | ID exacto del rol |
| `is_active` | boolean | `true` / `false` |
| `search` | string | Búsqueda en email, nombre y apellido |
| `ordering` | string | `created_at`, `-created_at`, `email`, `last_name` |
| `page` | integer | Número de página (tamaño: 10) |

**Ejemplo de request:**
```
GET /api/users/?is_active=true&ordering=-created_at&page=1
Authorization: Bearer <access_token>
```

**Response 200:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 5,
      "email": "maria@empresa.com",
      "first_name": "María",
      "last_name": "González",
      "full_name": "María González",
      "role": 1,
      "role_name": "Operador",
      "is_active": true,
      "created_at": "2025-06-01T12:00:00Z",
      "updated_at": "2025-06-01T12:00:00Z"
    }
  ]
}
```

**Errores:**
- `401` — Sin token o token inválido
- `403` — Sin permiso `usuarios.view`

---

### 2. Crear usuario

**POST** `/api/users/`

Crea un nuevo usuario desde el panel de administración. A diferencia del registro público, permite asignar rol y estado inicial.

**Request Body:**
```json
{
  "email": "maria@empresa.com",
  "first_name": "María",
  "last_name": "González",
  "password": "SecurePass123!",
  "role_id": 1,
  "is_active": true
}
```

**Campos:**
| Campo | Requerido | Descripción |
|-------|-----------|-------------|
| `email` | ✅ | Debe ser único en el sistema |
| `first_name` | ✅ | Nombre |
| `last_name` | ✅ | Apellido |
| `password` | ✅ | Debe cumplir políticas de seguridad de Django |
| `role_id` | ❌ | ID del rol. Si se omite el usuario queda sin rol |
| `is_active` | ❌ | Default `true` |

**Response 201:**
```json
{
  "id": 5,
  "email": "maria@empresa.com",
  "first_name": "María",
  "last_name": "González",
  "full_name": "María González",
  "role": 1,
  "role_name": "Operador",
  "is_active": true,
  "created_at": "2025-06-01T12:00:00Z",
  "updated_at": "2025-06-01T12:00:00Z"
}
```

**Errores:**
- `400` — Email ya existe, contraseña débil, campo requerido faltante
- `401` / `403` — Sin autenticación o permiso

---

### 3. Obtener usuario por ID

**GET** `/api/users/{id}/`

Retorna los datos de un usuario específico.

**Response 200:**
```json
{
  "id": 5,
  "email": "maria@empresa.com",
  "first_name": "María",
  "last_name": "González",
  "full_name": "María González",
  "role": 1,
  "role_name": "Operador",
  "is_active": true,
  "created_at": "2025-06-01T12:00:00Z",
  "updated_at": "2025-06-01T12:00:00Z"
}
```

**Errores:**
- `404` — Usuario no encontrado
- `401` / `403` — Sin autenticación o permiso

---

### 4. Editar usuario

**PATCH** `/api/users/{id}/`

Actualiza datos administrativos de un usuario. Todos los campos son opcionales (semántica PATCH).

> Para cambiar contraseña usar `/reset-password/`.
> Para desactivar usar `/deactivate/`.

**Request Body (todos opcionales):**
```json
{
  "first_name": "NuevoNombre",
  "last_name": "NuevoApellido",
  "role_id": 2
}
```

**Response 200:** objeto usuario actualizado (mismo formato que GET).

**Errores:**
- `400` — Datos inválidos
- `404` — Usuario no encontrado
- `401` / `403` — Sin autenticación o permiso

---

### 5. Desactivar usuario

**POST** `/api/users/{id}/deactivate/`

Desactiva un usuario (soft delete — `is_active = false`). El usuario queda en DB y puede reactivarse desde el admin de Django.

Incrementa `token_version` para **invalidar inmediatamente** todos los JWTs activos del usuario sin esperar a que expiren.

**Response 200:**
```json
{
  "id": 5,
  "email": "maria@empresa.com",
  ...
  "is_active": false
}
```

**Errores:**
- `400` — El usuario ya está desactivado
- `404` — Usuario no encontrado
- `401` / `403` — Sin autenticación o permiso

---

### 6. Reset de contraseña

**POST** `/api/users/{id}/reset-password/`

Genera una contraseña temporal aleatoria (16 caracteres, criptográficamente segura) y la asigna al usuario.

Incrementa `token_version` para forzar re-login en todos los dispositivos activos del usuario.

> ⚠️ La contraseña temporal se retorna **una única vez** en la respuesta. El caller es responsable de comunicarla al usuario de forma segura.
>
> 📧 TODO: Integrar envío automático por email.

**Response 200:**
```json
{
  "temp_password": "aB3!kX9&mZ7@nQ2w",
  "user": {
    "id": 5,
    "email": "maria@empresa.com",
    ...
  }
}
```

**Errores:**
- `404` — Usuario no encontrado
- `401` / `403` — Sin autenticación o permiso

---

## Modelo de respuesta (`AdminUserSerializer`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | integer | PK del usuario |
| `email` | string | Email (único) |
| `first_name` | string | Nombre |
| `last_name` | string | Apellido |
| `full_name` | string | `first_name + last_name` (computed) |
| `role` | integer \| null | ID del rol asignado |
| `role_name` | string \| null | Nombre del rol (ej: "Operador") |
| `is_active` | boolean | Estado de la cuenta |
| `created_at` | datetime | ISO 8601 |
| `updated_at` | datetime | ISO 8601 |

---

## Arquitectura interna

```
views.py (thin)
  ├── serializers.py    — validación de request/response
  ├── selectors.py      — consultas de lectura (select_related)
  ├── services.py       — lógica de negocio (@transaction.atomic)
  └── filters.py        — UserFilter (django-filter)
```

### Invalidación de tokens (`token_version`)

Las operaciones `deactivate_user` y `reset_password` incrementan `token_version` en el modelo `User`. El backend valida este campo en cada request autenticado vía `CustomJWTAuthentication`, por lo que los JWTs emitidos antes del incremento son rechazados sin esperar a su expiración natural.

---

## Tests

| Archivo | Cobertura |
|---------|-----------|
| `apps/users/tests/unit/test_services.py` | `services.py` — create, update, deactivate, reset |
| `apps/users/tests/unit/test_selectors.py` | `selectors.py` — get_by_id, get_list, N+1 |
| `apps/users/tests/api/test_admin_users.py` | Todos los endpoints — auth, permisos, lógica |
