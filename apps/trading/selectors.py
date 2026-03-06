"""
trading.selectors
=================
Consultas de lectura del módulo trading.

Sin lógica de negocio — solo queries optimizadas y reutilizables.
"""

from __future__ import annotations

from django.db.models import QuerySet

from .models import Asset, Client, ClientStatus, FiatCurrency, Order, Transaction


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


def get_client_list() -> QuerySet[Client]:
    """Todos los clientes, ordenados por nombre."""
    return Client.objects.all()


def get_client_by_id(client_id: int) -> Client:
    """Lanza Client.DoesNotExist si no existe."""
    return Client.objects.get(pk=client_id)


def get_client_by_cuit(cuit: str) -> Client:
    """Lanza Client.DoesNotExist si no existe."""
    return Client.objects.get(cuit=cuit.strip())


def get_active_clients() -> QuerySet[Client]:
    return Client.objects.filter(status=ClientStatus.ACTIVE)


def get_blocked_clients() -> QuerySet[Client]:
    return Client.objects.filter(status=ClientStatus.BLOCKED)


# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------


def get_asset_list() -> QuerySet[Asset]:
    """Todos los activos, ordenados por código."""
    return Asset.objects.all()


def get_asset_by_id(asset_id: int) -> Asset:
    """Lanza Asset.DoesNotExist si no existe."""
    return Asset.objects.get(pk=asset_id)


def get_asset_by_code(code: str) -> Asset:
    """Lanza Asset.DoesNotExist si no existe."""
    return Asset.objects.get(code=code.strip().upper())


def get_active_assets() -> QuerySet[Asset]:
    return Asset.objects.filter(is_active=True)


# ---------------------------------------------------------------------------
# FiatCurrency
# ---------------------------------------------------------------------------


def get_fiat_currency_list() -> QuerySet[FiatCurrency]:
    """Todas las monedas fiat, ordenadas por código."""
    return FiatCurrency.objects.all()


def get_fiat_currency_by_id(fiat_currency_id: int) -> FiatCurrency:
    """Lanza FiatCurrency.DoesNotExist si no existe."""
    return FiatCurrency.objects.get(pk=fiat_currency_id)


def get_fiat_currency_by_code(code: str) -> FiatCurrency:
    """Lanza FiatCurrency.DoesNotExist si no existe."""
    return FiatCurrency.objects.get(code=code.strip().upper())


def get_active_fiat_currencies() -> QuerySet[FiatCurrency]:
    return FiatCurrency.objects.filter(is_active=True)


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def get_order_list() -> QuerySet[Order]:
    """Todas las órdenes, ordenadas por fecha descendente."""
    return Order.objects.select_related("client", "asset", "fiat_currency").all()


def get_order_by_id(order_id: int) -> Order:
    """Lanza Order.DoesNotExist si no existe."""
    return Order.objects.select_related("client", "asset", "fiat_currency").get(pk=order_id)


def get_orders_by_client(client: Client) -> QuerySet[Order]:
    """Todas las órdenes de un cliente específico."""
    return Order.objects.filter(client=client).select_related("asset", "fiat_currency")


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------


def get_transaction_list() -> QuerySet[Transaction]:
    """Todas las transacciones, ordenadas por fecha descendente."""
    return Transaction.objects.select_related(
        "client", "asset", "fiat_currency", "order"
    ).all()


def get_transaction_by_id(tx_id: int) -> Transaction:
    """Lanza Transaction.DoesNotExist si no existe."""
    return Transaction.objects.select_related(
        "client", "asset", "fiat_currency", "order"
    ).get(pk=tx_id)


def get_transactions_by_client(client: Client) -> QuerySet[Transaction]:
    """Todas las transacciones de un cliente específico."""
    return Transaction.objects.filter(client=client).select_related(
        "asset", "fiat_currency", "order"
    )
