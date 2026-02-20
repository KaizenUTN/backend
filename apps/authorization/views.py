"""
authorization.views
====================
Views del módulo RBAC.

Cada view documenta explícitamente:
  - Qué permiso(s) se requieren para acceder.
  - Qué retorna en cada caso (200 / 403 / 401).
  - El modelo de authorización aplicado (HasPermission / HasAnyPermission / HasAllPermissions).

Todas las views verifican permisos **consultando la base de datos en cada request**,
lo que garantiza que un cambio de rol surta efecto de forma inmediata sin renovar tokens.
"""

from __future__ import annotations

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers as s
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authorization.permissions import HasAllPermissions, HasAnyPermission, HasPermission
from apps.authorization.services import get_user_permissions

# ---------------------------------------------------------------------------
# Shared inline response schemas
# ---------------------------------------------------------------------------

_403_response = OpenApiResponse(
    description=(
        "**Permiso denegado (403).**\n\n"
        "El usuario está autenticado pero su rol no incluye el permiso requerido.\n\n"
        "Esto ocurre cuando:\n"
        "- El usuario no tiene rol asignado.\n"
        "- Su rol existe pero no tiene el permiso necesario.\n\n"
        "El rol se evalúa en tiempo real contra la base de datos; "
        "no se requiere rotación de tokens para que los cambios de rol surtan efecto."
    ),
    examples=[
        OpenApiExample(
            name="Sin permiso",
            value={"detail": "Permiso denegado. Se requiere: 'conciliacion.run'."},
            response_only=True,
        )
    ],
)

_401_response = OpenApiResponse(
    description=(
        "**No autenticado (401).**\n\n"
        "El header `Authorization: Bearer <access_token>` está ausente, "
        "mal formado o el token ha expirado.\n\n"
        "Renovar el token con `POST /api/auth/refresh/` y reintentar."
    ),
    examples=[
        OpenApiExample(
            name="Token ausente o expirado",
            value={"detail": "Authentication credentials were not provided."},
            response_only=True,
        )
    ],
)


# ---------------------------------------------------------------------------
# View 1 — Conciliación: ejecutar (permiso único, PROTECT)
# ---------------------------------------------------------------------------

class ConciliacionRunView(APIView):
    """
    Ejecutar proceso de conciliación.
    Requiere permiso: **conciliacion.run**
    """
    permission_classes = [IsAuthenticated, HasPermission("conciliacion.run")]

    @extend_schema(
        tags=["RBAC — Ejemplos de autorización"],
        summary="Ejecutar conciliación",
        description=(
            "Inicia el proceso de conciliación automática.\n\n"
            "### Autorización requerida\n"
            "| Permiso | Descripción |\n"
            "|---------|-------------|\n"
            "| `conciliacion.run` | Ejecutar el proceso de conciliación automática |\n\n"
            "### Roles que tienen este permiso (configuración inicial)\n"
            "| Rol | ¿Tiene acceso? |\n"
            "|-----|----------------|\n"
            "| Solo Lectura | ❌ No |\n"
            "| Analista | ✅ Sí |\n"
            "| Supervisor | ✅ Sí |\n"
            "| Administrador | ✅ Sí |\n\n"
            "### Mecanismo de validación\n"
            "1. El JWT del header `Authorization` identifica al usuario.\n"
            "2. `HasPermission('conciliacion.run')` consulta en DB: "
            "`user.role.permissions.filter(code='conciliacion.run').exists()`.\n"
            "3. Si el resultado es `False` → respuesta `403` inmediata, sin ejecutar el handler.\n\n"
            "> **Efecto inmediato de cambios de rol:** si el administrador cambia el rol "
            "del usuario en la base de datos, el nuevo permiso aplica en el siguiente request "
            "sin necesidad de renovar el JWT."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="ConciliacionRunResponse",
                    fields={"status": s.CharField(help_text="Estado del proceso iniciado.")},
                ),
                description="Proceso de conciliación iniciado correctamente.",
                examples=[
                    OpenApiExample(
                        name="Éxito",
                        value={"status": "conciliacion iniciada"},
                        response_only=True,
                    )
                ],
            ),
            401: _401_response,
            403: _403_response,
        },
    )
    def post(self, request: Request) -> Response:
        return Response({"status": "conciliacion iniciada"})


# ---------------------------------------------------------------------------
# View 2 — Conciliación: listar (solo lectura)
# ---------------------------------------------------------------------------

class ConciliacionDetailView(APIView):
    """
    Consultar estado de conciliaciones.
    Requiere permiso: **conciliacion.view**
    """
    permission_classes = [IsAuthenticated, HasPermission("conciliacion.view")]

    @extend_schema(
        tags=["RBAC — Ejemplos de autorización"],
        summary="Ver conciliaciones",
        description=(
            "Retorna la lista de conciliaciones del sistema.\n\n"
            "### Autorización requerida\n"
            "| Permiso | Descripción |\n"
            "|---------|-------------|\n"
            "| `conciliacion.view` | Ver resultados y estado de conciliaciones |\n\n"
            "### Roles que tienen este permiso\n"
            "| Rol | ¿Tiene acceso? |\n"
            "|-----|----------------|\n"
            "| Solo Lectura | ✅ Sí |\n"
            "| Analista | ✅ Sí |\n"
            "| Supervisor | ✅ Sí |\n"
            "| Administrador | ✅ Sí |\n\n"
            "Este endpoint es de **solo lectura**: no modifica estado. "
            "Disponible para todos los roles básicos del sistema."
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="ConciliacionListResponse",
                    fields={
                        "conciliaciones": s.ListField(
                            child=s.DictField(),
                            help_text="Lista de registros de conciliación.",
                        )
                    },
                ),
                description="Lista de conciliaciones.",
                examples=[
                    OpenApiExample(
                        name="Lista vacía",
                        value={"conciliaciones": []},
                        response_only=True,
                    )
                ],
            ),
            401: _401_response,
            403: _403_response,
        },
    )
    def get(self, request: Request) -> Response:
        return Response({"conciliaciones": []})


# ---------------------------------------------------------------------------
# View 3 — Dashboard (HasAnyPermission — OR)
# ---------------------------------------------------------------------------

class DashboardView(APIView):
    """
    Dashboard principal.
    Requiere: **dashboard.view** OR **admin.full**
    """
    permission_classes = [IsAuthenticated, HasAnyPermission("dashboard.view", "admin.full")]

    @extend_schema(
        tags=["RBAC — Ejemplos de autorización"],
        summary="Dashboard principal",
        description=(
            "Retorna los widgets del panel principal.\n\n"
            "### Autorización requerida — `HasAnyPermission` (lógica OR)\n"
            "El usuario necesita **al menos uno** de estos permisos:\n\n"
            "| Permiso | Descripción |\n"
            "|---------|-------------|\n"
            "| `dashboard.view` | Ver el panel de métricas principal |\n"
            "| `admin.full` | Acceso completo al panel de administración |\n\n"
            "### Roles que tienen acceso\n"
            "| Rol | `dashboard.view` | `admin.full` | ¿Acceso? |\n"
            "|-----|-----------------|--------------|----------|\n"
            "| Solo Lectura | ✅ | ❌ | ✅ |\n"
            "| Analista | ✅ | ❌ | ✅ |\n"
            "| Supervisor | ✅ | ❌ | ✅ |\n"
            "| Administrador | ✅ | ✅ | ✅ |\n\n"
            "### Cuándo usar `HasAnyPermission`\n"
            "Ideal para recursos compartidos entre distintos roles donde "
            "cada rol llega por un camino diferente de permisos. "
            "Evita duplicar lógica en múltiples roles."
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="DashboardResponse",
                    fields={
                        "widgets": s.ListField(
                            child=s.DictField(),
                            help_text="Lista de widgets del dashboard.",
                        )
                    },
                ),
                description="Widgets del dashboard.",
                examples=[
                    OpenApiExample(
                        name="Dashboard vacío",
                        value={"widgets": []},
                        response_only=True,
                    )
                ],
            ),
            401: _401_response,
            403: OpenApiResponse(
                description=(
                    "**Permiso denegado (403).**\n\n"
                    "El usuario no tiene ni `dashboard.view` ni `admin.full`."
                ),
                examples=[
                    OpenApiExample(
                        name="Sin permiso",
                        value={"detail": "Permiso denegado. No posee ninguno de los permisos requeridos."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def get(self, request: Request) -> Response:
        return Response({"widgets": []})


# ---------------------------------------------------------------------------
# View 4 — Admin Panel (HasAllPermissions — AND)
# ---------------------------------------------------------------------------

class AdminPanelView(APIView):
    """
    Panel de administración.
    Requiere: **admin.read** AND **admin.write**
    """
    permission_classes = [IsAuthenticated, HasAllPermissions("admin.read", "admin.write")]

    @extend_schema(
        tags=["RBAC — Ejemplos de autorización"],
        summary="Panel de administración",
        description=(
            "Accede al panel de administración avanzado.\n\n"
            "### Autorización requerida — `HasAllPermissions` (lógica AND)\n"
            "El usuario necesita **todos** estos permisos simultáneamente:\n\n"
            "| Permiso | Descripción |\n"
            "|---------|-------------|\n"
            "| `admin.read` | Leer configuración y estado del sistema |\n"
            "| `admin.write` | Modificar configuración del sistema |\n\n"
            "Si el usuario tiene solo uno de los dos, recibe `403`.\n\n"
            "### Cuándo usar `HasAllPermissions`\n"
            "Útil para operaciones críticas (entorno financiero) donde se quiere "
            "garantizar que el rol tenga capacidades completas antes de permitir acceso. "
            "Permite una granularidad máxima en la asignación de permisos por rol.\n\n"
            "> **Ejemplo:** un rol `Auditor` podría tener `admin.read` pero no `admin.write`, "
            "pudiendo ver la configuración sin modificarla."
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="AdminPanelResponse",
                    fields={"panel": s.CharField(help_text="Estado del panel.")},
                ),
                description="Acceso al panel concedido.",
                examples=[
                    OpenApiExample(
                        name="Acceso concedido",
                        value={"panel": "ok"},
                        response_only=True,
                    )
                ],
            ),
            401: _401_response,
            403: OpenApiResponse(
                description=(
                    "**Permiso denegado (403).**\n\n"
                    "El usuario no tiene `admin.read` o no tiene `admin.write` (o ninguno)."
                ),
                examples=[
                    OpenApiExample(
                        name="Sin permisos",
                        value={"detail": "Permiso denegado. No posee todos los permisos requeridos."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def get(self, request: Request) -> Response:
        return Response({"panel": "ok"})


# ---------------------------------------------------------------------------
# View 5 — Introspección: permisos del usuario actual
# ---------------------------------------------------------------------------

class MyPermissionsView(APIView):
    """
    Consultar los permisos del usuario autenticado.
    Requiere: autenticación (sin permiso específico adicional).
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["RBAC — Introspección"],
        summary="Mis permisos",
        description=(
            "Retorna el rol y la lista completa de permisos del usuario autenticado.\n\n"
            "### Uso típico\n"
            "El frontend puede llamar a este endpoint tras el login para conocer "
            "qué secciones mostrar/ocultar en la UI, sin necesidad de hacer múltiples "
            "requests de comprobación.\n\n"
            "### Datos retornados\n"
            "| Campo | Tipo | Descripción |\n"
            "|-------|------|-------------|\n"
            "| `role` | `string \\| null` | Nombre del rol asignado al usuario. `null` si no tiene rol. |\n"
            "| `permissions` | `string[]` | Lista de códigos de permiso del rol. |\n\n"
            "### Cómo se calculan\n"
            "`services.get_user_permissions(user)` consulta "
            "`user.role.permissions.values_list('code', flat=True)` directamente en DB.\n\n"
            "> Los permisos reflejan el estado actual del rol en base de datos. "
            "Si el administrador modifica el rol, la próxima llamada a este endpoint "
            "ya devuelve los permisos actualizados."
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="MyPermissionsResponse",
                    fields={
                        "role": s.CharField(
                            allow_null=True,
                            help_text=(
                                "Nombre del rol asignado. `null` si el usuario no tiene rol asignado."
                            ),
                        ),
                        "permissions": s.ListField(
                            child=s.CharField(),
                            help_text=(
                                "Lista de códigos de permiso del rol actual. "
                                "Lista vacía si el usuario no tiene rol."
                            ),
                        ),
                    },
                ),
                description="Rol y permisos del usuario autenticado.",
                examples=[
                    OpenApiExample(
                        name="Usuario Analista",
                        value={
                            "role": "Analista",
                            "permissions": [
                                "conciliacion.run",
                                "conciliacion.view",
                                "dashboard.view",
                                "reportes.view",
                            ],
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        name="Usuario Administrador",
                        value={
                            "role": "Administrador",
                            "permissions": [
                                "admin.full",
                                "conciliacion.export",
                                "conciliacion.run",
                                "conciliacion.view",
                                "dashboard.view",
                                "reportes.export",
                                "reportes.view",
                                "usuarios.create",
                                "usuarios.delete",
                                "usuarios.edit",
                                "usuarios.view",
                            ],
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        name="Usuario sin rol asignado",
                        value={"role": None, "permissions": []},
                        response_only=True,
                    ),
                ],
            ),
            401: _401_response,
        },
    )
    def get(self, request: Request) -> Response:
        permisos = get_user_permissions(request.user)
        role = getattr(request.user, "role", None)
        return Response({
            "role": str(role) if role else None,
            "permissions": permisos,
        })
