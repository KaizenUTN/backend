"""
authorization.example_views
============================
Archivo de ejemplos — NO incluir en producción como URL real.

Muestra el patrón de uso de HasPermission, HasAnyPermission y
HasAllPermissions dentro de views DRF.

Para registrar uno de estos ejemplos en urls.py:
    path("api/conciliacion/run/", ConciliacionView.as_view()),
"""

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authorization.permissions import HasAllPermissions, HasAnyPermission, HasPermission
from apps.authorization.services import get_user_permissions


# ---------------------------------------------------------------------------
# Ejemplo 1 — Permiso único requerido
# ---------------------------------------------------------------------------

class ConciliacionView(APIView):
    """
    Solo accesible para usuarios cuyo rol incluya "conciliacion.run".

    El token JWT identifica *quién* es el usuario.
    La base de datos decide *qué puede hacer* consultando su rol en tiempo real.
    Cambiar el rol del usuario en DB surte efecto en el siguiente request,
    sin necesidad de revocar ni renovar tokens.
    """
    permission_classes = [IsAuthenticated, HasPermission("conciliacion.run")]

    @extend_schema(
        tags=["Conciliación"],
        summary="Ejecutar proceso de conciliación",
        description="Requiere permiso `conciliacion.run`.",
        responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
    )
    def post(self, request: Request) -> Response:
        # Toda la lógica de negocio va aquí o en un service dedicado.
        # La autorización ya fue validada antes de llegar a este punto.
        return Response({"status": "conciliacion iniciada"})


# ---------------------------------------------------------------------------
# Ejemplo 2 — Permiso de solo lectura
# ---------------------------------------------------------------------------

class ConciliacionDetailView(APIView):
    """Requiere "conciliacion.view" para leer el estado de conciliaciones."""

    permission_classes = [IsAuthenticated, HasPermission("conciliacion.view")]

    def get(self, request: Request) -> Response:
        return Response({"conciliaciones": []})


# ---------------------------------------------------------------------------
# Ejemplo 3 — Al menos uno de varios permisos (OR)
# ---------------------------------------------------------------------------

class DashboardView(APIView):
    """
    Accesible si el usuario tiene "dashboard.view" OR "admin.full".
    Útil cuando múltiples roles distintos deben ver el mismo recurso.
    """
    permission_classes = [IsAuthenticated, HasAnyPermission("dashboard.view", "admin.full")]

    def get(self, request: Request) -> Response:
        return Response({"widgets": []})


# ---------------------------------------------------------------------------
# Ejemplo 4 — Todos los permisos requeridos (AND)
# ---------------------------------------------------------------------------

class AdminPanelView(APIView):
    """
    Requiere "admin.read" AND "admin.write" simultáneamente.
    """
    permission_classes = [IsAuthenticated, HasAllPermissions("admin.read", "admin.write")]

    def get(self, request: Request) -> Response:
        return Response({"panel": "ok"})


# ---------------------------------------------------------------------------
# Ejemplo 5 — Introspección: permisos del usuario actual
# ---------------------------------------------------------------------------

class MyPermissionsView(APIView):
    """
    Retorna la lista de permisos del usuario autenticado.
    Útil para que el frontend ajuste la UI dinámicamente.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        permisos = get_user_permissions(request.user)
        return Response({
            "role": str(request.user.role) if request.user.role else None,  # type: ignore[union-attr]
            "permissions": permisos,
        })
