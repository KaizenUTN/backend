# Plataforma Backend — Visión General del Producto

## ¿Qué es esta plataforma?

Es un backend de gestión de usuarios, accesos y trazabilidad diseñado para servir como núcleo de autenticación y control de cualquier aplicación web o móvil.

Expone una **API REST** segura que el frontend (o cualquier cliente HTTP) consume para registrar usuarios, gestionar sesiones, administrar el equipo y auditar cada acción relevante del sistema.

---

## ¿Qué puede hacer?

### Autenticación de usuarios

Los usuarios acceden a la plataforma con **email y contraseña**. Al ingresar reciben un par de tokens seguros (estándar JWT) que el cliente utiliza para autenticar todas las peticiones siguientes.

- Registro de cuenta nueva con validación de contraseña segura
- Inicio y cierre de sesión
- Renovación automática de sesión sin volver a ingresar credenciales
- Actualización de perfil (nombre, apellido)
- Cambio de contraseña desde el perfil del usuario

### Cierre de sesión forzado e invalidación de tokens

Cuando un administrador desactiva una cuenta o resetea su contraseña, **todos los dispositivos de ese usuario quedan desconectados de forma inmediata**, sin esperar a que los tokens expiren naturalmente. Esto garantiza que una cuenta comprometida o desvinculada no pueda seguir operando.

### Política de contraseñas

Las contraseñas son validadas automáticamente al registrarse o cambiarlas:

- Mínimo 10 caracteres
- Debe incluir mayúsculas, minúsculas, números y caracteres especiales
- No puede ser demasiado similar al nombre o email del usuario
- No puede ser una contraseña genérica conocida

Los hashes son generados con **Argon2**, el algoritmo ganador de la Password Hashing Competition, considerado el más seguro disponible actualmente.

---

## Panel de administración de usuarios

Un usuario con los permisos adecuados puede gestionar el equipo completo desde la API:

| Acción | Descripción |
|--------|-------------|
| **Listar usuarios** | Vista paginada con filtros por nombre, email, rol y estado |
| **Crear usuario** | Alta con asignación de rol y estado inicial |
| **Editar usuario** | Actualización de nombre, apellido y rol |
| **Desactivar usuario** | Baja lógica — la cuenta queda en el sistema pero sin acceso |
| **Resetear contraseña** | Genera una contraseña temporal segura para entregarle al usuario |

Toda búsqueda soporta filtrado, ordenamiento y paginación para trabajar cómodamente con equipos de cualquier tamaño.

---

## Control de acceso por roles (RBAC)

Cada usuario pertenece a un **rol** que define exactamente qué puede hacer dentro del sistema. Los permisos se evalúan en tiempo real: cambiar el rol de un usuario tiene efecto inmediato en la próxima petición, sin necesidad de que vuelva a iniciar sesión.

Los roles y permisos base incluidos son:

| Rol | Descripción |
|-----|-------------|
| **Administrador** | Acceso completo a gestión de usuarios y auditoría |
| **Operador** | Acceso operativo restringido según los permisos asignados |

Los permisos son granulares por operación (`usuarios.view`, `usuarios.create`, `usuarios.edit`, `usuarios.delete`) y el sistema está diseñado para que agregar nuevos roles o permisos no requiera cambios en la lógica de negocio.

---

## Auditoría del sistema

**Cada acción relevante queda registrada** con quién la realizó, cuándo, sobre qué recurso y con qué resultado. El registro es inmutable y está disponible para consulta con filtros avanzados.

### Eventos que se registran automáticamente

| Evento | Descripción |
|--------|-------------|
| Inicio de sesión exitoso | Usuario, fecha y hora |
| Intento de inicio de sesión fallido | Email utilizado y motivo |
| Registro de cuenta nueva | Datos del usuario creado |
| Cierre de sesión | Usuario y fecha |
| Cambio de contraseña | Usuario (sin registrar la contraseña) |
| Actualización de perfil | Campos modificados |
| Creación de usuario por admin | Actor, usuario creado y email |
| Edición de usuario por admin | Actor y usuario modificado |
| Desactivación de cuenta | Actor y usuario afectado |
| Reset de contraseña por admin | Actor y usuario afectado |

### Consulta del log de auditoría

El historial es consultable vía API con los siguientes filtros:

| Filtro | Opciones |
|--------|----------|
| Tipo de evento | login, registro, baja, etc. |
| Resultado | exitoso / fallido |
| Usuario | por ID |
| Recurso | user, session, etc. |
| Rango de fechas | desde / hasta |
| Correlation ID | para rastrear operaciones compuestas |

La paginación y el ordenamiento están disponibles en todos los listados.

---

## Documentación interactiva

La API incluye documentación **Swagger UI** y **ReDoc** generada automáticamente a partir del código. Cualquier desarrollador frontend puede explorar todos los endpoints, ver qué parámetros acepta cada uno y probar peticiones directamente desde el navegador.

| Interfaz | URL |
|----------|-----|
| Swagger UI | `http://[host]/api/docs/` |
| ReDoc | `http://[host]/api/redoc/` |
| Esquema OpenAPI (JSON/YAML) | `http://[host]/api/schema/` |

---

## Seguridad técnica destacada

- **JWT con expiración corta**: los tokens de acceso tienen vida útil de 60 minutos; los de refresco, 7 días.
- **Blacklist de tokens**: al cerrar sesión el token queda invalidado aunque no haya expirado.
- **Token version**: mecanismo propio que permite invalidar todos los dispositivos de un usuario al instante.
- **HTTPS-ready**: la configuración de producción está preparada para operar detrás de un reverse proxy con TLS.
- **CORS configurable**: los orígenes permitidos se definen por variable de entorno, separando correctamente los entornos de desarrollo, testing y producción.
- **Contraseñas nunca almacenadas en claro**: Argon2 con salting automático.
- **Auditoría fail-silent**: un error al escribir un log de auditoría nunca interrumpe la operación de negocio.

---

## Entornos disponibles

| Entorno | Propósito |
|---------|-----------|
| **Desarrollo** | Servidor con hot-reload, ideal para iterar rápido |
| **Testing** | Suite de tests aislada con base de datos independiente |
| **Producción** | Servidor Gunicorn optimizado, sin modo debug |

Cada entorno tiene su propia configuración, base de datos y variables de entorno. El despliegue completo está containerizado con Docker.

---

## Cobertura de tests

El proyecto incluye una suite de tests automatizados que cubre modelos, servicios, endpoints y casos de error. Los tests corren en un entorno aislado y se ejecutan con un solo comando.

> **287 tests — todos pasando.**

---

## Módulos del sistema

| Módulo | Responsabilidad |
|--------|----------------|
| **users** | Identidad, autenticación JWT, perfil y administración de cuentas |
| **authorization** | Roles, permisos y control de acceso |
| **audit** | Registro inmutable de eventos del sistema |

Los módulos están diseñados para ser independientes entre sí, lo que facilita agregar funcionalidad (pagos, reportes, notificaciones) sin afectar lo ya construido.
