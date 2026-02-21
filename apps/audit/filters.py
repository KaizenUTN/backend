"""
audit.filters
=============
FilterSet para consultas sobre AuditLog.

Campos filtrables:
- action     — búsqueda exacta o contiene
- resource   — búsqueda exacta o contiene
- status     — SUCCESS / FAILURE
- user_id    — ID numérico del usuario
- timestamp  — rango __gte / __lte
- correlation_id — UUID exacto
"""

from __future__ import annotations

import django_filters

from .models import AuditLog


class AuditLogFilter(django_filters.FilterSet):
    """
    Filtros disponibles para el endpoint GET /api/audit/logs/.

    Ejemplos de uso:
        ?status=FAILURE
        ?action=auth.login
        ?action__icontains=login
        ?resource=session
        ?user_id=5
        ?timestamp__gte=2026-01-01T00:00:00Z
        ?timestamp__lte=2026-12-31T23:59:59Z
        ?correlation_id=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    """

    action = django_filters.CharFilter(lookup_expr="icontains")
    resource = django_filters.CharFilter(lookup_expr="icontains")
    status = django_filters.CharFilter(lookup_expr="exact")
    user_id = django_filters.NumberFilter(field_name="user__id")
    timestamp__gte = django_filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="gte")
    timestamp__lte = django_filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="lte")
    correlation_id = django_filters.UUIDFilter(field_name="correlation_id")

    class Meta:
        model = AuditLog
        fields = ["action", "resource", "status", "user_id", "correlation_id"]
