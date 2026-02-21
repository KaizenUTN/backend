"""
playground.views
================
Endpoints de prueba para validar el sistema de autenticación y autorización RBAC.

Este módulo es completamente independiente de `identity` y `authorization`.
Importa únicamente las clases de permiso del módulo authorization como consumidor.

Escenarios cubiertos
--------------------
A. Sin autenticación   → endpoints públicos, visibles para cualquiera
B. Solo autenticación  → requiere JWT válido, sin permiso adicional
C. HasPermission       → permiso único requerido (varios niveles de rol)
D. HasAnyPermission    → lógica OR entre dos permisos
E. HasAllPermissions   → lógica AND entre dos permisos
F. Introspección       → quién soy + qué puedo hacer
"""

from __future__ import annotations

from typing import Dict

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers as s
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authorization.permissions import HasAllPermissions, HasAnyPermission, HasPermission
from apps.authorization.services import get_user_permissions

# ---------------------------------------------------------------------------
# Shared response helpers
# ---------------------------------------------------------------------------

_401 = OpenApiResponse(
    description=(
        "**401 — No autenticado.**\n\n"
        "El header `Authorization` está ausente, mal formado o el access token expiró.\n\n"
        "**Solución:** hacer `POST /api/auth/login/`, copiar el campo `access` de la respuesta "
        "y enviarlo como `Authorization: Bearer <access_token>`."
    ),
    examples=[
        OpenApiExample(
            "Sin token",
            value={"detail": "Authentication credentials were not provided."},
            response_only=True,
        )
    ],
)

_403 = OpenApiResponse(
    description=(
        "**403 — Permiso denegado.**\n\n"
        "El usuario está autenticado (JWT válido) pero su rol no incluye el permiso requerido.\n\n"
        "El rol se consulta en DB en cada request. "
        "Cambiar el rol en el admin surte efecto inmediato."
    ),
    examples=[
        OpenApiExample(
            "Sin permiso",
            value={"detail": "Permiso denegado. Se requiere: 'X'."},
            response_only=True,
        )
    ],
)


def _ok(name: str, body: dict) -> OpenApiResponse:
    """Helper: crea un OpenApiResponse 200 con un ejemplo inline."""
    fields: Dict[str, s.Field] = {k: s.CharField() for k in body}
    return OpenApiResponse(
        response=inline_serializer(name=name, fields=fields),
        description="**200 — Acceso concedido.**",
        examples=[
            OpenApiExample("Respuesta exitosa", value=body, response_only=True)
        ],
    )


# ===========================================================================
# ESCENARIO A — Sin autenticación (endpoints públicos)
# ===========================================================================

class PublicView(APIView):
    """Endpoint completamente público, sin autenticación."""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Playground"],
        summary="Endpoint público (sin token)",
        description=(
            "Responde a **cualquier usuario**, autenticado o no.\n\n"
            "### ¿Qué demuestra?\n"
            "Que `permission_classes = [AllowAny]` desactiva por completo la verificación de identidad.\n\n"
            "### Cómo probarlo\n"
            "1. **Sin Bearer token** → debería retornar `200` ✅\n"
            "2. **Con un Bearer token válido** → también retorna `200` ✅\n"
            "3. **Con un token inválido/expirado** → también retorna `200` ✅ "
            "(AllowAny ignora el header Authorization completamente)\n\n"
            "### Resultado esperado por roles\n"
            "| Estado del usuario | Resultado |\n"
            "|--------------------|-----------|\n"
            "| Sin token (anónimo) | ✅ 200 |\n"
            "| Token expirado | ✅ 200 |\n"
            "| Autenticado, cualquier rol | ✅ 200 |\n"
        ),
        auth=[],
        responses={
            200: _ok(
                "PublicResponse",
                {
                    "message": "Endpoint público — accesible sin autenticación",
                    "authenticated": "false",
                },
            )
        },
    )
    def get(self, request: Request) -> Response:
        is_auth = bool(request.user and request.user.is_authenticated)
        return Response({
            "message": "Endpoint público — accesible sin autenticación",
            "authenticated": str(is_auth).lower(),
            "user": str(request.user) if is_auth else "anónimo",
        })


class AnonymousInfoView(APIView):
    """Muestra información del estado de autenticación del caller."""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Playground"],
        summary="¿Quién llama? (público)",
        description=(
            "Endpoint público que **informa el estado de autenticación** del solicitante.\n\n"
            "Útil para verificar que el token se está enviando correctamente "
            "antes de probar endpoints protegidos.\n\n"
            "### Cómo probarlo\n"
            "1. Sin Bearer token → `authenticated: false`, `user: 'anónimo'`\n"
            "2. Con Bearer token válido → `authenticated: true`, muestra email y rol\n\n"
            "### Resultado esperado\n"
            "| Estado | `authenticated` | `user` | `role` |\n"
            "|--------|----------------|--------|--------|\n"
            "| Sin token | `false` | `'anónimo'` | `null` |\n"
            "| Con token válido | `true` | email del usuario | nombre del rol |\n"
        ),
        auth=[],
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="AnonymousInfoResponse",
                    fields={
                        "authenticated": s.CharField(),
                        "user": s.CharField(),
                        "role": s.CharField(allow_null=True),
                    },
                ),
                description="Información del caller.",
                examples=[
                    OpenApiExample(
                        "Anónimo",
                        value={"authenticated": "false", "user": "anónimo", "role": None},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Autenticado",
                        value={"authenticated": "true", "user": "john@example.com", "role": "Operador"},
                        response_only=True,
                    ),
                ],
            )
        },
    )
    def get(self, request: Request) -> Response:
        is_auth = bool(request.user and request.user.is_authenticated)
        role = getattr(request.user, "role", None) if is_auth else None
        return Response({
            "authenticated": str(is_auth).lower(),
            "user": str(request.user) if is_auth else "anónimo",
            "role": str(role) if role else None,
        })


# ===========================================================================
# ESCENARIO B — Solo autenticación (cualquier rol)
# ===========================================================================

class AuthenticatedOnlyView(APIView):
    """Requiere JWT válido. No exige ningún permiso específico."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Playground"],
        summary="Solo usuarios autenticados (cualquier rol)",
        description=(
            "Responde a cualquier usuario con un **JWT válido**, "
            "independientemente del rol que tenga asignado.\n\n"
            "### ¿Qué demuestra?\n"
            "`IsAuthenticated` verifica solo que el token existe y es válido. "
            "No consulta roles ni permisos.\n\n"
            "### Cómo probarlo\n"
            "1. **Sin Bearer token** → `401` ❌\n"
            "2. **Con token expirado** → `401` ❌\n"
            "3. **Con token válido, rol Operador** → `200` ✅\n"
            "4. **Con token válido, rol Administrador** → `200` ✅\n\n"
            "### Resultado esperado por estado\n"
            "| Estado | Resultado |\n"
            "|--------|-----------|\n"
            "| Sin token | ❌ 401 |\n"
            "| Token expirado | ❌ 401 |\n"
            "| Token válido, **cualquier rol** | ✅ 200 |\n"
        ),
        responses={
            200: _ok(
                "AuthenticatedOnlyResponse",
                {
                    "message": "Acceso correcto — estás autenticado",
                    "user": "john@example.com",
                    "role": "Operador",
                },
            ),
            401: _401,
        },
    )
    def get(self, request: Request) -> Response:
        role = getattr(request.user, "role", None)
        return Response({
            "message": "Acceso correcto — estás autenticado",
            "user": str(request.user),
            "role": str(role) if role else None,
        })


# ===========================================================================
# ESCENARIO C — HasPermission (permiso único, distintos niveles)
# ===========================================================================

class PermisoConciliacionRun(APIView):
    """Requiere conciliacion.run — solo Administrador."""
    permission_classes = [IsAuthenticated, HasPermission("conciliacion.run")]

    @extend_schema(
        tags=["Playground"],
        summary="Requiere: conciliacion.run",
        description=(
            "Acepta usuarios cuyo rol incluya el permiso `conciliacion.run`.\n\n"
            "### Acceso por rol\n"
            "| Rol | Tiene `conciliacion.run` | Resultado |\n"
            "|-----|--------------------------|----------|\n"
            "| Sin token | — | ❌ 401 |\n"
            "| **Operador** | ❌ No | ❌ 403 |\n"
            "| **Administrador** | ✅ Sí | ✅ 200 |\n\n"
            "### Prueba rápida\n"
            "Logueate como usuario con rol **Operador** → `403`\n\n"
            "Logueate como usuario con rol **Administrador** → `200`"
        ),
        responses={200: _ok("PermisoConciliacionRunResponse", {"acceso": "concedido", "permiso": "conciliacion.run"}), 401: _401, 403: _403},
    )
    def get(self, request: Request) -> Response:
        return Response({"acceso": "concedido", "permiso": "conciliacion.run", "user": str(request.user)})


class PermisoConciliacionExport(APIView):
    """Requiere conciliacion.export — solo Administrador."""
    permission_classes = [IsAuthenticated, HasPermission("conciliacion.export")]

    @extend_schema(
        tags=["Playground"],
        summary="Requiere: conciliacion.export",
        description=(
            "Acepta usuarios cuyo rol incluya el permiso `conciliacion.export`.\n\n"
            "### Acceso por rol\n"
            "| Rol | Tiene `conciliacion.export` | Resultado |\n"
            "|-----|-----------------------------|----------|\n"
            "| Sin token | — | ❌ 401 |\n"
            "| **Operador** | ❌ No | ❌ 403 |\n"
            "| **Administrador** | ✅ Sí | ✅ 200 |\n\n"
            "### Prueba rápida\n"
            "Logueate como **Operador** → `403` (puede ver la conciliación pero no exportar)\n\n"
            "Logueate como **Administrador** → `200`"
        ),
        responses={200: _ok("PermisoConciliacionExportResponse", {"acceso": "concedido", "permiso": "conciliacion.export"}), 401: _401, 403: _403},
    )
    def get(self, request: Request) -> Response:
        return Response({"acceso": "concedido", "permiso": "conciliacion.export", "user": str(request.user)})


class PermisoReportesExport(APIView):
    """Requiere reportes.export — Supervisor y Administrador."""
    permission_classes = [IsAuthenticated, HasPermission("reportes.export")]

    @extend_schema(
        tags=["Playground"],
        summary="Requiere: reportes.export",
        description=(
            "Acepta usuarios cuyo rol incluya el permiso `reportes.export`.\n\n"
            "### Acceso por rol\n"
            "| Rol | Tiene `reportes.export` | Resultado |\n"
            "|-----|-------------------------|----------|\n"
            "| Sin token | — | ❌ 401 |\n"
            "| **Operador** | ❌ No | ❌ 403 |\n"
            "| **Administrador** | ✅ Sí | ✅ 200 |\n"
        ),
        responses={200: _ok("PermisoReportesExportResponse", {"acceso": "concedido", "permiso": "reportes.export"}), 401: _401, 403: _403},
    )
    def get(self, request: Request) -> Response:
        return Response({"acceso": "concedido", "permiso": "reportes.export", "user": str(request.user)})


class PermisoUsuariosDelete(APIView):
    """Requiere usuarios.delete — solo Administrador."""
    permission_classes = [IsAuthenticated, HasPermission("usuarios.delete")]

    @extend_schema(
        tags=["Playground"],
        summary="Requiere: usuarios.delete  ← solo Administrador",
        description=(
            "Solo accesible para el rol **Administrador** "
            "(único que incluye `usuarios.delete` en la carga inicial).\n\n"
            "### Acceso por rol\n"
            "| Rol | Tiene `usuarios.delete` | Resultado |\n"
            "|-----|-------------------------|----------|\n"
            "| Sin token | — | ❌ 401 |\n"
            "| **Operador** | ❌ No | ❌ 403 |\n"
            "| **Administrador** | ✅ Sí | ✅ 200 |\n\n"
            "### Prueba rápida\n"
            "Prueba con **Operador** → `403`.\n\n"
            "Demuestra que los roles tienen fronteras claras: ver ≠ eliminar."
        ),
        responses={200: _ok("PermisoDeleteResponse", {"acceso": "concedido", "permiso": "usuarios.delete"}), 401: _401, 403: _403},
        request=None,
    )
    def delete(self, request: Request) -> Response:
        return Response({"acceso": "concedido", "permiso": "usuarios.delete", "user": str(request.user)})


class PermisoAdminFull(APIView):
    """Requiere admin.full — solo Administrador."""
    permission_classes = [IsAuthenticated, HasPermission("admin.full")]

    @extend_schema(
        tags=["Playground"],
        summary="Requiere: admin.full  ← solo Administrador",
        description=(
            "Permiso de mayor nivel del sistema. Solo el rol **Administrador** lo posee.\n\n"
            "### Acceso por rol\n"
            "| Rol | Tiene `admin.full` | Resultado |\n"
            "|-----|--------------------|----------|\n"
            "| Sin token | — | ❌ 401 |\n"
            "| **Operador** | ❌ No | ❌ 403 |\n"
            "| **Administrador** | ✅ Sí | ✅ 200 |\n\n"
            "### Diferencia con `usuarios.delete`\n"
            "Ambos son de nivel Administrador, pero son permisos independientes. "
            "En el futuro se puede crear un rol **Super-Admin** que tenga `admin.full` "
            "pero no `usuarios.delete` (o viceversa), sin modificar código."
        ),
        responses={200: _ok("PermisoAdminFullResponse", {"acceso": "concedido", "permiso": "admin.full"}), 401: _401, 403: _403},
    )
    def get(self, request: Request) -> Response:
        return Response({"acceso": "concedido", "permiso": "admin.full", "user": str(request.user)})


# ===========================================================================
# ESCENARIO D — HasAnyPermission (lógica OR)
# ===========================================================================

class PermisoOrView(APIView):
    """Requiere conciliacion.view OR reportes.view."""
    permission_classes = [IsAuthenticated, HasAnyPermission("conciliacion.view", "reportes.view")]

    @extend_schema(
        tags=["Playground"],
        summary="Requiere: conciliacion.view OR reportes.view",
        description=(
            "Acepta usuarios que tengan **al menos uno** de los dos permisos.\n\n"
            "### Clase usada: `HasAnyPermission('conciliacion.view', 'reportes.view')`\n\n"
            "### Acceso por rol\n"
            "| Rol | `conciliacion.view` | `reportes.view` | OR → Resultado |\n"
            "|-----|---------------------|-----------------|----------------|\n"
            "| Sin token | — | — | ❌ 401 |\n"
            "| **Operador** | ✅ | ✅ | ✅ 200 |\n"
            "| **Administrador** | ✅ | ✅ | ✅ 200 |\n\n"
            "En este ejemplo ambos roles tienen acceso porque ambos permisos "
            "están en todos los roles. Para ver el OR en acción, prueba con un rol "
            "hipotético que tenga solo uno de los dos.\n\n"
            "### Cuándo usar lógica OR\n"
            "Ideal cuando **distintos dominios del sistema** necesitan acceso al mismo recurso. "
            "Ej: el equipo de conciliación y el equipo de reportes pueden ver el mismo dashboard."
        ),
        responses={
            200: _ok(
                "PermisoOrResponse",
                {
                    "acceso": "concedido",
                    "logica": "OR",
                    "permisos_evaluados": "conciliacion.view | reportes.view",
                },
            ),
            401: _401,
            403: OpenApiResponse(
                description=(
                    "**403** — El usuario no tiene ni `conciliacion.view` ni `reportes.view`.\n\n"
                    "En la configuración inicial esto **nunca ocurre** porque todos los roles "
                    "tienen ambos permisos, pero aplica si se crea un rol sin ellos."
                ),
                examples=[
                    OpenApiExample(
                        "Sin ningún permiso",
                        value={"detail": "Permiso denegado. No posee ninguno de los permisos requeridos."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def get(self, request: Request) -> Response:
        return Response({
            "acceso": "concedido",
            "logica": "OR",
            "permisos_evaluados": "conciliacion.view | reportes.view",
            "user": str(request.user),
        })


class PermisoOrRestrictivoView(APIView):
    """Requiere conciliacion.export OR admin.full — solo Supervisor y Admin."""
    permission_classes = [IsAuthenticated, HasAnyPermission("conciliacion.export", "admin.full")]

    @extend_schema(
        tags=["Playground"],
        summary="Requiere: conciliacion.export OR admin.full  ← solo Administrador",
        description=(
            "Ejemplo de OR **restrictivo**: los dos permisos son de nivel alto, "
            "por lo que solo roles de nivel Supervisor o superior acceden.\n\n"
            "### Clase usada: `HasAnyPermission('conciliacion.export', 'admin.full')`\n\n"
            "### Acceso por rol\n"
            "| Rol | `conciliacion.export` | `admin.full` | OR → Resultado |\n"
            "|-----|-----------------------|--------------|----------------|\n"
            "| Sin token | — | — | ❌ 401 |\n"
            "| **Operador** | ❌ | ❌ | ❌ 403 |\n"
            "| **Administrador** | ✅ | ✅ | ✅ 200 |\n\n"
            "Prueba con **Operador** → `403`. Prueba con **Administrador** → `200`."
        ),
        responses={
            200: _ok(
                "PermisoOrRestrictivoResponse",
                {
                    "acceso": "concedido",
                    "logica": "OR restrictivo",
                    "permisos_evaluados": "conciliacion.export | admin.full",
                },
            ),
            401: _401,
            403: _403,
        },
    )
    def get(self, request: Request) -> Response:
        return Response({
            "acceso": "concedido",
            "logica": "OR restrictivo",
            "permisos_evaluados": "conciliacion.export | admin.full",
            "user": str(request.user),
        })


# ===========================================================================
# ESCENARIO E — HasAllPermissions (lógica AND)
# ===========================================================================

class PermisoAndView(APIView):
    """Requiere conciliacion.run AND reportes.export — solo Supervisor y Admin."""
    permission_classes = [IsAuthenticated, HasAllPermissions("conciliacion.run", "reportes.export")]

    @extend_schema(
        tags=["Playground"],
        summary="Requiere: conciliacion.run AND reportes.export",
        description=(
            "Acepta usuarios que tengan **ambos** permisos simultáneamente.\n\n"
            "### Clase usada: `HasAllPermissions('conciliacion.run', 'reportes.export')`\n\n"
            "### Acceso por rol\n"
            "| Rol | `conciliacion.run` | `reportes.export` | AND → Resultado |\n"
            "|-----|--------------------|--------------------|------------------|\n"
            "| Sin token | — | — | ❌ 401 |\n"
            "| **Operador** | ❌ | ❌ | ❌ 403 |\n"
            "| **Administrador** | ✅ | ✅ | ✅ 200 |\n\n"
            "### Punto clave\n"
            "El **Operador** solo tiene permisos de vista y no posee `conciliacion.run` ni `reportes.export`. "
            "AND es más estricto: se requieren todos, no basta con uno.\n\n"
            "### Cuándo usar lógica AND\n"
            "Operaciones críticas que requieren capacidades de **múltiples dominios** "
            "(ej: proceso que corre una conciliación y luego exporta el reporte resultante)."
        ),
        responses={
            200: _ok(
                "PermisoAndResponse",
                {
                    "acceso": "concedido",
                    "logica": "AND",
                    "permisos_evaluados": "conciliacion.run AND reportes.export",
                },
            ),
            401: _401,
            403: OpenApiResponse(
                description=(
                    "**403** — El usuario no tiene uno o ambos permisos requeridos.\n\n"
                    "Caso típico: **Operador** no tiene ninguno de los dos permisos requeridos."
                ),
                examples=[
                    OpenApiExample(
                        "Tiene solo uno",
                        value={"detail": "Permiso denegado. No posee todos los permisos requeridos."},
                        response_only=True,
                    )
                ],
            ),
        },
        request=None,
    )
    def post(self, request: Request) -> Response:
        return Response({
            "acceso": "concedido",
            "logica": "AND",
            "permisos_evaluados": "conciliacion.run AND reportes.export",
            "user": str(request.user),
        })


class PermisoAndAdminView(APIView):
    """Requiere usuarios.create AND usuarios.delete — solo Administrador."""
    permission_classes = [IsAuthenticated, HasAllPermissions("usuarios.create", "usuarios.delete")]

    @extend_schema(
        tags=["Playground"],
        summary="Requiere: usuarios.create AND usuarios.delete  ← solo Administrador",
        description=(
            "Ejemplo extremo de AND: requiere dos permisos de gestión de usuarios "
            "que solo el **Administrador** posee.\n\n"
            "### Acceso por rol\n"
            "| Rol | `usuarios.create` | `usuarios.delete` | AND → Resultado |\n"
            "|-----|-------------------|--------------------|-----------------|\n"
            "| Sin token | — | — | ❌ 401 |\n"
            "| **Operador** | ❌ | ❌ | ❌ 403 |\n"
            "| **Administrador** | ✅ | ✅ | ✅ 200 |\n\n"
            "Demuestra que se puede construir una **jerarquía implícita** "
            "combinando AND con permisos de nivel alto."
        ),
        responses={
            200: _ok("PermisoAndAdminResponse", {"acceso": "concedido", "logica": "AND — solo Admin"}),
            401: _401,
            403: _403,
        },
        request=None,
    )
    def delete(self, request: Request) -> Response:
        return Response({
            "acceso": "concedido",
            "logica": "AND — solo Admin",
            "permisos_evaluados": "usuarios.create AND usuarios.delete",
            "user": str(request.user),
        })


# ===========================================================================
# ESCENARIO F — Introspección: quién soy y qué puedo hacer
# ===========================================================================

class WhoAmIView(APIView):
    """Devuelve identidad completa + permisos del usuario autenticado."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Playground"],
        summary="¿Quién soy? ¿Qué puedo hacer?",
        description=(
            "Retorna el perfil completo del usuario autenticado junto con su rol "
            "y la lista exacta de permisos que tiene en este momento.\n\n"
            "### ¿Qué demuestra?\n"
            "- Que el rol y los permisos se leen **directamente de la base de datos** "
            "en cada request, sin depender del contenido del JWT.\n"
            "- Que cambiar el rol en el admin de Django surte efecto **inmediatamente** "
            "en la próxima llamada a este endpoint.\n\n"
            "### Casos de prueba\n"
            "1. Loguear como **Operador** → ver que solo tiene permisos de vista\n"
            "2. En el admin de Django cambiar ese usuario a **Administrador**\n"
            "3. **Sin renovar el token**, volver a llamar este endpoint → los permisos ya cambiaron\n\n"
            "### Respuestas por rol\n"
            "| Rol | Permisos esperados |\n"
            "|-----|--------------------\n"
            "| Operador | `conciliacion.view`, `reportes.view`, `dashboard.view` (3 permisos) |\n"
            "| Administrador | Todos (11 permisos) |\n"
            "| Sin rol | `[]` |\n"
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="WhoAmIResponse",
                    fields={
                        "user": s.CharField(),
                        "email": s.EmailField(),
                        "role": s.CharField(allow_null=True),
                        "permissions": s.ListField(child=s.CharField()),
                        "permission_count": s.IntegerField(),
                    },
                ),
                description="Identidad completa + permisos del usuario.",
                examples=[
                    OpenApiExample(
                        "Operador",
                        value={
                            "user": "john@example.com",
                            "email": "john@example.com",
                            "role": "Operador",
                            "permissions": [
                                "conciliacion.view",
                                "dashboard.view",
                                "reportes.view",
                            ],
                            "permission_count": 3,
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Administrador",
                        value={
                            "user": "admin@example.com",
                            "email": "admin@example.com",
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
                            "permission_count": 11,
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Sin rol",
                        value={
                            "user": "norole@example.com",
                            "email": "norole@example.com",
                            "role": None,
                            "permissions": [],
                            "permission_count": 0,
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: _401,
        },
    )
    def get(self, request: Request) -> Response:
        user = request.user
        role = getattr(user, "role", None)
        permisos = get_user_permissions(user)
        return Response({
            "user": str(user),
            "email": getattr(user, "email", str(user)),
            "role": str(role) if role else None,
            "permissions": sorted(permisos),
            "permission_count": len(permisos),
        })


class AccessMatrixView(APIView):
    """Muestra una matriz de acceso para todos los permisos del sistema."""
    permission_classes = [IsAuthenticated]

    _TODOS_LOS_PERMISOS = [
        "conciliacion.run",
        "conciliacion.view",
        "conciliacion.export",
        "reportes.view",
        "reportes.export",
        "dashboard.view",
        "usuarios.view",
        "usuarios.create",
        "usuarios.edit",
        "usuarios.delete",
        "admin.full",
    ]

    @extend_schema(
        tags=["Playground"],
        summary="Matriz de acceso — qué endpoints puedo usar",
        description=(
            "Evalúa **en tiempo real** qué permisos del sistema tiene el usuario "
            "y cuáles le faltan, devolviendo una matriz completa.\n\n"
            "Útil para que el frontend sepa exactamente qué mostrar/ocultar "
            "sin hacer múltiples requests.\n\n"
            "### Cómo funciona\n"
            "Para cada permiso conocido del sistema llama internamente a "
            "`user_has_permission(user, code)` y agrupa los resultados en "
            "`tiene` y `no_tiene`.\n\n"
            "### Valor de esta vista\n"
            "Demuestra que el sistema RBAC es **dinámico**: si se cambia el rol "
            "del usuario en el admin de Django, la matriz es diferente en el siguiente "
            "request **sin renovar el token JWT**."
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="AccessMatrixResponse",
                    fields={
                        "user": s.CharField(),
                        "role": s.CharField(allow_null=True),
                        "tiene": s.ListField(child=s.CharField()),
                        "no_tiene": s.ListField(child=s.CharField()),
                    },
                ),
                description="Matriz de acceso completa.",
                examples=[
                    OpenApiExample(
                        "Operador",
                        value={
                            "user": "operador@example.com",
                            "role": "Operador",
                            "tiene": [
                                "conciliacion.view",
                                "dashboard.view",
                                "reportes.view",
                            ],
                            "no_tiene": [
                                "admin.full",
                                "conciliacion.export",
                                "conciliacion.run",
                                "reportes.export",
                                "usuarios.create",
                                "usuarios.delete",
                                "usuarios.edit",
                                "usuarios.view",
                            ],
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: _401,
        },
    )
    def get(self, request: Request) -> Response:
        from apps.authorization.services import user_has_permission
        user = request.user
        role = getattr(user, "role", None)

        tiene = []
        no_tiene = []
        for code in self._TODOS_LOS_PERMISOS:
            if user_has_permission(user, code):
                tiene.append(code)
            else:
                no_tiene.append(code)

        return Response({
            "user": str(user),
            "role": str(role) if role else None,
            "tiene": tiene,
            "no_tiene": no_tiene,
        })

