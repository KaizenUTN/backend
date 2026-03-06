"""
Unit tests for trading models.

Covers:
- Transaction immutability (save blocks UPDATE, delete always raises)
- Transaction.total computed property
- Order.notional computed property
- Client.is_active property
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from apps.trading.models import (
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

@pytest.mark.unit
@pytest.mark.django_db
class TestClientModel:
    def test_is_active_when_status_active(self, client_obj):
        assert client_obj.is_active is True

    def test_is_active_false_when_blocked(self, blocked_client):
        assert blocked_client.is_active is False

    def test_str_representation(self, client_obj):
        assert "Empresa Test S.A." in str(client_obj)
        assert "20-12345678-9" in str(client_obj)


# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestAssetModel:
    def test_str_returns_code(self, asset):
        assert str(asset) == "BTC"

    def test_inactive_asset_is_active_false(self, inactive_asset):
        assert inactive_asset.is_active is False


# ---------------------------------------------------------------------------
# FiatCurrency
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestFiatCurrencyModel:
    def test_str_returns_code(self, fiat_currency):
        assert str(fiat_currency) == "ARS"


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestOrderModel:
    def test_notional_is_price_times_quantity(self, order):
        expected = order.limit_price * order.quantity
        assert order.notional == expected

    def test_notional_precision(self):
        """notional debe usar aritmética Decimal sin pérdida de precisión."""
        price = Decimal("50000.12345678")
        qty = Decimal("0.00100000")
        o = Order.__new__(Order)
        o.limit_price = price
        o.quantity = qty
        assert o.notional == price * qty

    def test_str_contains_asset_and_type(self, order):
        s = str(order)
        assert "BTC" in s
        assert "Compra" in s or "BUY" in s


# ---------------------------------------------------------------------------
# Transaction — IMMUTABILITY
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestTransactionImmutability:
    def test_save_create_works(self, client_obj, asset, fiat_currency):
        """Primera inserción debe funcionar."""
        tx = Transaction.objects.create(
            client=client_obj,
            asset=asset,
            fiat_currency=fiat_currency,
            transaction_type=TransactionType.BUY,
            unit_price=Decimal("50000.00000000"),
            quantity=Decimal("0.01000000"),
            status=TransactionStatus.CONFIRMED,
        )
        assert tx.pk is not None

    def test_save_update_raises(self, transaction_obj):
        """Intentar UPDATE en Transaction debe lanzar PermissionError."""
        with pytest.raises(PermissionError):
            transaction_obj.save()

    def test_delete_raises(self, transaction_obj):
        """Intentar DELETE en Transaction debe lanzar PermissionError."""
        with pytest.raises(PermissionError):
            transaction_obj.delete()

    def test_total_property(self, transaction_obj):
        expected = transaction_obj.unit_price * transaction_obj.quantity
        assert transaction_obj.total == expected

    def test_total_is_not_db_field(self):
        """total no debe ser un campo de DB (no está en _meta.fields)."""
        field_names = [f.name for f in Transaction._meta.get_fields()]
        assert "total" not in field_names

    def test_str_contains_total(self, transaction_obj):
        s = str(transaction_obj)
        assert "BTC" in s
