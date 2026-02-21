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

_audit_log_success_example = OpenApiExample(
    name="Login exitoso",
    summary="Evento de autenticación correcta (status=SUCCESS)",
    value={
        "id": 1,
        "user": {"id": 5, "email": "admin@kaizen.com"},
        "action": "user.login",
        "resource": "user",
        "resource_id": "5",
        "status": "SUCCESS",
        "status_display": "Exitoso",
        "metadata": {"method": "jwt", "ip_country": "AR"},
        "ip_address": "192.168.1.10",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "timestamp": "2026-02-20T14:32:00Z",
        "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    },
    response_only=True,
)

_audit_log_failure_example = OpenApiExample(
    name="Intento de login fallido",
    summary="Evento de autenticación rechazada (status=FAILURE)",
    value={
        "id": 42,
        "user": None,
        "action": "user.login",
        "resource": "user",
        "resource_id": None,
        "status": "FAILURE",
        "status_display": "Fallido",
        "metadata": {"reason": "invalid_credentials", "attempts": 3},
        "ip_address": "203.0.113.77",
        "user_agent": "python-requests/2.31.0",
        "timestamp": "2026-02-20T15:01:00Z",
        "correlation_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    },
    response_only=True,
)

_audit_log_deactivation_example = OpenApiExample(
    name="Desactivación de usuario",
    summary="Evento de gestión administrativa sobre un usuario",
    value={
        "id": 88,
        "user": {"id": 1, "email": "superadmin@kaizen.com"},
        "action": "user.deactivated",
        "resource": "user",
        "resource_id": "12",
        "status": "SUCCESS",
        "status_display": "Exitoso",
        "metadata": {"reason": "inactive_policy", "previous_status": "ACTIVE"},
        "ip_address": "10.0.0.5",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "timestamp": "2026-02-21T09:15:00Z",
        "correlation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
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

_bad_filter_response = inline_serializer(
    name="AuditBadFilterResponse",
    fields={
        "status": drf_serializers.ListField(
            child=drf_serializers.CharField(),
            default=["Seleccione una opción válida. \"INVALID\" no está disponible."],
            required=False,
        ),
        "user_id": drf_serializers.ListField(
            child=drf_serializers.CharField(),
            default=["Introduzca un número entero válido."],
            required=False,
        ),
    },
)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


@extend_schema(
    operation_id="audit_logs_list",
    tags=["Auditoría"],
    summary="Listar logs de auditoría",
    description=(
        "Retorna la lista completa de eventos de auditoría registrados en el sistema, "
        "ordenados por defecto del más reciente al más antiguo.\n\n"
        "**Acceso:** JWT válido + permiso `auditoria.view` (rol Administrador). "
        "Sin ese permiso se retorna `403`.\n\n"
        "---\n\n"
        "### Filtros disponibles\n\n"
        "| Parámetro | Tipo | Coincidencia | Ejemplo |\n"
        "|---|---|---|---|\n"
        "| `action` | string | contiene | `?action=login` |\n"
        "| `resource` | string | contiene | `?resource=user` |\n"
        "| `status` | enum | exacto | `?status=FAILURE` |\n"
        "| `user_id` | int | exacto | `?user_id=5` |\n"
        "| `timestamp__gte` | ISO 8601 | mayor o igual | `?timestamp__gte=2026-02-01T00:00:00Z` |\n"
        "| `timestamp__lte` | ISO 8601 | menor o igual | `?timestamp__lte=2026-02-21T23:59:59Z` |\n"
        "| `correlation_id` | UUID | exacto | `?correlation_id=550e8400-...` |\n\n"
        "Los filtros son acumulables: "
        "`?action=login&status=FAILURE&user_id=5` devuelve los logins fallidos del usuario 5.\n\n"
        "---\n\n"
        "### Ordenamiento\n\n"
        "Parámetro `ordering`. Valores válidos:\n"
        "- `-timestamp` _(default)_ — más reciente primero\n"
        "- `timestamp` — más antiguo primero\n"
        "- `action`, `-action` — alfabético por nombre de acción\n"
        "- `resource`, `-resource` — alfabético por tipo de recurso\n"
        "- `status`, `-status` — SUCCESS antes que FAILURE (o al revés)\n\n"
        "---\n\n"
        "### Seguridad del campo `metadata`\n\n"
        "El campo `metadata` es un JSON libre pero **nunca** contiene contraseñas, "
        "tokens, ni PII sensible. Por convención del servicio de escritura, "
        "solo se almacena contexto operacional (razón de la acción, valores previos, etc.).\n\n"
        "---\n\n"
        "### Formato de `user`\n\n"
        "El campo `user` puede ser `null` para acciones del sistema o eventos anónimos "
        "(ej: intentos de login con credenciales inexistentes)."
    ),
    parameters=[
        OpenApiParameter(
            "action",
            str,
            required=False,
            description=(
                "Filtrar por nombre de acción (búsqueda parcial). "
                "Convención del sistema: `<recurso>.<verbo>`. "
                "Ejemplos: `user.login`, `user.deactivated`, `brokerage.client.blocked`."
            ),
        ),
        OpenApiParameter(
            "resource",
            str,
            required=False,
            description=(
                "Filtrar por tipo de recurso afectado (búsqueda parcial). "
                "Ejemplos: `user`, `brokerage`, `asset`."
            ),
        ),
        OpenApiParameter(
            "status",
            str,
            required=False,
            enum=["SUCCESS", "FAILURE"],
            description=(
                "Filtrar por resultado del evento. "
                "`SUCCESS` = operación completada. `FAILURE` = operación rechazada o con error."
            ),
        ),
        OpenApiParameter(
            "user_id",
            int,
            required=False,
            description=(
                "Filtrar por ID exacto del usuario que ejecutó la acción. "
                "Útil para auditar todas las acciones de un usuario específico."
            ),
        ),
        OpenApiParameter(
            "timestamp__gte",
            str,
            required=False,
            description=(
                "Timestamp mínimo en formato ISO 8601 (UTC recomendado). "
                "Retorna eventos desde esta fecha/hora inclusive. "
                "Ejemplo: `2026-02-01T00:00:00Z`."
            ),
        ),
        OpenApiParameter(
            "timestamp__lte",
            str,
            required=False,
            description=(
                "Timestamp máximo en formato ISO 8601 (UTC recomendado). "
                "Retorna eventos hasta esta fecha/hora inclusive. "
                "Ejemplo: `2026-02-21T23:59:59Z`."
            ),
        ),
        OpenApiParameter(
            "correlation_id",
            str,
            required=False,
            description=(
                "UUID de correlación exacto. Permite recuperar todos los eventos "
                "asociados a una misma operación compuesta (ej: onboarding de usuario "
                "que dispara múltiples logs con el mismo `correlation_id`)."
            ),
        ),
        OpenApiParameter(
            "ordering",
            str,
            required=False,
            description=(
                "Campo de ordenamiento. Prefijo `-` para orden descendente. "
                "Valores: `timestamp`, `-timestamp` _(default)_, `action`, `-action`, "
                "`resource`, `-resource`, `status`, `-status`."
            ),
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=AuditLogSerializer(many=True),
            description="Lista de logs de auditoría. Array vacío `[]` si no hay registros que cumplan los filtros.",
            examples=[
                _audit_log_success_example,
                _audit_log_failure_example,
                _audit_log_deactivation_example,
            ],
        ),
        400: OpenApiResponse(
            response=_bad_filter_response,
            description=(
                "Parámetros de filtrado inválidos. "
                "El cuerpo incluye los campos con error y los mensajes descriptivos."
            ),
        ),
        401: OpenApiResponse(
            description="No autenticado. Se requiere JWT válido en el header `Authorization: Bearer <token>`."
        ),
        403: OpenApiResponse(
            response=_forbidden_response,
            description="Sin permiso `auditoria.view`. Solo usuarios con rol Administrador pueden acceder.",
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
    operation_id="audit_logs_retrieve",
    tags=["Auditoría"],
    summary="Obtener log de auditoría por ID",
    description=(
        "Retorna el detalle completo de un registro de auditoría identificado por su `id` interno.\n\n"
        "**Acceso:** JWT válido + permiso `auditoria.view` (rol Administrador).\n\n"
        "---\n\n"
        "### Cuándo usar este endpoint\n\n"
        "- **Investigación de incidentes:** cuando tenés el ID de un log específico "
        "  y necesitás ver todos sus detalles (metadata completa, user agent, IP).\n"
        "- **Correlación de eventos:** cada log tiene un `correlation_id` (UUID). "
        "  Si encontrás este ID en otro sistema o log, podés volver al listado con "
        "  `?correlation_id=<uuid>` para recuperar todos los eventos de esa operación.\n"
        "- **Auditoría puntual:** para mostrar el detalle de un evento en un panel "
        "  de administración al hacer click en una fila del listado.\n\n"
        "---\n\n"
        "### Campos clave de la respuesta\n\n"
        "| Campo | Descripción |\n"
        "|---|---|\n"
        "| `user` | Objeto `{id, email}` o `null` para eventos anónimos/del sistema |\n"
        "| `action` | Acción ejecutada. Convención: `<recurso>.<verbo>` |\n"
        "| `resource` | Tipo de entidad afectada |\n"
        "| `resource_id` | ID de la instancia específica afectada (string o null) |\n"
        "| `status` | `SUCCESS` o `FAILURE` |\n"
        "| `status_display` | Etiqueta legible: `Exitoso` o `Fallido` |\n"
        "| `metadata` | JSON libre con contexto del evento (sin datos sensibles) |\n"
        "| `ip_address` | IP de origen de la request |\n"
        "| `user_agent` | Cliente HTTP que generó el evento |\n"
        "| `timestamp` | Fecha y hora UTC del evento (inmutable) |\n"
        "| `correlation_id` | UUID para correlacionar eventos de una misma operación compuesta |\n\n"
        "**Nota:** los registros de auditoría son inmutables. No existe endpoint para "
        "modificar ni eliminar logs."
    ),
    responses={
        200: OpenApiResponse(
            response=AuditLogSerializer,
            description="Detalle completo del log de auditoría.",
            examples=[
                _audit_log_success_example,
                _audit_log_failure_example,
                _audit_log_deactivation_example,
            ],
        ),
        401: OpenApiResponse(
            description="No autenticado. Se requiere JWT válido en el header `Authorization: Bearer <token>`."
        ),
        403: OpenApiResponse(
            response=_forbidden_response,
            description="Sin permiso `auditoria.view`. Solo usuarios con rol Administrador pueden acceder.",
        ),
        404: OpenApiResponse(
            response=_not_found_response,
            description="No existe ningún log con el `id` proporcionado.",
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
