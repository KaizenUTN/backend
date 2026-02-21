# API de Autenticación - Módulo Users

## Descripción General
API RESTful para autenticación de usuarios usando JWT (JSON Web Tokens) con Django REST Framework.

## Endpoints Disponibles

### 1. Registro de Usuario
**POST** `/api/auth/register/`

Crea un nuevo usuario en el sistema.

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePassword123!",
  "password_confirm": "SecurePassword123!"
}
```

**Response (201 Created):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "is_active": true,
    "created_at": "2025-02-17T20:00:00Z",
    "updated_at": "2025-02-17T20:00:00Z"
  }
}
```

**Errores Comunes:**
- `400 Bad Request`: Email o username ya existe, contraseñas no coinciden
- `400 Bad Request`: Contraseña no cumple requisitos de seguridad

---

### 2. Login
**POST** `/api/auth/login/`

Autentica un usuario y retorna tokens JWT.

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "is_active": true,
    "created_at": "2025-02-17T20:00:00Z",
    "updated_at": "2025-02-17T20:00:00Z"
  }
}
```

**Errores Comunes:**
- `400 Bad Request`: Email o contraseña incorrectos
- `400 Bad Request`: Usuario inactivo

---

### 3. Logout
**POST** `/api/auth/logout/`

Invalida el refresh token para cerrar sesión.

**Autenticación:** Requiere token Bearer en header

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "message": "Successfully logged out"
}
```

**Errores Comunes:**
- `400 Bad Request`: Token inválido o ya usado
- `401 Unauthorized`: Sin token de autenticación

---

### 4. Refresh Token
**POST** `/api/auth/refresh/`

Obtiene un nuevo access token usando el refresh token.

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Errores Comunes:**
- `401 Unauthorized`: Refresh token inválido o expirado

---

### 5. Perfil de Usuario
**GET** `/api/auth/profile/`

Obtiene información del usuario autenticado.

**Autenticación:** Requiere token Bearer en header

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Response (200 OK):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2025-02-17T20:00:00Z",
  "updated_at": "2025-02-17T20:00:00Z"
}
```

---

**PUT/PATCH** `/api/auth/profile/`

Actualiza información del usuario autenticado.

**Autenticación:** Requiere token Bearer en header

**Request Body (PATCH - parcial):**
```json
{
  "first_name": "Johnny",
  "last_name": "Doe"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "Johnny",
  "last_name": "Doe",
  "full_name": "Johnny Doe",
  "is_active": true,
  "created_at": "2025-02-17T20:00:00Z",
  "updated_at": "2025-02-17T20:45:00Z"
}
```

**Nota:** El campo `email` no puede ser modificado por seguridad.

---

### 6. Cambiar Contraseña
**POST** `/api/auth/change-password/`

Cambia la contraseña del usuario autenticado.

**Autenticación:** Requiere token Bearer en header

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Request Body:**
```json
{
  "old_password": "SecurePassword123!",
  "new_password": "NewSecurePassword456!",
  "new_password_confirm": "NewSecurePassword456!"
}
```

**Response (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

**Errores Comunes:**
- `400 Bad Request`: Contraseña antigua incorrecta
- `400 Bad Request`: Contraseñas nuevas no coinciden
- `400 Bad Request`: Nueva contraseña no cumple requisitos

---

## Configuración de Seguridad

### Tokens JWT
- **Access Token**: 10 minutos de duración
- **Refresh Token**: 7 días de duración
- **Blacklist**: Los refresh tokens se invalidan al hacer logout

### Password Hashing
- **Algoritmo**: Argon2 (más seguro que PBKDF2)
- **Validación**: Requisitos mínimos de Django

### CORS
- **Desarrollo**: Permite todos los orígenes
- **Producción**: Configurar `CORS_ALLOWED_ORIGINS` en `.env.prod`

---

## Ejemplos de Uso con cURL

### Registro
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "password": "SecurePassword123!",
    "password_confirm": "SecurePassword123!"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }'
```

### Obtener Perfil
```bash
curl -X GET http://localhost:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Actualizar Perfil
```bash
curl -X PATCH http://localhost:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Johnny"
  }'
```

### Cambiar Contraseña
```bash
curl -X POST http://localhost:8000/api/auth/change-password/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "SecurePassword123!",
    "new_password": "NewSecurePassword456!",
    "new_password_confirm": "NewSecurePassword456!"
  }'
```

### Refresh Token
```bash
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "YOUR_REFRESH_TOKEN"
  }'
```

### Logout
```bash
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "YOUR_REFRESH_TOKEN"
  }'
```

---

## Ejemplos con Python Requests

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Registro
response = requests.post(f"{BASE_URL}/auth/register/", json={
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "password": "SecurePassword123!",
    "password_confirm": "SecurePassword123!"
})
print(response.json())

# Login
response = requests.post(f"{BASE_URL}/auth/login/", json={
    "email": "john@example.com",
    "password": "SecurePassword123!"
})
tokens = response.json()
access_token = tokens['access']

# Obtener perfil
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(f"{BASE_URL}/auth/profile/", headers=headers)
print(response.json())

# Cambiar contraseña
response = requests.post(f"{BASE_URL}/auth/change-password/", 
    headers=headers,
    json={
        "old_password": "SecurePassword123!",
        "new_password": "NewSecurePassword456!",
        "new_password_confirm": "NewSecurePassword456!"
    }
)
print(response.json())
```

---

## Ejemplos con JavaScript (Fetch)

```javascript
const BASE_URL = 'http://localhost:8000/api';

// Registro
async function register() {
    const response = await fetch(`${BASE_URL}/auth/register/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: 'johndoe',
            email: 'john@example.com',
            first_name: 'John',
            last_name: 'Doe',
            password: 'SecurePassword123!',
            password_confirm: 'SecurePassword123!'
        })
    });
    return await response.json();
}

// Login
async function login(email, password) {
    const response = await fetch(`${BASE_URL}/auth/login/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password })
    });
    const data = await response.json();
    // Guardar tokens en localStorage
    localStorage.setItem('accessToken', data.access);
    localStorage.setItem('refreshToken', data.refresh);
    return data;
}

// Obtener perfil
async function getProfile() {
    const accessToken = localStorage.getItem('accessToken');
    const response = await fetch(`${BASE_URL}/auth/profile/`, {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    });
    return await response.json();
}

// Refresh token
async function refreshToken() {
    const refreshToken = localStorage.getItem('refreshToken');
    const response = await fetch(`${BASE_URL}/auth/refresh/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh: refreshToken })
    });
    const data = await response.json();
    localStorage.setItem('accessToken', data.access);
    return data;
}

// Logout
async function logout() {
    const accessToken = localStorage.getItem('accessToken');
    const refreshToken = localStorage.getItem('refreshToken');
    
    await fetch(`${BASE_URL}/auth/logout/`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh: refreshToken })
    });
    
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
}
```

---

## Estructura de Archivos

```
apps/users/
├── __init__.py
├── admin.py              # Configuración del admin de Django
├── apps.py               # Configuración de la app
├── authentication.py     # Clase de autenticación JWT personalizada
├── models.py            # Modelo User (email-based)
├── serializers.py       # Serializers para login, registro, etc.
├── services.py          # Servicios de negocio (vacío por ahora)
├── tests.py             # Tests unitarios
├── urls.py              # Rutas de la API
├── views.py             # Vistas de la API
└── migrations/
    ├── __init__.py
    └── 0001_initial.py  # Migración inicial del modelo User
```

---

## Testing

Para probar los endpoints, primero asegúrate de que los contenedores estén corriendo:

```bash
# Iniciar contenedores
docker-compose -f docker-compose.dev.yaml up -d

# Crear un superusuario (opcional)
docker-compose -f docker-compose.dev.yaml exec web python manage.py createsuperuser

# Acceder al admin de Django
# http://localhost:8000/admin/
```

---

## Próximos Pasos (Módulos Futuros)

Este módulo está diseñado SOLO para autenticación básica. En el futuro se pueden agregar:

1. **Autorización**: Sistema de permisos y roles
2. **OAuth2**: Login social (Google, Facebook, etc.)
3. **2FA**: Autenticación de dos factores
4. **Email Verification**: Verificación de email al registrarse
5. **Password Reset**: Recuperación de contraseña vía email
6. **Rate Limiting**: Límite de intentos de login
7. **Audit Log**: Registro de actividades de usuario
