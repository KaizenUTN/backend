"""
trading.views
=============
Endpoints REST del módulo trading.

Cubre: Client, Asset, FiatCurrency, Order, Transaction.
Autenticación: JWT (IsAuthenticated).
Permisos RBAC: reservados para iteración posterior con HasPermission.

Etiqueta Swagger: "Brokerage"
"""

from __future__ import annotations

from decimal import Decimal
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

from .models import (
    Asset,
    Client,
    ClientStatus,
    FiatCurrency,
    Order,
    OrderStatus,
    Transaction,
    TransactionType,
)
from .selectors import (
    get_active_assets,
    get_active_fiat_currencies,
    get_asset_by_id,
    get_asset_list,
    get_client_by_id,
    get_client_list,
    get_fiat_currency_by_id,
    get_fiat_currency_list,
    get_order_by_id,
    get_order_list,
    get_transaction_by_id,
    get_transaction_list,
)
from .services import (
    block_client,
    cancel_order,
    create_asset,
    create_client,
    create_fiat_currency,
    create_order,
    create_transaction,
    deactivate_asset,
    deactivate_fiat_currency,
    reactivate_asset,
    reactivate_fiat_currency,
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
    email = s.EmailField(allow_blank=True)
    status = s.ChoiceField(choices=ClientStatus.choices)
    is_active = s.BooleanField(read_only=True)
    created_at = s.DateTimeField(read_only=True)


class ClientCreateSerializer(s.Serializer):
    cuit = s.CharField(max_length=13)
    name = s.CharField(max_length=200)
    email = s.EmailField(required=False, allow_blank=True, default="")


class ClientUpdateSerializer(s.Serializer):
    name = s.CharField(max_length=200, required=False)
    email = s.EmailField(required=False, allow_blank=True)


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
        "email": c.email,
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
        tags=["Trading"],
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
        tags=["Trading"],
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
                email=data.get("email", ""),
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
        tags=["Trading"],
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
        tags=["Trading"],
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
            client = update_client(
                client=client,
                name=data.get("name"),
                email=data.get("email"),
            )
        except ValidationError as exc:
            return _validation_error(exc)
        return Response(_to_client_dict(client))


class ClientBlockView(APIView):
    """Bloquea un cliente activo."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_clients_block",
        tags=["Trading"],
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
        tags=["Trading"],
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
        tags=["Trading"],
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
        tags=["Trading"],
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
        tags=["Trading"],
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
        tags=["Trading"],
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
        tags=["Trading"],
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


# ---------------------------------------------------------------------------
# FiatCurrency views
# ---------------------------------------------------------------------------

_ERR_FIAT_NOT_FOUND = "Moneda fiat no encontrada."

_404_fiat = OpenApiResponse(
    response=inline_serializer(
        name="FiatNotFoundResponse",
        fields={"error": s.CharField(default="Moneda fiat no encontrada.")},
    ),
    description="La moneda fiat con el ID proporcionado no existe.",
)


class FiatCurrencySerializer(s.Serializer):
    id = s.IntegerField(read_only=True)
    code = s.CharField()
    name = s.CharField()
    is_active = s.BooleanField()


class FiatCurrencyCreateSerializer(s.Serializer):
    code = s.CharField(max_length=10)
    name = s.CharField(max_length=50, required=False, allow_blank=True, default="")


def _to_fiat_dict(f: FiatCurrency) -> dict:
    return {"id": f.pk, "code": f.code, "name": f.name, "is_active": f.is_active}


_fiat_ars_example = OpenApiExample(
    name="ARS activo",
    value={"id": 1, "code": "ARS", "name": "Peso Argentino", "is_active": True},
    response_only=True,
)

_fiat_usd_example = OpenApiExample(
    name="USD activo",
    value={"id": 2, "code": "USD", "name": "Dólar Estadounidense", "is_active": True},
    response_only=True,
)


class FiatCurrencyListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_fiat_list",
        tags=["Trading"],
        summary="Listar monedas fiat",
        description=(
            "Retorna la lista de monedas fiat de liquidación registradas.\n\n"
            "Pasando `?active=true` se retornan sólo las activas."
        ),
        parameters=[
            OpenApiParameter(
                name="active",
                type=str,
                enum=["true"],
                required=False,
                description="Filtra sólo monedas fiat activas.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=FiatCurrencySerializer(many=True),
                description="Lista de monedas fiat.",
                examples=[
                    OpenApiExample(
                        name="Lista completa",
                        value=[
                            {"id": 1, "code": "ARS", "name": "Peso Argentino", "is_active": True},
                            {"id": 2, "code": "USD", "name": "Dólar Estadounidense", "is_active": True},
                        ],
                        response_only=True,
                    )
                ],
            ),
            401: _401,
        },
    )
    def get(self, request: Request) -> Response:
        only_active = request.query_params.get("active") == "true"
        fiats = get_active_fiat_currencies() if only_active else get_fiat_currency_list()
        return Response([_to_fiat_dict(f) for f in fiats])

    @extend_schema(
        operation_id="brokerage_fiat_create",
        tags=["Trading"],
        summary="Registrar moneda fiat",
        description=(
            "Registra una nueva moneda fiat de liquidación.\n\n"
            "El `code` (ISO 4217) debe ser único. Se convierte a mayúsculas automáticamente."
        ),
        request=FiatCurrencyCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=FiatCurrencySerializer,
                description="Moneda fiat creada.",
                examples=[_fiat_ars_example],
            ),
            400: _400_validation,
            401: _401,
        },
    )
    def post(self, request: Request) -> Response:
        ser = FiatCurrencyCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = cast(dict[str, Any], ser.validated_data)
        try:
            fiat = create_fiat_currency(code=data["code"], name=data.get("name", ""))
        except ValidationError as exc:
            return _validation_error(exc)
        return Response(_to_fiat_dict(fiat), status=status.HTTP_201_CREATED)


class FiatCurrencyDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, fiat_id: int) -> FiatCurrency | None:
        try:
            return get_fiat_currency_by_id(fiat_id)
        except FiatCurrency.DoesNotExist:
            return None

    @extend_schema(
        operation_id="brokerage_fiat_retrieve",
        tags=["Trading"],
        summary="Obtener detalle de moneda fiat",
        responses={
            200: OpenApiResponse(response=FiatCurrencySerializer, examples=[_fiat_ars_example, _fiat_usd_example]),
            401: _401,
            404: _404_fiat,
        },
    )
    def get(self, request: Request, fiat_id: int) -> Response:
        fiat = self._get(fiat_id)
        if not fiat:
            return Response({"error": _ERR_FIAT_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        return Response(_to_fiat_dict(fiat))


class FiatCurrencyDeactivateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_fiat_deactivate",
        tags=["Trading"],
        summary="Desactivar moneda fiat",
        description="Suspende una moneda fiat. Idempotente si ya está inactiva.",
        request=None,
        responses={
            200: OpenApiResponse(response=FiatCurrencySerializer, description="Moneda fiat desactivada."),
            401: _401,
            404: _404_fiat,
        },
    )
    def post(self, request: Request, fiat_id: int) -> Response:
        try:
            fiat = get_fiat_currency_by_id(fiat_id)
        except FiatCurrency.DoesNotExist:
            return Response({"error": _ERR_FIAT_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        fiat = deactivate_fiat_currency(fiat_currency=fiat)
        return Response(_to_fiat_dict(fiat))


class FiatCurrencyReactivateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_fiat_reactivate",
        tags=["Trading"],
        summary="Reactivar moneda fiat",
        description="Habilita nuevamente una moneda fiat. Idempotente si ya está activa.",
        request=None,
        responses={
            200: OpenApiResponse(response=FiatCurrencySerializer, description="Moneda fiat reactivada."),
            401: _401,
            404: _404_fiat,
        },
    )
    def post(self, request: Request, fiat_id: int) -> Response:
        try:
            fiat = get_fiat_currency_by_id(fiat_id)
        except FiatCurrency.DoesNotExist:
            return Response({"error": _ERR_FIAT_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        fiat = reactivate_fiat_currency(fiat_currency=fiat)
        return Response(_to_fiat_dict(fiat))


# ---------------------------------------------------------------------------
# Order views
# ---------------------------------------------------------------------------

_ERR_ORDER_NOT_FOUND = "Orden no encontrada."

_404_order = OpenApiResponse(
    response=inline_serializer(
        name="OrderNotFoundResponse",
        fields={"error": s.CharField(default="Orden no encontrada.")},
    ),
    description="La orden con el ID proporcionado no existe.",
)


class OrderSerializer(s.Serializer):
    id = s.IntegerField(read_only=True)
    client_id = s.IntegerField(source="client.pk", read_only=True)
    client_cuit = s.CharField(source="client.cuit", read_only=True)
    asset_code = s.CharField(source="asset.code", read_only=True)
    fiat_currency_code = s.CharField(source="fiat_currency.code", read_only=True)
    transaction_type = s.CharField()
    limit_price = s.DecimalField(max_digits=20, decimal_places=8)
    quantity = s.DecimalField(max_digits=20, decimal_places=8)
    notional = s.DecimalField(max_digits=30, decimal_places=8, read_only=True)
    status = s.CharField()
    created_at = s.DateTimeField(read_only=True)
    updated_at = s.DateTimeField(read_only=True)


class OrderCreateSerializer(s.Serializer):
    client_id = s.IntegerField()
    asset_id = s.IntegerField()
    fiat_currency_id = s.IntegerField()
    transaction_type = s.ChoiceField(choices=TransactionType.choices)
    limit_price = s.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=Decimal("0.00000001"),
    )
    quantity = s.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=Decimal("0.00000001"),
    )


def _to_order_dict(o: Order) -> dict:
    return {
        "id": o.pk,
        "client_id": o.client_id,
        "client_cuit": o.client.cuit,
        "asset_code": o.asset.code,
        "fiat_currency_code": o.fiat_currency.code,
        "transaction_type": o.transaction_type,
        "limit_price": str(o.limit_price),
        "quantity": str(o.quantity),
        "notional": str(o.notional),
        "status": o.status,
        "created_at": o.created_at,
        "updated_at": o.updated_at,
    }


_order_example = OpenApiExample(
    name="Orden de compra pendiente",
    value={
        "id": 1,
        "client_id": 3,
        "client_cuit": "20-12345678-9",
        "asset_code": "BTC",
        "fiat_currency_code": "ARS",
        "transaction_type": "BUY",
        "limit_price": "50000000.00000000",
        "quantity": "0.01000000",
        "notional": "500000.00000000",
        "status": "PENDING",
        "created_at": "2026-02-20T14:30:00Z",
        "updated_at": "2026-02-20T14:30:00Z",
    },
    response_only=True,
)


class OrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_orders_list",
        tags=["Trading"],
        summary="Listar órdenes",
        description=(
            "Retorna todas las órdenes registradas, ordenadas por fecha descendente.\n\n"
            "Una **Orden** representa una intención de compra/venta a precio límite "
            "antes de ser ejecutada. Una orden puede derivar en cero, una o múltiples "
            "Transacciones (ejecución parcial)."
        ),
        responses={
            200: OpenApiResponse(
                response=OrderSerializer(many=True),
                description="Lista de órdenes.",
            ),
            401: _401,
        },
    )
    def get(self, request: Request) -> Response:
        orders = get_order_list()
        return Response([_to_order_dict(o) for o in orders])

    @extend_schema(
        operation_id="brokerage_orders_create",
        tags=["Trading"],
        summary="Crear orden",
        description=(
            "Crea una nueva orden de compra/venta a precio límite.\n\n"
            "**Validaciones:**\n"
            "- El cliente debe estar en estado `ACTIVE`.\n"
            "- El activo debe estar activo (`is_active=true`).\n"
            "- La moneda fiat debe estar activa.\n"
            "- `limit_price` y `quantity` deben ser mayores a cero."
        ),
        request=OrderCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=OrderSerializer,
                description="Orden creada con estado `PENDING`.",
                examples=[_order_example],
            ),
            400: _400_validation,
            401: _401,
        },
    )
    def post(self, request: Request) -> Response:
        ser = OrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = cast(dict[str, Any], ser.validated_data)

        try:
            client = get_client_by_id(data["client_id"])
        except Client.DoesNotExist:
            return Response({"client_id": ["Cliente no encontrado."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            asset = get_asset_by_id(data["asset_id"])
        except Asset.DoesNotExist:
            return Response({"asset_id": ["Activo no encontrado."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            fiat = get_fiat_currency_by_id(data["fiat_currency_id"])
        except FiatCurrency.DoesNotExist:
            return Response({"fiat_currency_id": ["Moneda fiat no encontrada."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = create_order(
                client=client,
                asset=asset,
                fiat_currency=fiat,
                transaction_type=data["transaction_type"],
                limit_price=data["limit_price"],
                quantity=data["quantity"],
            )
        except ValidationError as exc:
            return _validation_error(exc)
        return Response(_to_order_dict(order), status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, order_id: int) -> Order | None:
        try:
            return get_order_by_id(order_id)
        except Order.DoesNotExist:
            return None

    @extend_schema(
        operation_id="brokerage_orders_retrieve",
        tags=["Trading"],
        summary="Obtener detalle de una orden",
        responses={
            200: OpenApiResponse(response=OrderSerializer, examples=[_order_example]),
            401: _401,
            404: _404_order,
        },
    )
    def get(self, request: Request, order_id: int) -> Response:
        order = self._get(order_id)
        if not order:
            return Response({"error": _ERR_ORDER_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        return Response(_to_order_dict(order))


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_orders_cancel",
        tags=["Trading"],
        summary="Cancelar orden",
        description=(
            "Cancela una orden en estado `PENDING` o `PARTIAL`.\n\n"
            "No se puede cancelar una orden `FILLED` o ya `CANCELLED`."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=OrderSerializer,
                description="Orden cancelada. El campo `status` será `CANCELLED`.",
            ),
            400: OpenApiResponse(
                response=inline_serializer(
                    name="OrderCancelError",
                    fields={"status": s.ListField(child=s.CharField())},
                ),
                description="La orden no puede cancelarse en su estado actual.",
            ),
            401: _401,
            404: _404_order,
        },
    )
    def post(self, request: Request, order_id: int) -> Response:
        try:
            order = get_order_by_id(order_id)
        except Order.DoesNotExist:
            return Response({"error": _ERR_ORDER_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        try:
            order = cancel_order(order=order)
        except ValidationError as exc:
            return _validation_error(exc)
        return Response(_to_order_dict(order))


# ---------------------------------------------------------------------------
# Transaction views
# ---------------------------------------------------------------------------

_ERR_TX_NOT_FOUND = "Transacción no encontrada."

_404_tx = OpenApiResponse(
    response=inline_serializer(
        name="TxNotFoundResponse",
        fields={"error": s.CharField(default="Transacción no encontrada.")},
    ),
    description="La transacción con el ID proporcionado no existe.",
)


class TransactionSerializer(s.Serializer):
    id = s.IntegerField(read_only=True)
    client_id = s.IntegerField(source="client.pk", read_only=True)
    client_cuit = s.CharField(source="client.cuit", read_only=True)
    order_id = s.IntegerField(source="order.pk", allow_null=True, read_only=True)
    asset_code = s.CharField(source="asset.code", read_only=True)
    fiat_currency_code = s.CharField(source="fiat_currency.code", read_only=True)
    transaction_type = s.CharField()
    unit_price = s.DecimalField(max_digits=20, decimal_places=8)
    quantity = s.DecimalField(max_digits=20, decimal_places=8)
    total = s.DecimalField(max_digits=30, decimal_places=8, read_only=True)
    status = s.CharField()
    blockchain_hash = s.CharField(allow_null=True, allow_blank=True)
    created_at = s.DateTimeField(read_only=True)


class TransactionCreateSerializer(s.Serializer):
    client_id = s.IntegerField()
    asset_id = s.IntegerField()
    fiat_currency_id = s.IntegerField()
    transaction_type = s.ChoiceField(choices=TransactionType.choices)
    unit_price = s.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=Decimal("0.00000001"),
    )
    quantity = s.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=Decimal("0.00000001"),
    )
    order_id = s.IntegerField(required=False, allow_null=True, default=None)
    blockchain_hash = s.CharField(
        max_length=255, required=False, allow_blank=True, allow_null=True, default=None
    )


def _to_tx_dict(t: Transaction) -> dict:
    return {
        "id": t.pk,
        "client_id": t.client_id,
        "client_cuit": t.client.cuit,
        "order_id": t.order_id,
        "asset_code": t.asset.code,
        "fiat_currency_code": t.fiat_currency.code,
        "transaction_type": t.transaction_type,
        "unit_price": str(t.unit_price),
        "quantity": str(t.quantity),
        "total": str(t.total),
        "status": t.status,
        "blockchain_hash": t.blockchain_hash,
        "created_at": t.created_at,
    }


_tx_example = OpenApiExample(
    name="Compra de BTC",
    value={
        "id": 1,
        "client_id": 3,
        "client_cuit": "20-12345678-9",
        "order_id": 1,
        "asset_code": "BTC",
        "fiat_currency_code": "ARS",
        "transaction_type": "BUY",
        "unit_price": "50000000.00000000",
        "quantity": "0.01000000",
        "total": "500000.00000000",
        "status": "CONFIRMED",
        "blockchain_hash": None,
        "created_at": "2026-02-20T14:35:00Z",
    },
    response_only=True,
)


class TransactionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="brokerage_transactions_list",
        tags=["Trading"],
        summary="Listar transacciones",
        description=(
            "Retorna todas las transacciones registradas, ordenadas por fecha descendente.\n\n"
            "Una **Transacción** es un hecho contable ejecutado e **inmutable**. "
            "Representa la liquidación real de una operación financiera. "
            "El campo `total` (precio unitario × cantidad) se calcula en tiempo real "
            "y no está almacenado en la base de datos."
        ),
        responses={
            200: OpenApiResponse(
                response=TransactionSerializer(many=True),
                description="Lista de transacciones.",
            ),
            401: _401,
        },
    )
    def get(self, request: Request) -> Response:
        txs = get_transaction_list()
        return Response([_to_tx_dict(t) for t in txs])

    @extend_schema(
        operation_id="brokerage_transactions_create",
        tags=["Trading"],
        summary="Registrar transacción",
        description=(
            "Registra una nueva transacción contable ejecutada.\n\n"
            "**Inmutabilidad:** una vez creada, la transacción no puede modificarse ni eliminarse. "
            "Para revertir una operación, crear una nueva transacción de signo contrario.\n\n"
            "**Validaciones:**\n"
            "- El cliente debe estar en estado `ACTIVE`.\n"
            "- `unit_price` y `quantity` deben ser mayores a cero.\n"
            "- `order_id` es opcional (transacciones OTC o directas sin orden previa)."
        ),
        request=TransactionCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=TransactionSerializer,
                description="Transacción registrada con estado `CONFIRMED`.",
                examples=[_tx_example],
            ),
            400: _400_validation,
            401: _401,
        },
    )
    def post(self, request: Request) -> Response:
        ser = TransactionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = cast(dict[str, Any], ser.validated_data)

        try:
            client = get_client_by_id(data["client_id"])
        except Client.DoesNotExist:
            return Response({"client_id": ["Cliente no encontrado."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            asset = get_asset_by_id(data["asset_id"])
        except Asset.DoesNotExist:
            return Response({"asset_id": ["Activo no encontrado."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            fiat = get_fiat_currency_by_id(data["fiat_currency_id"])
        except FiatCurrency.DoesNotExist:
            return Response({"fiat_currency_id": ["Moneda fiat no encontrada."]}, status=status.HTTP_400_BAD_REQUEST)

        order = None
        if data.get("order_id"):
            try:
                order = get_order_by_id(data["order_id"])
            except Order.DoesNotExist:
                return Response({"order_id": ["Orden no encontrada."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tx = create_transaction(
                client=client,
                asset=asset,
                fiat_currency=fiat,
                transaction_type=data["transaction_type"],
                unit_price=data["unit_price"],
                quantity=data["quantity"],
                order=order,
                blockchain_hash=data.get("blockchain_hash"),
            )
        except ValidationError as exc:
            return _validation_error(exc)
        return Response(_to_tx_dict(tx), status=status.HTTP_201_CREATED)


class TransactionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, tx_id: int) -> Transaction | None:
        try:
            return get_transaction_by_id(tx_id)
        except Transaction.DoesNotExist:
            return None

    @extend_schema(
        operation_id="brokerage_transactions_retrieve",
        tags=["Trading"],
        summary="Obtener detalle de una transacción",
        responses={
            200: OpenApiResponse(response=TransactionSerializer, examples=[_tx_example]),
            401: _401,
            404: _404_tx,
        },
    )
    def get(self, request: Request, tx_id: int) -> Response:
        tx = self._get(tx_id)
        if not tx:
            return Response({"error": _ERR_TX_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        return Response(_to_tx_dict(tx))
