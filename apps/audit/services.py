"""
audit.services
==============
Servicios de escritura de auditoría.

Principios de diseño:

1. Open/Closed: las funciones aceptan el modelo como parámetro (audit_model),
   lo que permite registrar en AuditLog, FinancialAuditLog, SecurityAuditLog, etc.
   sin modificar este módulo.

2. Fail-silent: un fallo de escritura en auditoría NUNCA debe cortar el flujo
   de negocio principal. Los errores se loggean internamente.

3. Sin side-effects no controlados: no emite señales, no llama a otros servicios,
   no hace HTTP, no usa celery tasks (en esta capa).

4. Sin lógica de negocio: este módulo solo escribe registros. Quién llama,
   cuándo, qué escribir — eso lo decide el servicio de negocio del caller.

5. Preparado para future-proofing:
   - Fácil de reemplazar la capa de persistencia por una cola de mensajes.
   - Compatible con export a ELK/Loki agregando handlers en el logger "audit".
   - correlation_id habilita trazabilidad en arquitecturas event-driven.

Uso típico desde una capa service:

    from apps.audit.services import log_action, log_failure

    # Registro de acción exitosa (modelo por defecto: AuditLog)
    log_action(
        user=user,
        action="user.created",
        resource="user",
        resource_id=str(user.pk),
        metadata={"email": user.email, "role_id": user.role_id},
    )

    # Registro con modelo especializado
    from apps.payments.models import FinancialAuditLog

    log_action(
        audit_model=FinancialAuditLog,
        user=user,
        action="payment.approved",
        resource="payment",
        resource_id=str(payment.pk),
        metadata={"payment_id": payment.pk, "amount": str(payment.amount)},
        amount=payment.amount,
        currency=payment.currency,
    )

    # Registro de fallo
    log_failure(
        user=request.user,
        action="auth.login",
        resource="session",
        metadata={"reason": "invalid_credentials"},
        ip_address=get_client_ip(request),
    )

IMPORTANTE: Nunca incluir en metadata: passwords, tokens, claves privadas,
PAN de tarjetas u otros datos sensibles.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.db import DatabaseError

from .models import AuditLog, AuditStatus, BaseAuditLog

logger = logging.getLogger("audit")

# Alias de tipo para documentar que se espera una subclase concreta de BaseAuditLog.
# Ejemplo: AuditLog, FinancialAuditLog, SecurityAuditLog.
type AuditModel = type[BaseAuditLog]


# ---------------------------------------------------------------------------
# Función genérica de bajo nivel
# ---------------------------------------------------------------------------


def create_audit_entry(
    *,
    audit_model: AuditModel = AuditLog,
    user: Any | None = None,
    action: str,
    resource: str,
    resource_id: str = "",
    status: str = AuditStatus.SUCCESS,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str = "",
    correlation_id: uuid.UUID | None = None,
    **extra_fields: Any,
) -> BaseAuditLog | None:
    """
    Función genérica de bajo nivel para crear un entry de auditoría.

    Acepta cualquier subclase concreta de BaseAuditLog a través de audit_model,
    lo que habilita el patrón Open/Closed: nuevas clases de auditoría se usan
    aquí sin modificar este módulo.

    Los campos adicionales definidos en subclases concretas se pasan como
    keyword arguments y se aplican vía **extra_fields.

    Fail-silent: ante DatabaseError, loggea el error y retorna None —
    nunca interrumpe el flujo de negocio del caller.

    Args:
        audit_model:    Subclase concreta de BaseAuditLog (default: AuditLog).
        user:           Instancia del modelo User, o None para acciones anónimas/sistema.
        action:         Identificador de la acción. Convención "<recurso>.<verbo>".
                        Ej: "user.created", "auth.login_failed", "payment.approved".
        resource:       Tipo de recurso. Ej: "user", "payment", "report".
        resource_id:    ID del recurso específico afectado (opcional, string).
        status:         "SUCCESS" o "FAILURE". Ver AuditStatus.
        metadata:       Contexto adicional en JSON. NUNCA incluir passwords, tokens.
        ip_address:     IP de origen de la request (IPv4 o IPv6).
        user_agent:     User-Agent del cliente HTTP.
        correlation_id: UUID para correlacionar múltiples eventos de una operación.
                        Se auto-genera si no se provee.
        **extra_fields: Campos adicionales para subclases (ej: amount, currency).

    Returns:
        Instancia guardada del modelo de auditoría, o None si falló la escritura.
    """
    try:
        entry = audit_model(
            user=user,
            action=action,
            resource=resource,
            resource_id=resource_id,
            status=status,
            metadata=metadata if metadata is not None else {},
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id if correlation_id is not None else uuid.uuid4(),
            **extra_fields,
        )
        entry.save()
        return entry

    except DatabaseError:
        logger.exception(
            "audit_write_failed",
            extra={
                "audit_model": audit_model.__name__,
                "action": action,
                "resource": resource,
                "resource_id": resource_id,
                "status": status,
            },
        )
        return None


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def log_action(
    *,
    audit_model: AuditModel = AuditLog,
    user: Any | None = None,
    action: str,
    resource: str,
    resource_id: str = "",
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str = "",
    correlation_id: uuid.UUID | None = None,
    **extra_fields: Any,
) -> BaseAuditLog | None:
    """
    Registra una acción exitosa (status=SUCCESS).

    Wrapper semántico sobre create_audit_entry. Usar cuando la operación
    de negocio completó correctamente.

    Ejemplo de uso directo desde un service:

        @transaction.atomic
        def create_user(*, email, first_name, last_name, password, role_id=None):
            user = User(...)
            user.save()

            log_action(
                user=actor,                  # quién creó
                action="user.created",
                resource="user",
                resource_id=str(user.pk),
                metadata={"email": user.email, "role_id": role_id},
            )
            return user

    Ejemplo con modelo especializado (FinancialAuditLog):

        log_action(
            audit_model=FinancialAuditLog,
            user=user,
            action="payment.approved",
            resource="payment",
            resource_id=str(payment.pk),
            metadata={"payment_id": payment.pk},
            amount=payment.amount,          # campo de FinancialAuditLog
            currency=payment.currency,      # campo de FinancialAuditLog
        )
    """
    return create_audit_entry(
        audit_model=audit_model,
        user=user,
        action=action,
        resource=resource,
        resource_id=resource_id,
        status=AuditStatus.SUCCESS,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
        **extra_fields,
    )


def log_failure(
    *,
    audit_model: AuditModel = AuditLog,
    user: Any | None = None,
    action: str,
    resource: str,
    resource_id: str = "",
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str = "",
    correlation_id: uuid.UUID | None = None,
    **extra_fields: Any,
) -> BaseAuditLog | None:
    """
    Registra un intento fallido (status=FAILURE).

    Wrapper semántico sobre create_audit_entry. Usar para intentos de acceso
    no autorizado, validaciones fallidas, errores de negocio, etc.

    Ejemplo de uso en un view (capa de presentación):

        def login_view(request):
            user = authenticate(...)
            if user is None:
                log_failure(
                    action="auth.login",
                    resource="session",
                    metadata={"reason": "invalid_credentials"},
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )
                return Response({"detail": "Credenciales inválidas."}, status=401)

    Ejemplo con modelo de seguridad (SecurityAuditLog):

        log_failure(
            audit_model=SecurityAuditLog,
            action="auth.brute_force_detected",
            resource="session",
            metadata={"attempts": 10, "window_seconds": 60},
            ip_address=ip,
            threat_level="HIGH",            # campo de SecurityAuditLog
            blocked=True,                   # campo de SecurityAuditLog
        )
    """
    return create_audit_entry(
        audit_model=audit_model,
        user=user,
        action=action,
        resource=resource,
        resource_id=resource_id,
        status=AuditStatus.FAILURE,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
        **extra_fields,
    )
