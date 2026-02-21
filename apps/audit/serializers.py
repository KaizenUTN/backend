"""
audit.serializers
=================
Serializers de solo lectura para los logs de auditoría.

El módulo audit es write-only desde el punto de vista externo:
los registros solo se crean via services.py y se leen via esta API.
No existe serializer de escritura — ningún endpoint permite crear, editar
ni eliminar registros de auditoría.
"""

from __future__ import annotations

from rest_framework import serializers

from .models import AuditLog


class AuditLogUserSerializer(serializers.Serializer):
    """Representación mínima del usuario asociado al log."""

    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para AuditLog.

    El campo `user` muestra id + email en lugar del PK crudo.
    El campo `status_display` expone la etiqueta legible del choice.
    """

    user = AuditLogUserSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "action",
            "resource",
            "resource_id",
            "status",
            "status_display",
            "metadata",
            "ip_address",
            "user_agent",
            "timestamp",
            "correlation_id",
        ]
        read_only_fields = fields
