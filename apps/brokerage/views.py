"""
brokerage.views
===============
Endpoints REST del módulo brokerage.

Estado actual: CRUD básico de Client y Asset.
Autenticación: JWT (IsAuthenticated).
Permisos RBAC: reservados para iteración posterior con HasPermission.

Etiqueta Swagger: "Brokerage"
"""

from __future__ import annotations

from typing import Any, cast

from django.core.exceptions import ValidationError
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Asset, Client, ClientStatus
from .selectors import (
    get_active_assets,
    get_asset_by_id,
    get_asset_list,
    get_client_by_id,
    get_client_list,
)
from .services import (
    block_client,
    create_asset,
    create_client,
    deactivate_asset,
    reactivate_asset,
    unblock_client,
    update_client,
)


# ---------------------------------------------------------------------------
# Inline serializers (Swagger + validación de entrada)
# ---------------------------------------------------------------------------


class ClientSerializer(s.Serializer):
    id = s.IntegerField(read_only=True)
    cuit = s.CharField()
    name = s.CharField()
    status = s.ChoiceField(choices=ClientStatus.choices)
    is_active = s.BooleanField(read_only=True)
    created_at = s.DateTimeField(read_only=True)


class ClientCreateSerializer(s.Serializer):
    cuit = s.CharField(max_length=13)
    name = s.CharField(max_length=200)


class ClientUpdateSerializer(s.Serializer):
    name = s.CharField(max_length=200)


class AssetSerializer(s.Serializer):
    id = s.IntegerField(read_only=True)
    code = s.CharField()
    name = s.CharField()
    is_active = s.BooleanField()


class AssetCreateSerializer(s.Serializer):
    code = s.CharField(max_length=20)
    name = s.CharField(max_length=100, required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Shared OpenAPI building blocks
# ---------------------------------------------------------------------------

_401 = OpenApiResponse(description="No autenticado. Se requiere JWT válido en el header `Authorization: Bearer <token>`.")
_404_client = OpenApiResponse(
    response=inline_serializer(
        name="ClientNotFoundResponse",
        fields={"error": s.CharField(default="Cliente no encontrado.")},
    ),
    description="El cliente con el ID proporcionado no existe.",
)
_404_asset = OpenApiResponse(
    response=inline_serializer(
        name="AssetNotFoundResponse",
        fields={"error": s.CharField(default="Activo no encontrado.")},
    ),
    description="El activo con el ID proporcionado no existe.",
)
_400_validation = OpenApiResponse(
    response=inline_serializer(
        name="BrokerageValidationErrorResponse",
        fields={
            "cuit": s.ListField(child=s.CharField(), required=False),
            "name": s.ListField(child=s.CharField(), required=False),
            "code": s.ListField(child=s.CharField(), required=False),
        },
    ),
    description=(
        "Datos de entrada inválidos. El cuerpo incluye un objeto con los campos "
        "que fallaron y una lista de mensajes descriptivos por campo.\n\n"
        "Ejemplo: `{\"cuit\": [\"Ya existe un cliente con CUIT '20-12345678-9'.\"]}`"
    ),
)

# --- Ejemplos de respuesta reutilizables ---

_client_example = OpenApiExample(
    name="Cliente activo",
    summary="Respuesta estándar de un cliente operativo",
    value={
        "id": 3,
        "cuit": "20-12345678-9",
        "name": "Industrias Río de la Plata S.A.",
        "status": "ACTIVE",
        "is_active": True,
        "created_at": "2026-02-15T10:30:00Z",
    },
    response_only=True,
)

_client_blocked_example = OpenApiExample(
    name="Cliente bloqueado",
    summary="Cliente cuyo estado es BLOCKED — no puede operar",
    value={
        "id": 7,
        "cuit": "30-98765432-1",
        "name": "Inversiones del Sur S.R.L.",
        "status": "BLOCKED",
        "is_active": False,
        "created_at": "2026-01-10T09:00:00Z",
    },
    response_only=True,
)

_asset_active_example = OpenApiExample(
    name="Activo activo",
    summary="Instrumento habilitado para operar",
    value={
        "id": 1,
        "code": "BTC",
        "name": "Bitcoin",
        "is_active": True,
    },
    response_only=True,
)

_asset_inactive_example = OpenApiExample(
    name="Activo desactivado",
    summary="Instrumento suspendido — no acepta nuevas operaciones",
    value={
        "id": 5,
        "code": "LUNA",
        "name": "Terra Luna",
        "is_active": False,
    },
    response_only=True,
)

_ERR_CLIENT_NOT_FOUND = "Cliente no encontrado."
_ERR_ASSET_NOT_FOUND = "Activo no encontrado."


def _to_client_dict(c: Client) -> dict:
    return {
        "id": c.pk,
        "cuit": c.cuit,
        "name": c.name,
        "status": c.status,
        "is_active": c.is_active,
        "created_at": c.created_at,
    }


def _to_asset_dict(a: Asset) -> dict:
    return {"id": a.pk, "code": a.code, "name": a.name, "is_active": a.is_active}


def _validation_error(exc: ValidationError) -> Response:
    detail = exc.message_dict if hasattr(exc, "message_dict") else {"error": str(exc)}
    return Response(detail, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Client views
# ---------------------------------------------------------------------------


class ClientListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_clients_list",
        tags=["Brokerage"],
        summary="Listar todos los clientes",
        description=(
            "Retorna la lista completa de clientes registrados en el sistema de brokerage, "
            "ordenados alfabéticamente por nombre.\n\n"
            "**¿Qué es un Cliente?**\n"
            "Un cliente es una contraparte operacional identificada por su CUIT (Clave Única "
            "de Identificación Tributaria). Puede tratarse de una persona física o jurídica "
            "habilitada para realizar operaciones financieras en la plataforma.\n\n"
            "**Estados posibles:**\n"
            "- `ACTIVE` — el cliente puede operar normalmente.\n"
            "- `BLOCKED` — el cliente está suspendido y no puede generar nuevas operaciones. "
            "  El historial previo se mantiene intacto.\n\n"
            "**Nota:** este endpoint devuelve todos los clientes sin paginar. "
            "Para operaciones de alta escala, se incorporará paginación en una iteración posterior."
        ),
        responses={
            200: OpenApiResponse(
                response=ClientSerializer(many=True),
                description="Lista de clientes. Array vacío `[]` si no hay clientes registrados.",
                examples=[
                    OpenApiExample(
                        name="Lista con clientes mixtos",
                        summary="Respuesta típica con clientes activos y bloqueados",
                        value=[
                            {
                                "id": 1,
                                "cuit": "20-12345678-9",
                                "name": "Industrias Río de la Plata S.A.",
                                "status": "ACTIVE",
                                "is_active": True,
                                "created_at": "2026-02-15T10:30:00Z",
                            },
                            {
                                "id": 2,
                                "cuit": "30-98765432-1",
                                "name": "Inversiones del Sur S.R.L.",
                                "status": "BLOCKED",
                                "is_active": False,
                                "created_at": "2026-01-10T09:00:00Z",
                            },
                        ],
                        response_only=True,
                    )
                ],
            ),
            401: _401,
        },
    )
    def get(self, request: Request) -> Response:
        clients = get_client_list()
        return Response([_to_client_dict(c) for c in clients])

    @extend_schema(
        operation_id="brokerage_clients_create",
        tags=["Brokerage"],
        summary="Registrar nuevo cliente",
        description=(
            "Registra una nueva contraparte operacional en el sistema de brokerage.\n\n"
            "**Reglas de negocio:**\n"
            "- El `cuit` debe ser único en el sistema. Si ya existe un cliente con el mismo "
            "  CUIT, se retorna `400` con el detalle del conflicto.\n"
            "- El `cuit` se almacena en el formato ingresado; se recomienda el estándar "
            "  argentino `XX-XXXXXXXX-X` (ej: `20-12345678-9`).\n"
            "- El cliente se crea con estado `ACTIVE` de forma automática.\n"
            "- `name` acepta razón social o nombre completo (máx. 200 caracteres).\n\n"
            "**No confundir con el módulo de usuarios:** este endpoint registra una "
            "contraparte financiera, no una cuenta de acceso al sistema."
        ),
        request=ClientCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=ClientSerializer,
                description="Cliente creado exitosamente. Se retorna la representación completa.",
                examples=[_client_example],
            ),
            400: _400_validation,
            401: _401,
        },
    )
    def post(self, request: Request) -> Response:
        ser = ClientCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = cast(dict[str, Any], ser.validated_data)
        try:
            client = create_client(
                cuit=data["cuit"],
                name=data["name"],
            )
        except ValidationError as exc:
            return _validation_error(exc)
        return Response(_to_client_dict(client), status=status.HTTP_201_CREATED)


class ClientDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, client_id: int) -> Client | None:
        try:
            return get_client_by_id(client_id)
        except Client.DoesNotExist:
            return None

    @extend_schema(
        operation_id="brokerage_clients_retrieve",
        tags=["Brokerage"],
        summary="Obtener detalle de un cliente",
        description=(
            "Retorna la representación completa de un cliente identificado por su `id` interno.\n\n"
            "Útil para:\n"
            "- Verificar el estado actual de un cliente antes de procesar una operación.\n"
            "- Mostrar datos del cliente en pantallas de detalle o confirmación.\n\n"
            "**Nota:** si necesitas buscar por CUIT en lugar de por ID, "
            "usa el listado general y filtrá en el cliente."
        ),
        responses={
            200: OpenApiResponse(
                response=ClientSerializer,
                description="Detalle del cliente.",
                examples=[_client_example, _client_blocked_example],
            ),
            401: _401,
            404: _404_client,
        },
    )
    def get(self, request: Request, client_id: int) -> Response:
        client = self._get(client_id)
        if not client:
            return Response({"error": _ERR_CLIENT_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        return Response(_to_client_dict(client))

    @extend_schema(
        operation_id="brokerage_clients_partial_update",
        tags=["Brokerage"],
        summary="Actualizar nombre del cliente",
        description=(
            "Actualiza el campo `name` (razón social / nombre completo) de un cliente existente.\n\n"
            "**Campos modificables:**\n"
            "- `name` — nombre o razón social. Máx. 200 caracteres. No puede quedar vacío.\n\n"
            "**Campos inmutables:** `cuit`, `status`, `created_at`. "
            "Para cambiar el estado de un cliente usá los endpoints `/block/` y `/unblock/`.\n\n"
            "Este endpoint acepta actualizaciones parciales (`PATCH`): "
            "solo los campos enviados son modificados."
        ),
        request=ClientUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=ClientSerializer,
                description="Cliente actualizado. Se retorna la representación completa con el nuevo nombre.",
                examples=[_client_example],
            ),
            400: _400_validation,
            401: _401,
            404: _404_client,
        },
    )
    def patch(self, request: Request, client_id: int) -> Response:
        client = self._get(client_id)
        if not client:
            return Response({"error": _ERR_CLIENT_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        ser = ClientUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = cast(dict[str, Any], ser.validated_data)
        try:
            client = update_client(client=client, name=data.get("name"))
        except ValidationError as exc:
            return _validation_error(exc)
        return Response(_to_client_dict(client))


class ClientBlockView(APIView):
    """Bloquea un cliente activo."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_clients_block",
        tags=["Brokerage"],
        summary="Bloquear cliente",
        description=(
            "Cambia el estado del cliente a `BLOCKED`, impidiendo que genere nuevas operaciones.\n\n"
            "**Comportamiento:**\n"
            "- Si el cliente ya está `BLOCKED`, la operación es **idempotente** "
            "  (retorna `200` con el estado actual sin generar un error).\n"
            "- El historial de operaciones previas del cliente se mantiene intacto.\n"
            "- No requiere cuerpo en el request (`body` vacío o ausente).\n\n"
            "**Caso de uso típico:** suspensión preventiva por detección de actividad "
            "anómala, orden judicial, o incumplimiento de compliance."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=ClientSerializer,
                description="Cliente bloqueado. El campo `status` será `BLOCKED` e `is_active` será `false`.",
                examples=[_client_blocked_example],
            ),
            401: _401,
            404: _404_client,
        },
    )
    def post(self, request: Request, client_id: int) -> Response:
        try:
            client = get_client_by_id(client_id)
        except Client.DoesNotExist:
            return Response({"error": _ERR_CLIENT_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        client = block_client(client=client)
        return Response(_to_client_dict(client))


class ClientUnblockView(APIView):
    """Reactiva un cliente bloqueado."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_clients_unblock",
        tags=["Brokerage"],
        summary="Desbloquear cliente",
        description=(
            "Reactiva un cliente bloqueado, restaurando su estado a `ACTIVE` y "
            "habilitándolo para generar nuevas operaciones.\n\n"
            "**Comportamiento:**\n"
            "- Si el cliente ya está `ACTIVE`, la operación es **idempotente** "
            "  (retorna `200` con el estado actual sin generar un error).\n"
            "- No requiere cuerpo en el request (`body` vacío o ausente).\n\n"
            "**Caso de uso típico:** levantamiento de una suspensión tras resolución "
            "de un conflicto de compliance o corrección de datos."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=ClientSerializer,
                description="Cliente reactivado. El campo `status` será `ACTIVE` e `is_active` será `true`.",
                examples=[_client_example],
            ),
            401: _401,
            404: _404_client,
        },
    )
    def post(self, request: Request, client_id: int) -> Response:
        try:
            client = get_client_by_id(client_id)
        except Client.DoesNotExist:
            return Response({"error": _ERR_CLIENT_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        client = unblock_client(client=client)
        return Response(_to_client_dict(client))


# ---------------------------------------------------------------------------
# Asset views
# ---------------------------------------------------------------------------


class AssetListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_assets_list",
        tags=["Brokerage"],
        summary="Listar activos / instrumentos",
        description=(
            "Retorna la lista de activos (instrumentos negociables) registrados en el sistema.\n\n"
            "**¿Qué es un Activo?**\n"
            "Un activo representa un instrumento financiero o criptoactivo identificado por su "
            "símbolo de mercado (`code`). Ejemplos: `BTC` (Bitcoin), `ETH` (Ethereum), "
            "`USD` (Dólar estadounidense), `ARS` (Peso argentino).\n\n"
            "**Filtro por estado activo:**\n"
            "Pasando `?active=true` se retorna solo los activos habilitados para operar. "
            "Sin ese parámetro se retornan todos (activos e inactivos).\n\n"
            "**Ordenamiento:** alfabético por `code`."
        ),
        parameters=[
            OpenApiParameter(
                name="active",
                type=str,
                enum=["true"],
                required=False,
                description=(
                    "Si se pasa `active=true`, retorna únicamente los activos con `is_active=true`. "
                    "Omitir este parámetro retorna todos los activos sin filtrar."
                ),
            )
        ],
        responses={
            200: OpenApiResponse(
                response=AssetSerializer(many=True),
                description="Lista de activos ordenada por código. Array vacío `[]` si no hay activos.",
                examples=[
                    OpenApiExample(
                        name="Lista completa (activos e inactivos)",
                        value=[
                            {"id": 1, "code": "BTC", "name": "Bitcoin", "is_active": True},
                            {"id": 2, "code": "ETH", "name": "Ethereum", "is_active": True},
                            {"id": 3, "code": "LUNA", "name": "Terra Luna", "is_active": False},
                            {"id": 4, "code": "USDT", "name": "Tether USD", "is_active": True},
                        ],
                        response_only=True,
                    ),
                    OpenApiExample(
                        name="Solo activos (?active=true)",
                        value=[
                            {"id": 1, "code": "BTC", "name": "Bitcoin", "is_active": True},
                            {"id": 2, "code": "ETH", "name": "Ethereum", "is_active": True},
                            {"id": 4, "code": "USDT", "name": "Tether USD", "is_active": True},
                        ],
                        response_only=True,
                    ),
                ],
            ),
            401: _401,
        },
    )
    def get(self, request: Request) -> Response:
        only_active = request.query_params.get("active") == "true"
        assets = get_active_assets() if only_active else get_asset_list()
        return Response([_to_asset_dict(a) for a in assets])

    @extend_schema(
        operation_id="brokerage_assets_create",
        tags=["Brokerage"],
        summary="Registrar nuevo activo",
        description=(
            "Registra un nuevo instrumento financiero en el catálogo de activos negociables.\n\n"
            "**Reglas de negocio:**\n"
            "- El `code` (símbolo de mercado) debe ser único. Se convierte a mayúsculas "
            "  automáticamente: `btc` → `BTC`.\n"
            "- El `code` identifica el activo en todo el sistema; elegirlo con cuidado ya "
            "  que es el identificador de negocio (no el `id` interno).\n"
            "- `name` es opcional y descriptivo (ej: `Bitcoin`, `Ethereum`). "
            "  Si se omite queda en blanco.\n"
            "- El activo se crea habilitado (`is_active: true`) de forma automática.\n\n"
            "**Ejemplos de códigos válidos:** `BTC`, `ETH`, `USDT`, `ARS`, `USD`, `AL30`, `GD30`."
        ),
        request=AssetCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=AssetSerializer,
                description="Activo creado exitosamente.",
                examples=[_asset_active_example],
            ),
            400: _400_validation,
            401: _401,
        },
    )
    def post(self, request: Request) -> Response:
        ser = AssetCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = cast(dict[str, Any], ser.validated_data)
        try:
            asset = create_asset(
                code=data["code"],
                name=data.get("name", ""),
            )
        except ValidationError as exc:
            return _validation_error(exc)
        return Response(_to_asset_dict(asset), status=status.HTTP_201_CREATED)


class AssetDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, asset_id: int) -> Asset | None:
        try:
            return get_asset_by_id(asset_id)
        except Asset.DoesNotExist:
            return None

    @extend_schema(
        operation_id="brokerage_assets_retrieve",
        tags=["Brokerage"],
        summary="Obtener detalle de un activo",
        description=(
            "Retorna la representación completa de un activo identificado por su `id` interno.\n\n"
            "El campo `is_active` indica si el activo está habilitado para generar nuevas "
            "operaciones. Un activo inactivo (`is_active: false`) mantiene su historial "
            "de operaciones pero no acepta nuevas.\n\n"
            "**Tip:** para buscar un activo por símbolo de mercado en vez de por ID, "
            "combiná el listado con filtrado del lado cliente usando el campo `code`."
        ),
        responses={
            200: OpenApiResponse(
                response=AssetSerializer,
                description="Detalle del activo.",
                examples=[_asset_active_example, _asset_inactive_example],
            ),
            401: _401,
            404: _404_asset,
        },
    )
    def get(self, request: Request, asset_id: int) -> Response:
        asset = self._get(asset_id)
        if not asset:
            return Response({"error": _ERR_ASSET_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        return Response(_to_asset_dict(asset))


class AssetDeactivateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_assets_deactivate",
        tags=["Brokerage"],
        summary="Desactivar activo",
        description=(
            "Suspende un activo del catálogo, impidiendo que sea usado en nuevas operaciones.\n\n"
            "**Comportamiento:**\n"
            "- Si el activo ya está inactivo (`is_active: false`), la operación es **idempotente** "
            "  (retorna `200` con el estado actual sin generar error).\n"
            "- El historial de operaciones previas que referencian este activo se mantiene intacto.\n"
            "- No requiere cuerpo en el request.\n\n"
            "**Caso de uso típico:** suspensión regulatoria de un instrumento, "
            "deslistado de un criptoactivo del mercado, o mantenimiento temporal."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=AssetSerializer,
                description="Activo desactivado. El campo `is_active` será `false`.",
                examples=[_asset_inactive_example],
            ),
            401: _401,
            404: _404_asset,
        },
    )
    def post(self, request: Request, asset_id: int) -> Response:
        try:
            asset = get_asset_by_id(asset_id)
        except Asset.DoesNotExist:
            return Response({"error": _ERR_ASSET_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        asset = deactivate_asset(asset=asset)
        return Response(_to_asset_dict(asset))


class AssetReactivateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_assets_reactivate",
        tags=["Brokerage"],
        summary="Reactivar activo",
        description=(
            "Habilita nuevamente un activo previamente desactivado, permitiendo "
            "que sea usado en nuevas operaciones.\n\n"
            "**Comportamiento:**\n"
            "- Si el activo ya está activo (`is_active: true`), la operación es **idempotente** "
            "  (retorna `200` con el estado actual sin generar error).\n"
            "- No requiere cuerpo en el request.\n\n"
            "**Caso de uso típico:** reincorporación de un instrumento al mercado tras el "
            "levantamiento de una suspensión regulatoria o relistado."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=AssetSerializer,
                description="Activo reactivado. El campo `is_active` será `true`.",
                examples=[_asset_active_example],
            ),
            401: _401,
            404: _404_asset,
        },
    )
    def post(self, request: Request, asset_id: int) -> Response:
        try:
            asset = get_asset_by_id(asset_id)
        except Asset.DoesNotExist:
            return Response({"error": _ERR_ASSET_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        asset = reactivate_asset(asset=asset)
        return Response(_to_asset_dict(asset))

