"""
users.selectors
===============
Consultas de lectura sobre el modelo User.

Regla: ninguna función aquí muta estado.
Toda query usa select_related para evitar N+1 en la serialización del rol.
"""

from __future__ import annotations

from django.db.models import QuerySet

from .models import User


def get_user_by_id(user_id: int) -> User:
    """
    Retorna un usuario por PK con su rol precargado.
    Lanza User.DoesNotExist si no existe.
    """
    return User.objects.select_related('role').get(pk=user_id)


def get_user_list() -> QuerySet[User]:
    """
    Retorna el queryset base de todos los usuarios con su rol precargado.

    Los filtros de la request (email, role, is_active) se aplican externamente
    a través de UserFilter (filters.py) por DjangoFilterBackend.
    El ordenamiento y la paginación también los gestiona DRF.
    """
    return User.objects.select_related('role').order_by('-created_at')
