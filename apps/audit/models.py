"""
audit.models
============
Modelos de auditoría del sistema.

Arquitectura (Open/Closed Principle):
- BaseAuditLog: clase abstracta con todos los campos comunes.
  Cerrada para modificación, abierta para extensión.
  Cada subclase genera su propia tabla en la base de datos.

- AuditLog: implementación concreta por defecto para eventos generales.

Para agregar nuevas clases de auditoría sin modificar esta base:

    # En otro módulo (ej: apps/payments/models.py)
    from apps.audit.models import BaseAuditLog

    class FinancialAuditLog(BaseAuditLog):
        amount = models.DecimalField(max_digits=14, decimal_places=2)
        currency = models.CharField(max_length=3, default="ARS")

        class Meta(BaseAuditLog.Meta):
            app_label = "payments"
            verbose_name = "Log Financiero"
            verbose_name_plural = "Logs Financieros"

Diseño deliberado:
- Sin ForeignKey a otros módulos (solo a settings.AUTH_USER_MODEL).
- user nullable para registrar acciones anónimas o del sistema.
- metadata JSONField libre para contexto adicional sin romper el esquema.
- correlation_id permite trazabilidad de operaciones compuestas.
- Índices compuestos en campos de alta cardinalidad para consultas eficientes.
- Preparado para exportar a ELK/Loki/SIEM sin cambios estructurales.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# Choices de estado
# ---------------------------------------------------------------------------


class AuditStatus(models.TextChoices):
    """Estado del evento auditado."""

    SUCCESS = "SUCCESS", "Exitoso"
    FAILURE = "FAILURE", "Fallido"


# ---------------------------------------------------------------------------
# Clase base abstracta
# ---------------------------------------------------------------------------


class BaseAuditLog(models.Model):
    """
    Clase base abstracta para todos los logs de auditoría.

    abstract = True: no genera tabla propia. Cada subclase concreta tiene
    su propia tabla, lo que permite particionar el histórico por tipo de evento
    y optimizar consultas de forma independiente.

    Campos comunes a toda auditoría:
    - user: quién ejecutó la acción (nullable para acciones del sistema).
    - action: qué acción se ejecutó (convención: "<recurso>.<verbo>").
    - resource: qué tipo de entidad fue afectada.
    - resource_id: cuál instancia específica fue afectada.
    - status: si la operación fue exitosa o fallida.
    - metadata: contexto adicional en JSON (sin datos sensibles).
    - ip_address: IP de origen de la request.
    - user_agent: cliente HTTP de origen.
    - timestamp: cuándo ocurrió (inmutable, auto-generado).
    - correlation_id: UUID para correlacionar eventos de una misma operación.

    Para extender: crear una subclase concreta con campos adicionales.
    NO modificar esta clase para agregar lógica específica de dominio.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",  # deshabilita reverse accessor — el log es write-only desde User
        verbose_name="Usuario",
        help_text="Usuario que ejecutó la acción. Null para acciones anónimas o del sistema.",
    )
    action = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Acción",
        help_text='Identificador de la acción. Convención: "<recurso>.<verbo>" — ej: "user.created".',
    )
    resource = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Recurso",
        help_text='Tipo de recurso afectado. Ej: "user", "payment", "report".',
    )
    resource_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="ID del recurso",
        help_text="Identificador del recurso específico afectado (opcional).",
    )
    status = models.CharField(
        max_length=10,
        choices=AuditStatus.choices,
        default=AuditStatus.SUCCESS,
        db_index=True,
        verbose_name="Estado",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadata",
        help_text=(
            "Contexto adicional en formato JSON. "
            "NUNCA incluir datos sensibles: passwords, tokens, claves privadas."
        ),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dirección IP",
        help_text="IP de origen de la solicitud.",
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        verbose_name="User-Agent",
        help_text="Identificación del cliente HTTP.",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Timestamp",
        help_text="Fecha y hora UTC de creación. Inmutable.",
    )
    correlation_id = models.UUIDField(
        default=uuid.uuid4,
        db_index=True,
        verbose_name="Correlation ID",
        help_text=(
            "UUID que correlaciona múltiples eventos de una misma operación. "
            "Útil para trazabilidad en arquitecturas orientadas a eventos."
        ),
    )

    class Meta:
        abstract = True
        ordering = ["-timestamp"]
        indexes = [
            # Consultas por tipo de evento: "¿qué acciones se hicieron sobre X recurso?"
            models.Index(fields=["action", "resource"], name="%(app_label)s_%(class)s_act_res_idx"),
            # Consultas de monitoreo: "¿cuántos fallos hubo en las últimas N horas?"
            models.Index(fields=["status", "timestamp"], name="%(app_label)s_%(class)s_status_ts_idx"),
            # Consultas por usuario: "¿qué hizo este usuario?"
            models.Index(fields=["user", "timestamp"], name="%(app_label)s_%(class)s_user_ts_idx"),
        ]

    def __str__(self) -> str:
        user_id = getattr(self, "user_id", None)
        actor = f"user:{user_id}" if user_id else "anonymous"
        return f"[{self.timestamp}] {self.action} on {self.resource} by {actor} — {self.status}"


# ---------------------------------------------------------------------------
# Implementación concreta por defecto
# ---------------------------------------------------------------------------


class AuditLog(BaseAuditLog):
    """
    Log de auditoría general del sistema.

    Tabla por defecto para eventos de negocio estándar que no requieren
    campos adicionales (alta de usuario, cambio de contraseña, etc.).

    Para eventos especializados, crear subclases de BaseAuditLog en lugar
    de agregar campos aquí. Esto mantiene cada tabla enfocada y optimizada.

    Ejemplo de extensión para auditoría financiera:

        class FinancialAuditLog(BaseAuditLog):
            amount = models.DecimalField(max_digits=14, decimal_places=2)
            currency = models.CharField(max_length=3, default="ARS")
            payment_method = models.CharField(max_length=50, blank=True, default="")

            class Meta(BaseAuditLog.Meta):
                app_label = "payments"
                verbose_name = "Log Financiero"
                verbose_name_plural = "Logs Financieros"

    Ejemplo de extensión para auditoría de seguridad:

        class SecurityAuditLog(BaseAuditLog):
            threat_level = models.CharField(
                max_length=20,
                choices=[("LOW", "Bajo"), ("MEDIUM", "Medio"), ("HIGH", "Alto"), ("CRITICAL", "Crítico")],
                default="LOW",
            )
            blocked = models.BooleanField(default=False)

            class Meta(BaseAuditLog.Meta):
                app_label = "security"
                verbose_name = "Log de Seguridad"
    """

    class Meta(BaseAuditLog.Meta):
        app_label = "audit"
        verbose_name = "Log de Auditoría"
        verbose_name_plural = "Logs de Auditoría"
