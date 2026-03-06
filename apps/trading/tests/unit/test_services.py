"""
Unit tests for trading services.

Covers all service functions:
- create_client, update_client, block_client, unblock_client
- create_asset, deactivate_asset, reactivate_asset
- create_fiat_currency, deactivate_fiat_currency, reactivate_fiat_currency
- create_order, cancel_order
- create_transaction
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.trading.models import ClientStatus, OrderStatus, TransactionStatus, TransactionType
from apps.trading.services import (
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
# create_client
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestCreateClient:
    def test_creates_active_client(self):
        c = create_client(cuit="20-11111111-1", name="Test SA")
        assert c.pk is not None
        assert c.status == ClientStatus.ACTIVE
        assert c.name == "Test SA"
        assert c.cuit == "20-11111111-1"

    def test_strips_whitespace(self):
        c = create_client(cuit="  20-22222222-2  ", name="  Empresa   ")
        assert c.cuit == "20-22222222-2"
        assert c.name == "Empresa"

    def test_email_optional(self):
        c = create_client(cuit="20-33333333-3", name="No Email")
        assert c.email == ""

    def test_email_stored(self):
        c = create_client(cuit="20-44444444-4", name="Con Email", email="ceo@firma.com")
        assert c.email == "ceo@firma.com"

    def test_duplicate_cuit_raises(self):
        create_client(cuit="20-55555555-5", name="Primera")
        with pytest.raises(ValidationError) as exc_info:
            create_client(cuit="20-55555555-5", name="Segunda")
        assert "cuit" in exc_info.value.message_dict

    def test_empty_cuit_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            create_client(cuit="   ", name="Sin CUIT")
        assert "cuit" in exc_info.value.message_dict

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            create_client(cuit="20-66666666-6", name="   ")
        assert "name" in exc_info.value.message_dict


# ---------------------------------------------------------------------------
# update_client
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestUpdateClient:
    def test_update_name(self, client_obj):
        updated = update_client(client=client_obj, name="Nuevo Nombre S.A.")
        assert updated.name == "Nuevo Nombre S.A."

    def test_update_email(self, client_obj):
        updated = update_client(client=client_obj, email="nuevo@mail.com")
        assert updated.email == "nuevo@mail.com"

    def test_empty_name_raises(self, client_obj):
        with pytest.raises(ValidationError) as exc_info:
            update_client(client=client_obj, name="   ")
        assert "name" in exc_info.value.message_dict

    def test_no_changes_returns_same_object(self, client_obj):
        original_name = client_obj.name
        result = update_client(client=client_obj)
        assert result.name == original_name


# ---------------------------------------------------------------------------
# block_client / unblock_client
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestBlockUnblockClient:
    def test_block_active_client(self, client_obj):
        blocked = block_client(client=client_obj)
        assert blocked.status == ClientStatus.BLOCKED
        assert blocked.is_active is False

    def test_block_idempotent(self, blocked_client):
        result = block_client(client=blocked_client)
        assert result.status == ClientStatus.BLOCKED

    def test_unblock_blocked_client(self, blocked_client):
        active = unblock_client(client=blocked_client)
        assert active.status == ClientStatus.ACTIVE
        assert active.is_active is True

    def test_unblock_idempotent(self, client_obj):
        result = unblock_client(client=client_obj)
        assert result.status == ClientStatus.ACTIVE


# ---------------------------------------------------------------------------
# create_asset
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestCreateAsset:
    def test_creates_active_asset(self):
        a = create_asset(code="ETH", name="Ethereum")
        assert a.pk is not None
        assert a.is_active is True
        assert a.code == "ETH"

    def test_code_uppercased(self):
        a = create_asset(code="usdt")
        assert a.code == "USDT"

    def test_name_optional(self):
        a = create_asset(code="DOGE")
        assert a.name == ""

    def test_duplicate_code_raises(self):
        create_asset(code="SOL")
        with pytest.raises(ValidationError) as exc_info:
            create_asset(code="SOL")
        assert "code" in exc_info.value.message_dict

    def test_empty_code_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            create_asset(code="   ")
        assert "code" in exc_info.value.message_dict


# ---------------------------------------------------------------------------
# deactivate_asset / reactivate_asset
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestDeactivateReactivateAsset:
    def test_deactivate(self, asset):
        result = deactivate_asset(asset=asset)
        assert result.is_active is False

    def test_deactivate_idempotent(self, inactive_asset):
        result = deactivate_asset(asset=inactive_asset)
        assert result.is_active is False

    def test_reactivate(self, inactive_asset):
        result = reactivate_asset(asset=inactive_asset)
        assert result.is_active is True

    def test_reactivate_idempotent(self, asset):
        result = reactivate_asset(asset=asset)
        assert result.is_active is True


# ---------------------------------------------------------------------------
# create_fiat_currency
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestCreateFiatCurrency:
    def test_creates_active_fiat(self):
        f = create_fiat_currency(code="USD", name="Dólar")
        assert f.pk is not None
        assert f.is_active is True
        assert f.code == "USD"

    def test_code_uppercased(self):
        f = create_fiat_currency(code="brl")
        assert f.code == "BRL"

    def test_duplicate_code_raises(self):
        create_fiat_currency(code="MXN")
        with pytest.raises(ValidationError) as exc_info:
            create_fiat_currency(code="MXN")
        assert "code" in exc_info.value.message_dict

    def test_empty_code_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            create_fiat_currency(code="  ")
        assert "code" in exc_info.value.message_dict


# ---------------------------------------------------------------------------
# deactivate_fiat_currency / reactivate_fiat_currency
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestDeactivateReactivateFiat:
    def test_deactivate(self, fiat_currency):
        result = deactivate_fiat_currency(fiat_currency=fiat_currency)
        assert result.is_active is False

    def test_deactivate_idempotent(self, inactive_fiat):
        result = deactivate_fiat_currency(fiat_currency=inactive_fiat)
        assert result.is_active is False

    def test_reactivate(self, inactive_fiat):
        result = reactivate_fiat_currency(fiat_currency=inactive_fiat)
        assert result.is_active is True

    def test_reactivate_idempotent(self, fiat_currency):
        result = reactivate_fiat_currency(fiat_currency=fiat_currency)
        assert result.is_active is True


# ---------------------------------------------------------------------------
# create_order
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestCreateOrder:
    def test_creates_pending_order(self, client_obj, asset, fiat_currency):
        order = create_order(
            client=client_obj,
            asset=asset,
            fiat_currency=fiat_currency,
            transaction_type=TransactionType.BUY,
            limit_price=Decimal("50000.00000000"),
            quantity=Decimal("0.01000000"),
        )
        assert order.pk is not None
        assert order.status == OrderStatus.PENDING
        assert order.transaction_type == TransactionType.BUY

    def test_blocked_client_raises(self, blocked_client, asset, fiat_currency):
        with pytest.raises(ValidationError) as exc_info:
            create_order(
                client=blocked_client,
                asset=asset,
                fiat_currency=fiat_currency,
                transaction_type=TransactionType.BUY,
                limit_price=Decimal("50000"),
                quantity=Decimal("1"),
            )
        assert "client" in exc_info.value.message_dict

    def test_inactive_asset_raises(self, client_obj, inactive_asset, fiat_currency):
        with pytest.raises(ValidationError) as exc_info:
            create_order(
                client=client_obj,
                asset=inactive_asset,
                fiat_currency=fiat_currency,
                transaction_type=TransactionType.BUY,
                limit_price=Decimal("100"),
                quantity=Decimal("1"),
            )
        assert "asset" in exc_info.value.message_dict

    def test_inactive_fiat_raises(self, client_obj, asset, inactive_fiat):
        with pytest.raises(ValidationError) as exc_info:
            create_order(
                client=client_obj,
                asset=asset,
                fiat_currency=inactive_fiat,
                transaction_type=TransactionType.BUY,
                limit_price=Decimal("100"),
                quantity=Decimal("1"),
            )
        assert "fiat_currency" in exc_info.value.message_dict

    def test_invalid_transaction_type_raises(self, client_obj, asset, fiat_currency):
        with pytest.raises(ValidationError) as exc_info:
            create_order(
                client=client_obj,
                asset=asset,
                fiat_currency=fiat_currency,
                transaction_type="INVALID",
                limit_price=Decimal("100"),
                quantity=Decimal("1"),
            )
        assert "transaction_type" in exc_info.value.message_dict

    def test_sell_order(self, client_obj, asset, fiat_currency):
        order = create_order(
            client=client_obj,
            asset=asset,
            fiat_currency=fiat_currency,
            transaction_type=TransactionType.SELL,
            limit_price=Decimal("60000"),
            quantity=Decimal("0.5"),
        )
        assert order.transaction_type == TransactionType.SELL


# ---------------------------------------------------------------------------
# cancel_order
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestCancelOrder:
    def test_cancel_pending_order(self, order):
        result = cancel_order(order=order)
        assert result.status == OrderStatus.CANCELLED

    def test_cancel_filled_raises(self, filled_order):
        with pytest.raises(ValidationError) as exc_info:
            cancel_order(order=filled_order)
        assert "status" in exc_info.value.message_dict

    def test_cancel_already_cancelled_raises(self, cancelled_order):
        with pytest.raises(ValidationError) as exc_info:
            cancel_order(order=cancelled_order)
        assert "status" in exc_info.value.message_dict


# ---------------------------------------------------------------------------
# create_transaction
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestCreateTransaction:
    def test_creates_confirmed_transaction(self, client_obj, asset, fiat_currency):
        tx = create_transaction(
            client=client_obj,
            asset=asset,
            fiat_currency=fiat_currency,
            transaction_type=TransactionType.BUY,
            unit_price=Decimal("50000.00000000"),
            quantity=Decimal("0.01000000"),
        )
        assert tx.pk is not None
        assert tx.status == TransactionStatus.CONFIRMED

    def test_with_linked_order(self, client_obj, asset, fiat_currency, order):
        tx = create_transaction(
            client=client_obj,
            asset=asset,
            fiat_currency=fiat_currency,
            transaction_type=TransactionType.BUY,
            unit_price=Decimal("50000"),
            quantity=Decimal("0.01"),
            order=order,
        )
        assert tx.order_id == order.pk

    def test_with_blockchain_hash(self, client_obj, asset, fiat_currency):
        tx = create_transaction(
            client=client_obj,
            asset=asset,
            fiat_currency=fiat_currency,
            transaction_type=TransactionType.BUY,
            unit_price=Decimal("50000"),
            quantity=Decimal("0.01"),
            blockchain_hash="0xabc123",
        )
        assert tx.blockchain_hash == "0xabc123"

    def test_blocked_client_raises(self, blocked_client, asset, fiat_currency):
        with pytest.raises(ValidationError) as exc_info:
            create_transaction(
                client=blocked_client,
                asset=asset,
                fiat_currency=fiat_currency,
                transaction_type=TransactionType.BUY,
                unit_price=Decimal("100"),
                quantity=Decimal("1"),
            )
        assert "client" in exc_info.value.message_dict

    def test_invalid_transaction_type_raises(self, client_obj, asset, fiat_currency):
        with pytest.raises(ValidationError) as exc_info:
            create_transaction(
                client=client_obj,
                asset=asset,
                fiat_currency=fiat_currency,
                transaction_type="SWAP",
                unit_price=Decimal("100"),
                quantity=Decimal("1"),
            )
        assert "transaction_type" in exc_info.value.message_dict

    def test_total_computed(self, client_obj, asset, fiat_currency):
        tx = create_transaction(
            client=client_obj,
            asset=asset,
            fiat_currency=fiat_currency,
            transaction_type=TransactionType.SELL,
            unit_price=Decimal("60000"),
            quantity=Decimal("2"),
        )
        assert tx.total == Decimal("120000")
