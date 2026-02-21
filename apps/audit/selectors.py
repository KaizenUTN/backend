"""
audit.selectors
===============
Consultas de lectura para los logs de auditoría.

Responsabilidades:
- Recuperar registros sin mutaciones.
- Aplicar select_related para no disparar N+1 queries.
- Devolver QuerySets; el filtrado adicional lo hace la vista con FilterSet.
"""

from __future__ import annotations

from django.db.models import QuerySet

from .models import AuditLog


def get_audit_log_list() -> QuerySet[AuditLog]:
    """
    Retorna todos los logs de auditoría, ordenados por timestamp descendente.

    Incluye select_related sobre user para acceder a user.email
    sin queries adicionales.
    """
    return AuditLog.objects.select_related("user").all()


def get_audit_log_by_id(log_id: int) -> AuditLog | None:
    """
    Retorna el log con el ID dado, o None si no existe.
    """
    return AuditLog.objects.select_related("user").filter(pk=log_id).first()
