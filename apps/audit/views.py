"""
audit.views
===========
Endpoints de lectura para el histórico de auditoría.

Diseño:
- Solo lectura — no hay POST/PATCH/DELETE.
- Requieren autenticación JWT + permiso RBAC `auditoria.view`.
- Paginación automática via DEFAULT_PAGINATION_CLASS del proyecto.
- Filtros via AuditLogFilter (action, resource, status, user_id, timestamp, correlation_id).
- Documentación OpenAPI completa via drf-spectacular (@extend_schema).

URLs:
    GET  /api/audit/logs/        — lista paginada con filtros
    GET  /api/audit/logs/{id}/   — detalle de un log específico

Uso típico:
    - Panel de administración para investigar eventos de seguridad.
    - Auditoría de acciones de un usuario específico (?user_id=5).
    - Investigación de incidentes por ventana de tiempo (?timestamp__gte=...).
    - Correlación de eventos de una operación compuesta (?correlation_id=...).
"""

from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import filters as drf_filters
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authorization.permissions import HasPermission

from .filters import AuditLogFilter
from .models import AuditLog
from .selectors import get_audit_log_by_id, get_audit_log_list
from .serializers import AuditLogSerializer

# ---------------------------------------------------------------------------
# Shared schema snippets
# ---------------------------------------------------------------------------

_audit_log_example = OpenApiExample(
    name="AuditLog ejemplo",
    value={
        "id": 1,
        "user": {"id": 5, "email": "admin@example.com"},
        "action": "user.deactivated",
        "resource": "user",
        "resource_id": "12",
        "status": "SUCCESS",
        "status_display": "Exitoso",
        "metadata": {"reason": "inactive policy"},
        "ip_address": "192.168.1.10",
        "user_agent": "Mozilla/5.0",
        "timestamp": "2026-02-20T14:32:00Z",
        "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    },
    response_only=True,
)

_not_found_response = inline_serializer(
    name="AuditNotFoundResponse",
    fields={"detail": drf_serializers.CharField(default="No encontrado.")},
)

_forbidden_response = inline_serializer(
    name="AuditForbiddenResponse",
    fields={"detail": drf_serializers.CharField(default="Permiso denegado. Se requiere: 'auditoria.view'.")},
)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["Auditoría"],
    summary="Listar logs de auditoría",
    description=(
        "Retorna la lista paginada de todos los registros de auditoría del sistema.\n\n"
        "**Requiere:** autenticación JWT + permiso `auditoria.view` (rol Administrador).\n\n"
        "**Filtros disponibles:**\n"
        "- `action` — contiene (ej: `?action=login`)\n"
        "- `resource` — contiene (ej: `?resource=user`)\n"
        "- `status` — `SUCCESS` o `FAILURE`\n"
        "- `user_id` — ID numérico del usuario\n"
        "- `timestamp__gte` — fecha/hora mínima (ISO 8601)\n"
        "- `timestamp__lte` — fecha/hora máxima (ISO 8601)\n"
        "- `correlation_id` — UUID exacto\n\n"
        "**Ordenamiento:** por defecto `-timestamp` (más reciente primero). "
        "Se puede invertir con `?ordering=timestamp`.\n\n"
        "**Nota de seguridad:** el campo `metadata` nunca contiene contraseñas, "
        "tokens ni datos sensibles por convención del servicio de escritura."
    ),
    parameters=[
        OpenApiParameter("action", str, description="Filtrar por nombre de acción (contiene)"),
        OpenApiParameter("resource", str, description="Filtrar por tipo de recurso (contiene)"),
        OpenApiParameter("status", str, enum=["SUCCESS", "FAILURE"], description="Estado del evento"),
        OpenApiParameter("user_id", int, description="ID del usuario ejecutor"),
        OpenApiParameter("timestamp__gte", str, description="Timestamp mínimo (ISO 8601)"),
        OpenApiParameter("timestamp__lte", str, description="Timestamp máximo (ISO 8601)"),
        OpenApiParameter("correlation_id", str, description="UUID de correlación exacto"),
        OpenApiParameter("ordering", str, description="Campo de ordenamiento. Ej: `-timestamp`, `action`"),
    ],
    responses={
        200: OpenApiResponse(
            response=AuditLogSerializer(many=True),
            description="Lista paginada de logs.",
            examples=[_audit_log_example],
        ),
        401: OpenApiResponse(description="No autenticado."),
        403: OpenApiResponse(
            response=_forbidden_response,
            description="Sin permiso `auditoria.view`.",
        ),
    },
)
class AuditLogListView(APIView):
    """
    GET /api/audit/logs/
    Lista paginada de todos los registros de auditoría.
    Requiere permiso `auditoria.view`.
    """

    permission_classes = [HasPermission("auditoria.view")]
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]
    filterset_class = AuditLogFilter
    ordering_fields = ["timestamp", "action", "resource", "status"]
    ordering = ["-timestamp"]

    def get(self, request: Request) -> Response:
        qs = get_audit_log_list()

        # Aplicar filtros manuales (DjangoFilterBackend no se aplica automáticamente en APIView)
        filterset = AuditLogFilter(request.query_params, queryset=qs)
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)

        qs = filterset.qs

        # Ordering
        ordering_param = request.query_params.get("ordering", "-timestamp")
        allowed = {"timestamp", "-timestamp", "action", "-action", "resource", "-resource", "status", "-status"}
        if ordering_param in allowed:
            qs = qs.order_by(ordering_param)

        serializer = AuditLogSerializer(qs, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=["Auditoría"],
    summary="Obtener log de auditoría por ID",
    description=(
        "Retorna el detalle completo de un registro de auditoría específico.\n\n"
        "**Requiere:** autenticación JWT + permiso `auditoria.view` (rol Administrador).\n\n"
        "Útil para investigar un evento específico a partir de su ID o al "
        "correlacionar un `correlation_id` encontrado en otro log."
    ),
    responses={
        200: OpenApiResponse(
            response=AuditLogSerializer,
            description="Detalle del log.",
            examples=[_audit_log_example],
        ),
        401: OpenApiResponse(description="No autenticado."),
        403: OpenApiResponse(
            response=_forbidden_response,
            description="Sin permiso `auditoria.view`.",
        ),
        404: OpenApiResponse(
            response=_not_found_response,
            description="Log no encontrado.",
        ),
    },
)
class AuditLogDetailView(APIView):
    """
    GET /api/audit/logs/{id}/
    Detalle de un registro de auditoría específico.
    Requiere permiso `auditoria.view`.
    """

    permission_classes = [HasPermission("auditoria.view")]

    def get(self, request: Request, log_id: int) -> Response:
        log = get_audit_log_by_id(log_id)
        if log is None:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AuditLogSerializer(log)
        return Response(serializer.data)
