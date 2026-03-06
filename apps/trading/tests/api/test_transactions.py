"""
API tests for trading transaction endpoints.

Endpoints covered:
  GET   /api/trading/transactions/
  POST  /api/trading/transactions/
  GET   /api/trading/transactions/<id>/
"""
from __future__ import annotations

import pytest
from rest_framework import status

BASE = "/api/trading/transactions/"


def _tx_payload(client_obj, asset, fiat_currency, **overrides):
    payload = {
        "client_id": client_obj.pk,
        "asset_id": asset.pk,
        "fiat_currency_id": fiat_currency.pk,
        "transaction_type": "BUY",
        "unit_price": "50000.00000000",
        "quantity": "0.01000000",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# GET /api/trading/transactions/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestTransactionList:
    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.get(BASE).status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_list(self, auth_client):
        assert auth_client.get(BASE).json() == []

    def test_returns_all_transactions(self, auth_client, transaction_obj):
        response = auth_client.get(BASE)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

    def test_response_fields(self, auth_client, transaction_obj):
        data = auth_client.get(BASE).json()[0]
        for field in (
            "id", "client_id", "client_cuit", "order_id",
            "asset_code", "fiat_currency_code",
            "transaction_type", "unit_price", "quantity", "total",
            "status", "blockchain_hash", "created_at",
        ):
            assert field in data, f"Missing field: {field}"

    def test_total_field_computed(self, auth_client, transaction_obj):
        data = auth_client.get(BASE).json()[0]
        expected = float(transaction_obj.unit_price) * float(transaction_obj.quantity)
        assert float(data["total"]) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# POST /api/trading/transactions/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestTransactionCreate:
    def test_create_transaction(self, auth_client, client_obj, asset, fiat_currency):
        payload = _tx_payload(client_obj, asset, fiat_currency)
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "CONFIRMED"
        assert data["asset_code"] == "BTC"
        assert data["transaction_type"] == "BUY"

    def test_create_sell_transaction(self, auth_client, client_obj, asset, fiat_currency):
        payload = _tx_payload(client_obj, asset, fiat_currency, transaction_type="SELL")
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["transaction_type"] == "SELL"

    def test_create_with_blockchain_hash(self, auth_client, client_obj, asset, fiat_currency):
        payload = _tx_payload(
            client_obj, asset, fiat_currency, blockchain_hash="0xdeadbeef"
        )
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["blockchain_hash"] == "0xdeadbeef"

    def test_create_with_linked_order(self, auth_client, client_obj, asset, fiat_currency, order):
        payload = _tx_payload(client_obj, asset, fiat_currency, order_id=order.pk)
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["order_id"] == order.pk

    def test_total_in_response(self, auth_client, client_obj, asset, fiat_currency):
        payload = _tx_payload(
            client_obj, asset, fiat_currency,
            unit_price="60000.00000000",
            quantity="2.00000000",
        )
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert float(response.json()["total"]) == pytest.approx(120000.0)

    def test_blocked_client_returns_400(self, auth_client, blocked_client, asset, fiat_currency):
        payload = _tx_payload(blocked_client, asset, fiat_currency)
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "client" in response.json()

    def test_invalid_client_returns_400(self, auth_client, asset, fiat_currency):
        payload = {
            "client_id": 99999,
            "asset_id": asset.pk,
            "fiat_currency_id": fiat_currency.pk,
            "transaction_type": "BUY",
            "unit_price": "100",
            "quantity": "1",
        }
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_transaction_type_returns_400(self, auth_client, client_obj, asset, fiat_currency):
        payload = _tx_payload(client_obj, asset, fiat_currency, transaction_type="SWAP")
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_zero_price_returns_400(self, auth_client, client_obj, asset, fiat_currency):
        payload = _tx_payload(client_obj, asset, fiat_currency, unit_price="0")
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_fiat_returns_400(self, auth_client, client_obj, asset):
        payload = {
            "client_id": client_obj.pk,
            "asset_id": asset.pk,
            "fiat_currency_id": 99999,
            "transaction_type": "BUY",
            "unit_price": "100",
            "quantity": "1",
        }
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_order_id_returns_400(self, auth_client, client_obj, asset, fiat_currency):
        payload = _tx_payload(client_obj, asset, fiat_currency, order_id=99999)
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.post(BASE, {}).status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /api/trading/transactions/<id>/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestTransactionDetail:
    def test_returns_transaction(self, auth_client, transaction_obj):
        response = auth_client.get(f"{BASE}{transaction_obj.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == transaction_obj.pk

    def test_not_found_returns_404(self, auth_client):
        assert auth_client.get(f"{BASE}99999/").status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, api_client, transaction_obj):
        assert (
            api_client.get(f"{BASE}{transaction_obj.pk}/").status_code
            == status.HTTP_401_UNAUTHORIZED
        )
