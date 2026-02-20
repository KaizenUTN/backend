"""
users.filters
=============
Filtros de listado de usuarios usando django-filter.

Filtros disponibles:
    email       → búsqueda parcial case-insensitive (icontains)
    role        → ID exacto del rol (FK)
    is_active   → booleano (true / false como string en query string)
    search      → búsqueda combinada en email, first_name, last_name (SearchFilter de DRF)
    ordering    → campos permitidos para ordenamiento (OrderingFilter de DRF)
"""

from __future__ import annotations

import django_filters

from .models import User


class UserFilter(django_filters.FilterSet):
    email = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Email (contiene)',
    )
    role = django_filters.NumberFilter(
        field_name='role_id',
        label='ID de rol',
    )
    is_active = django_filters.BooleanFilter(
        label='Activo',
    )

    class Meta:
        model = User
        fields = ['email', 'role', 'is_active']
