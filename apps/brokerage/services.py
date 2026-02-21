"""
brokerage.services
==================
Operaciones de escritura del módulo brokerage.

Estado actual: CRUD básico de Client y Asset.
No contiene lógica financiera (órdenes, transacciones, balances).

Convenciones del proyecto:
  - Funciones keyword-only (*, param).
  - Transacciones atómicas en toda mutación.
  - ValidationError de Django para errores de negocio.
  - Sin side-effects hacia otros módulos en esta etapa.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Asset, Client, ClientStatus


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


@transaction.atomic
def create_client(*, cuit: str, name: str) -> Client:
    """
    Registra un nuevo cliente operacional.

    Valida que el CUIT no esté ya registrado antes de insertar.
    El estado inicial es siempre ACTIVE.
    """
    cuit = cuit.strip()
    name = name.strip()

    if not cuit:
        raise ValidationError({"cuit": "El CUIT es obligatorio."})
    if not name:
        raise ValidationError({"name": "El nombre es obligatorio."})
    if Client.objects.filter(cuit=cuit).exists():
        raise ValidationError({"cuit": f"Ya existe un cliente con CUIT '{cuit}'."})

    return Client.objects.create(cuit=cuit, name=name, status=ClientStatus.ACTIVE)


@transaction.atomic
def update_client(*, client: Client, name: str | None = None) -> Client:
    """
    Actualiza los campos editables de un cliente.
    Solo se actualiza el campo si se pasa explícitamente.
    """
    changed = False

    if name is not None:
        name = name.strip()
        if not name:
            raise ValidationError({"name": "El nombre no puede estar vacío."})
        client.name = name
        changed = True

    if changed:
        client.save(update_fields=["name"])

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
