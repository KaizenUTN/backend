"""
API tests for trading order endpoints.

Endpoints covered:
  GET   /api/trading/orders/
  POST  /api/trading/orders/
  GET   /api/trading/orders/<id>/
  POST  /api/trading/orders/<id>/cancel/
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework import status

BASE = "/api/trading/orders/"


def _order_payload(client_obj, asset, fiat_currency, **overrides):
    payload = {
        "client_id": client_obj.pk,
        "asset_id": asset.pk,
        "fiat_currency_id": fiat_currency.pk,
        "transaction_type": "BUY",
        "limit_price": "50000.00000000",
        "quantity": "0.01000000",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# GET /api/trading/orders/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestOrderList:
    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.get(BASE).status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_list(self, auth_client):
        assert auth_client.get(BASE).json() == []

    def test_returns_all_orders(self, auth_client, order, filled_order):
        response = auth_client.get(BASE)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

    def test_response_fields(self, auth_client, order):
        data = auth_client.get(BASE).json()[0]
        for field in (
            "id", "client_id", "client_cuit", "asset_code", "fiat_currency_code",
            "transaction_type", "limit_price", "quantity", "notional",
            "status", "created_at", "updated_at",
        ):
            assert field in data, f"Missing field: {field}"

    def test_notional_computed(self, auth_client, order):
        data = auth_client.get(BASE).json()[0]
        expected = float(order.limit_price) * float(order.quantity)
        assert float(data["notional"]) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# POST /api/trading/orders/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestOrderCreate:
    def test_create_buy_order(self, auth_client, client_obj, asset, fiat_currency):
        payload = _order_payload(client_obj, asset, fiat_currency)
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "PENDING"
        assert data["transaction_type"] == "BUY"
        assert data["asset_code"] == "BTC"

    def test_create_sell_order(self, auth_client, client_obj, asset, fiat_currency):
        payload = _order_payload(client_obj, asset, fiat_currency, transaction_type="SELL")
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["transaction_type"] == "SELL"

    def test_blocked_client_returns_400(self, auth_client, blocked_client, asset, fiat_currency):
        payload = _order_payload(blocked_client, asset, fiat_currency)
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "client" in response.json()

    def test_inactive_asset_returns_400(self, auth_client, client_obj, inactive_asset, fiat_currency):
        payload = _order_payload(client_obj, inactive_asset, fiat_currency)
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "asset" in response.json()

    def test_inactive_fiat_returns_400(self, auth_client, client_obj, asset, inactive_fiat):
        payload = _order_payload(client_obj, asset, inactive_fiat)
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "fiat_currency" in response.json()

    def test_invalid_client_id_returns_400(self, auth_client, asset, fiat_currency):
        payload = {
            "client_id": 99999,
            "asset_id": asset.pk,
            "fiat_currency_id": fiat_currency.pk,
            "transaction_type": "BUY",
            "limit_price": "100",
            "quantity": "1",
        }
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_transaction_type_returns_400(self, auth_client, client_obj, asset, fiat_currency):
        payload = _order_payload(client_obj, asset, fiat_currency, transaction_type="INVALID")
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_zero_price_returns_400(self, auth_client, client_obj, asset, fiat_currency):
        payload = _order_payload(client_obj, asset, fiat_currency, limit_price="0")
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.post(BASE, {}).status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /api/trading/orders/<id>/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestOrderDetail:
    def test_returns_order(self, auth_client, order):
        response = auth_client.get(f"{BASE}{order.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == order.pk

    def test_not_found_returns_404(self, auth_client):
        assert auth_client.get(f"{BASE}99999/").status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, api_client, order):
        assert api_client.get(f"{BASE}{order.pk}/").status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# POST /api/trading/orders/<id>/cancel/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestOrderCancel:
    def test_cancel_pending_order(self, auth_client, order):
        response = auth_client.post(f"{BASE}{order.pk}/cancel/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "CANCELLED"

    def test_cancel_filled_order_returns_400(self, auth_client, filled_order):
        response = auth_client.post(f"{BASE}{filled_order.pk}/cancel/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "status" in response.json()

    def test_cancel_already_cancelled_returns_400(self, auth_client, cancelled_order):
        response = auth_client.post(f"{BASE}{cancelled_order.pk}/cancel/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_not_found_returns_404(self, auth_client):
        assert auth_client.post(f"{BASE}99999/cancel/").status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, api_client, order):
        assert (
            api_client.post(f"{BASE}{order.pk}/cancel/").status_code
            == status.HTTP_401_UNAUTHORIZED
        )
