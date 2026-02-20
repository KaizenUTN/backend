"""
authorization.services
======================
Capa de servicios para el módulo RBAC.

Responsabilidades:
  - Consultar permisos desde base de datos.
  - Proveer la función central `user_has_permission` que es la ÚNICA
    fuente de verdad para decisiones de autorización en toda la app.

Reglas de diseño:
  - Sin dependencias hacia el módulo identity (no importa views/serializers).
  - Sin lógica de JWT ni de sesiones.
  - Las queries son deliberadamente simples para favorecer cacheado futuro.
  - Todos los casos edge se resuelven devolviendo False (fail-closed).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Importación solo para type-checking; evita ciclos en runtime.
    from django.contrib.auth.base_user import AbstractBaseUser


def user_has_permission(user: "AbstractBaseUser | None", permission_code: str) -> bool:
    """
    Verifica si *user* posee el permiso identificado por *permission_code*.

    Lógica de evaluación (fail-closed):
      1. Si el usuario es None, anónimo o inactivo → False.
      2. Si el usuario no tiene rol asignado → False.
      3. Consulta en DB si el rol del usuario contiene el permiso.

    Args:
        user:            Instancia del modelo User autenticado (o None/AnonymousUser).
        permission_code: Código del permiso, ej: "conciliacion.run".

    Returns:
        True si el usuario tiene el permiso; False en cualquier otro caso.

    Example:
        >>> if user_has_permission(request.user, "conciliacion.run"):
        ...     run_conciliacion()
    """
    if user is None:
        return False

    # AnonymousUser no tiene is_authenticated como booleano simple en todas
    # las versiones de Django; comparamos explícitamente.
    if not getattr(user, "is_authenticated", False):
        return False

    if not getattr(user, "is_active", False):
        return False

    # Acceso al FK role; el atributo existe solo en el User concreto del proyecto.
    role = getattr(user, "role", None)
    if role is None:
        return False

    # SELECT EXISTS en la tabla intermedia role_permissions.
    # No carga los objetos Permission completos; solo comprueba existencia.
    return role.permissions.filter(code=permission_code).exists()


def get_user_permissions(user: "AbstractBaseUser | None") -> list[str]:
    """
    Retorna la lista de códigos de permiso que posee *user*.

    Útil para endpoints de introspección o para construir payloads
    de respuesta sin exponer lógica de autorización en las views.

    Args:
        user: Instancia del modelo User autenticado (o None/AnonymousUser).

    Returns:
        Lista de strings con los códigos de permiso. Lista vacía si
        el usuario no tiene rol o no está autenticado.
    """
    if user is None:
        return []

    if not getattr(user, "is_authenticated", False):
        return []

    if not getattr(user, "is_active", False):
        return []

    role = getattr(user, "role", None)
    if role is None:
        return []

    return list(role.permissions.values_list("code", flat=True))
