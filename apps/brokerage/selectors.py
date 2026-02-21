"""
brokerage.selectors
===================
Consultas de lectura del módulo brokerage.

Sin lógica de negocio — solo queries optimizadas y reutilizables.
"""

from __future__ import annotations

from django.db.models import QuerySet

from .models import Asset, Client, ClientStatus


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
