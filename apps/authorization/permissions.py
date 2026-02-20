"""
authorization.permissions
=========================
Clases de permiso DRF basadas en el sistema RBAC.

Uso en views:
    from apps.authorization.permissions import HasPermission

    class ConciliacionView(APIView):
        permission_classes = [HasPermission("conciliacion.run")]

    # O combinando con IsAuthenticated explícito:
    class ReporteView(APIView):
        permission_classes = [IsAuthenticated, HasPermission("reportes.export")]

Diseño:
  - `HasPermission` es una *factory function* que devuelve una clase DRF.
    Esto permite pasar el código de permiso de forma declarativa en la
    lista `permission_classes`, que DRF instancia en tiempo de request.
  - Toda la lógica de autorización vive en `services.user_has_permission`.
    Esta capa solo actúa de adaptador entre DRF y el servicio.
  - Fail-closed: cualquier usuario sin rol o sin el permiso recibe 403.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from .services import user_has_permission


class HasPermission:
    """
    Factory que retorna una clase DRF ``BasePermission`` que valida
    el permiso *permission_code* contra el rol del usuario autenticado.

    El permiso se consulta en base de datos en cada request, lo que
    garantiza que cambios de rol surtan efecto inmediatamente sin
    necesidad de renovar tokens JWT.

    Args:
        permission_code: Código del permiso. Ej: ``"conciliacion.run"``.

    Returns:
        Una subclase de ``BasePermission`` lista para usar en
        ``permission_classes``.

    Example::

        class ConciliacionView(APIView):
            permission_classes = [HasPermission("conciliacion.run")]

        class ComboView(APIView):
            permission_classes = [
                HasPermission("conciliacion.run"),
                HasPermission("conciliacion.view"),
            ]
    """

    def __new__(cls, permission_code: str) -> type[BasePermission]:  # type: ignore[misc]
        class _HasPermission(BasePermission):
            _code: str = permission_code
            message: str = f"Permiso denegado. Se requiere: '{permission_code}'."

            def has_permission(self, request: Request, view: APIView) -> bool:  # type: ignore[override]
                return user_has_permission(request.user, self._code)

        # Nombres legibles en logs, repr() y Swagger.
        _HasPermission.__name__ = f"HasPermission({permission_code!r})"
        _HasPermission.__qualname__ = f"HasPermission({permission_code!r})"
        return _HasPermission


class HasAnyPermission:
    """
    Factory que retorna una clase DRF ``BasePermission`` que retorna True
    si el usuario posee AL MENOS UNO de los códigos de permiso proporcionados.

    Útil para endpoints a los que distintos roles deben acceder.

    Example::

        class DashboardView(APIView):
            permission_classes = [HasAnyPermission("dashboard.view", "admin.full")]
    """

    def __new__(cls, *permission_codes: str) -> type[BasePermission]:  # type: ignore[misc]
        class _HasAnyPermission(BasePermission):
            _codes: tuple[str, ...] = permission_codes
            message: str = "Permiso denegado. No posee ninguno de los permisos requeridos."

            def has_permission(self, request: Request, view: APIView) -> bool:  # type: ignore[override]
                return any(
                    user_has_permission(request.user, code) for code in self._codes
                )

        label = " | ".join(permission_codes)
        _HasAnyPermission.__name__ = f"HasAnyPermission({label!r})"
        _HasAnyPermission.__qualname__ = f"HasAnyPermission({label!r})"
        return _HasAnyPermission


class HasAllPermissions:
    """
    Factory que retorna una clase DRF ``BasePermission`` que retorna True
    solo si el usuario posee TODOS los códigos de permiso proporcionados.

    Example::

        class AdminPanelView(APIView):
            permission_classes = [HasAllPermissions("admin.read", "admin.write")]
    """

    def __new__(cls, *permission_codes: str) -> type[BasePermission]:  # type: ignore[misc]
        class _HasAllPermissions(BasePermission):
            _codes: tuple[str, ...] = permission_codes
            message: str = "Permiso denegado. No posee todos los permisos requeridos."

            def has_permission(self, request: Request, view: APIView) -> bool:  # type: ignore[override]
                return all(
                    user_has_permission(request.user, code) for code in self._codes
                )

        label = " & ".join(permission_codes)
        _HasAllPermissions.__name__ = f"HasAllPermissions({label!r})"
        _HasAllPermissions.__qualname__ = f"HasAllPermissions({label!r})"
        return _HasAllPermissions
