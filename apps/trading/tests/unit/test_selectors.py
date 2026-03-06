"""
Unit tests for trading selectors.

Verifies that all query functions return the correct querysets/objects.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from apps.trading.models import (
    Asset,
    Client,
    FiatCurrency,
    Order,
    Transaction,
)
from apps.trading.selectors import (
    get_active_assets,
    get_active_clients,
    get_active_fiat_currencies,
    get_asset_by_code,
    get_asset_by_id,
    get_asset_list,
    get_blocked_clients,
    get_client_by_cuit,
    get_client_by_id,
    get_client_list,
    get_fiat_currency_by_code,
    get_fiat_currency_by_id,
    get_fiat_currency_list,
    get_order_by_id,
    get_order_list,
    get_orders_by_client,
    get_transaction_by_id,
    get_transaction_list,
    get_transactions_by_client,
)


# ---------------------------------------------------------------------------
# Client selectors
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestClientSelectors:
    def test_get_client_list_empty(self):
        assert list(get_client_list()) == []

    def test_get_client_list_returns_all(self, client_obj, blocked_client):
        result = list(get_client_list())
        assert len(result) == 2

    def test_get_client_by_id_found(self, client_obj):
        result = get_client_by_id(client_obj.pk)
        assert result.pk == client_obj.pk

    def test_get_client_by_id_not_found(self):
        with pytest.raises(Client.DoesNotExist):
            get_client_by_id(99999)

    def test_get_client_by_cuit(self, client_obj):
        result = get_client_by_cuit(client_obj.cuit)
        assert result.pk == client_obj.pk

    def test_get_client_by_cuit_strips_whitespace(self, client_obj):
        result = get_client_by_cuit(f"  {client_obj.cuit}  ")
        assert result.pk == client_obj.pk

    def test_get_client_by_cuit_not_found(self):
        with pytest.raises(Client.DoesNotExist):
            get_client_by_cuit("99-99999999-9")

    def test_get_active_clients(self, client_obj, blocked_client):
        result = list(get_active_clients())
        pks = [c.pk for c in result]
        assert client_obj.pk in pks
        assert blocked_client.pk not in pks

    def test_get_blocked_clients(self, client_obj, blocked_client):
        result = list(get_blocked_clients())
        pks = [c.pk for c in result]
        assert blocked_client.pk in pks
        assert client_obj.pk not in pks


# ---------------------------------------------------------------------------
# Asset selectors
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestAssetSelectors:
    def test_get_asset_list_returns_all(self, asset, inactive_asset):
        result = list(get_asset_list())
        assert len(result) == 2

    def test_get_active_assets_only_active(self, asset, inactive_asset):
        result = list(get_active_assets())
        pks = [a.pk for a in result]
        assert asset.pk in pks
        assert inactive_asset.pk not in pks

    def test_get_asset_by_id(self, asset):
        result = get_asset_by_id(asset.pk)
        assert result.code == "BTC"

    def test_get_asset_by_id_not_found(self):
        with pytest.raises(Asset.DoesNotExist):
            get_asset_by_id(99999)

    def test_get_asset_by_code(self, asset):
        result = get_asset_by_code("BTC")
        assert result.pk == asset.pk

    def test_get_asset_by_code_case_insensitive(self, asset):
        result = get_asset_by_code("btc")
        assert result.pk == asset.pk

    def test_get_asset_by_code_not_found(self):
        with pytest.raises(Asset.DoesNotExist):
            get_asset_by_code("XYZ")


# ---------------------------------------------------------------------------
# FiatCurrency selectors
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestFiatCurrencySelectors:
    def test_get_fiat_list_returns_all(self, fiat_currency, inactive_fiat):
        result = list(get_fiat_currency_list())
        assert len(result) == 2

    def test_get_active_fiat_only_active(self, fiat_currency, inactive_fiat):
        result = list(get_active_fiat_currencies())
        pks = [f.pk for f in result]
        assert fiat_currency.pk in pks
        assert inactive_fiat.pk not in pks

    def test_get_fiat_by_id(self, fiat_currency):
        result = get_fiat_currency_by_id(fiat_currency.pk)
        assert result.code == "ARS"

    def test_get_fiat_by_id_not_found(self):
        with pytest.raises(FiatCurrency.DoesNotExist):
            get_fiat_currency_by_id(99999)

    def test_get_fiat_by_code(self, fiat_currency):
        result = get_fiat_currency_by_code("ARS")
        assert result.pk == fiat_currency.pk

    def test_get_fiat_by_code_case_insensitive(self, fiat_currency):
        result = get_fiat_currency_by_code("ars")
        assert result.pk == fiat_currency.pk


# ---------------------------------------------------------------------------
# Order selectors
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestOrderSelectors:
    def test_get_order_list_returns_all(self, order, filled_order):
        result = list(get_order_list())
        assert len(result) == 2

    def test_get_order_by_id(self, order):
        result = get_order_by_id(order.pk)
        assert result.pk == order.pk

    def test_get_order_by_id_not_found(self):
        with pytest.raises(Order.DoesNotExist):
            get_order_by_id(99999)

    def test_get_orders_by_client(self, client_obj, order, filled_order):
        result = list(get_orders_by_client(client_obj))
        pks = [o.pk for o in result]
        assert order.pk in pks
        assert filled_order.pk in pks

    def test_get_orders_by_client_returns_empty_for_new_client(self, db):
        from apps.trading.models import ClientStatus
        new_client = Client.objects.create(
            cuit="11-22333444-5", name="Nuevo", status=ClientStatus.ACTIVE
        )
        result = list(get_orders_by_client(new_client))
        assert result == []


# ---------------------------------------------------------------------------
# Transaction selectors
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.django_db
class TestTransactionSelectors:
    def test_get_transaction_list(self, transaction_obj):
        result = list(get_transaction_list())
        assert len(result) == 1

    def test_get_transaction_by_id(self, transaction_obj):
        result = get_transaction_by_id(transaction_obj.pk)
        assert result.pk == transaction_obj.pk

    def test_get_transaction_by_id_not_found(self):
        with pytest.raises(Transaction.DoesNotExist):
            get_transaction_by_id(99999)

    def test_get_transactions_by_client(self, client_obj, transaction_obj):
        result = list(get_transactions_by_client(client_obj))
        assert len(result) == 1
        assert result[0].pk == transaction_obj.pk

    def test_get_transactions_by_client_empty(self, blocked_client):
        result = list(get_transactions_by_client(blocked_client))
        assert result == []
