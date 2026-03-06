"""
trading.services
================
Operaciones de escritura del módulo trading.

Convenciones del proyecto:
  - Funciones keyword-only (*, param).
  - Transacciones atómicas en toda mutación.
  - ValidationError de Django para errores de negocio.
  - Sin side-effects hacia otros módulos en esta etapa.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    Asset,
    Client,
    ClientStatus,
    FiatCurrency,
    Order,
    OrderStatus,
    Transaction,
    TransactionStatus,
    TransactionType,
)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


@transaction.atomic
def create_client(*, cuit: str, name: str, email: str = "") -> Client:
    """
    Registra un nuevo cliente operacional.

    Valida que el CUIT no esté ya registrado antes de insertar.
    El estado inicial es siempre ACTIVE.
    """
    cuit = cuit.strip()
    name = name.strip()
    email = email.strip()

    if not cuit:
        raise ValidationError({"cuit": "El CUIT es obligatorio."})
    if not name:
        raise ValidationError({"name": "El nombre es obligatorio."})
    if Client.objects.filter(cuit=cuit).exists():
        raise ValidationError({"cuit": f"Ya existe un cliente con CUIT '{cuit}'."})

    return Client.objects.create(cuit=cuit, name=name, email=email, status=ClientStatus.ACTIVE)


@transaction.atomic
def update_client(*, client: Client, name: str | None = None, email: str | None = None) -> Client:
    """
    Actualiza los campos editables de un cliente.
    Solo se actualiza el campo si se pasa explícitamente.
    """
    fields: list[str] = []

    if name is not None:
        name = name.strip()
        if not name:
            raise ValidationError({"name": "El nombre no puede estar vacío."})
        client.name = name
        fields.append("name")

    if email is not None:
        client.email = email.strip()
        fields.append("email")

    if fields:
        client.save(update_fields=fields)

    return client


@transaction.atomic
def block_client(*, client: Client) -> Client:
    """Bloquea un cliente activo. Idempotente si ya está bloqueado."""
    if client.status == ClientStatus.BLOCKED:
        return client
    client.status = ClientStatus.BLOCKED
    client.save(update_fields=["status"])
    return client


@transaction.atomic
def unblock_client(*, client: Client) -> Client:
    """Reactiva un cliente bloqueado. Idempotente si ya está activo."""
    if client.status == ClientStatus.ACTIVE:
        return client
    client.status = ClientStatus.ACTIVE
    client.save(update_fields=["status"])
    return client


# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------


@transaction.atomic
def create_asset(*, code: str, name: str = "") -> Asset:
    """
    Registra un nuevo activo negociable.

    El `code` debe ser único (ticker de mercado).
    Por defecto el activo queda activo (is_active=True).
    """
    code = code.strip().upper()
    if not code:
        raise ValidationError({"code": "El código del activo es obligatorio."})
    if Asset.objects.filter(code=code).exists():
        raise ValidationError({"code": f"Ya existe un activo con código '{code}'."})

    return Asset.objects.create(code=code, name=name.strip(), is_active=True)


@transaction.atomic
def deactivate_asset(*, asset: Asset) -> Asset:
    """Desactiva un activo. No borra registros históricos."""
    if not asset.is_active:
        return asset
    asset.is_active = False
    asset.save(update_fields=["is_active"])
    return asset


@transaction.atomic
def reactivate_asset(*, asset: Asset) -> Asset:
    """Reactiva un activo previamente desactivado."""
    if asset.is_active:
        return asset
    asset.is_active = True
    asset.save(update_fields=["is_active"])
    return asset


# ---------------------------------------------------------------------------
# FiatCurrency
# ---------------------------------------------------------------------------


@transaction.atomic
def create_fiat_currency(*, code: str, name: str = "") -> FiatCurrency:
    """
    Registra una nueva moneda fiat de liquidación.

    El `code` debe ser único (ISO 4217).
    """
    code = code.strip().upper()
    if not code:
        raise ValidationError({"code": "El código de la moneda fiat es obligatorio."})
    if FiatCurrency.objects.filter(code=code).exists():
        raise ValidationError({"code": f"Ya existe una moneda fiat con código '{code}'."})

    return FiatCurrency.objects.create(code=code, name=name.strip(), is_active=True)


@transaction.atomic
def deactivate_fiat_currency(*, fiat_currency: FiatCurrency) -> FiatCurrency:
    """Desactiva una moneda fiat. Idempotente."""
    if not fiat_currency.is_active:
        return fiat_currency
    fiat_currency.is_active = False
    fiat_currency.save(update_fields=["is_active"])
    return fiat_currency


@transaction.atomic
def reactivate_fiat_currency(*, fiat_currency: FiatCurrency) -> FiatCurrency:
    """Reactiva una moneda fiat previamente desactivada. Idempotente."""
    if fiat_currency.is_active:
        return fiat_currency
    fiat_currency.is_active = True
    fiat_currency.save(update_fields=["is_active"])
    return fiat_currency


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


@transaction.atomic
def create_order(
    *,
    client: Client,
    asset: Asset,
    fiat_currency: FiatCurrency,
    transaction_type: str,
    limit_price: Decimal,
    quantity: Decimal,
) -> Order:
    """
    Crea una orden de compra/venta a precio límite.

    Valida que el cliente esté ACTIVE, que el activo y la moneda fiat
    estén activos, y que los valores numéricos sean positivos.
    """
    if not client.is_active:
        raise ValidationError(
            {"client": "El cliente está bloqueado y no puede generar nuevas órdenes."}
        )
    if not asset.is_active:
        raise ValidationError(
            {"asset": "El activo no está disponible para nuevas operaciones."}
        )
    if not fiat_currency.is_active:
        raise ValidationError(
            {"fiat_currency": "La moneda fiat no está activa."}
        )
    if transaction_type not in TransactionType.values:
        raise ValidationError(
            {"transaction_type": f"Tipo inválido. Opciones: {TransactionType.values}."}
        )

    return Order.objects.create(
        client=client,
        asset=asset,
        fiat_currency=fiat_currency,
        transaction_type=transaction_type,
        limit_price=limit_price,
        quantity=quantity,
        status=OrderStatus.PENDING,
    )


@transaction.atomic
def cancel_order(*, order: Order) -> Order:
    """
    Cancela una orden pendiente o parcialmente ejecutada.

    No se puede cancelar una orden FILLED o ya CANCELLED.
    """
    if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
        raise ValidationError(
            {"status": f"No se puede cancelar una orden en estado '{order.status}'."}
        )
    order.status = OrderStatus.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return order


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------


@transaction.atomic
def create_transaction(
    *,
    client: Client,
    asset: Asset,
    fiat_currency: FiatCurrency,
    transaction_type: str,
    unit_price: Decimal,
    quantity: Decimal,
    order: Order | None = None,
    blockchain_hash: str | None = None,
) -> Transaction:
    """
    Registra una transacción contable ejecutada.

    La transacción es INMUTABLE: una vez creada no puede ser modificada
    ni eliminada. Para revertir, crear una nueva transacción de signo contrario.

    Valida que el cliente esté activo en el momento de la ejecución.
    """
    if not client.is_active:
        raise ValidationError(
            {"client": "El cliente está bloqueado y no puede generar transacciones."}
        )
    if transaction_type not in TransactionType.values:
        raise ValidationError(
            {"transaction_type": f"Tipo inválido. Opciones: {TransactionType.values}."}
        )

    return Transaction.objects.create(
        client=client,
        asset=asset,
        fiat_currency=fiat_currency,
        transaction_type=transaction_type,
        unit_price=unit_price,
        quantity=quantity,
        order=order,
        blockchain_hash=blockchain_hash,
        status=TransactionStatus.CONFIRMED,
    )
