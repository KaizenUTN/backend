"""
API tests for trading asset endpoints.

Endpoints covered:
  GET    /api/trading/assets/
  POST   /api/trading/assets/
  GET    /api/trading/assets/<id>/
  POST   /api/trading/assets/<id>/deactivate/
  POST   /api/trading/assets/<id>/reactivate/
"""
from __future__ import annotations

import pytest
from rest_framework import status

BASE = "/api/trading/assets/"


# ---------------------------------------------------------------------------
# GET /api/trading/assets/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestAssetList:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(BASE)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_list(self, auth_client):
        assert auth_client.get(BASE).json() == []

    def test_returns_all_assets(self, auth_client, asset, inactive_asset):
        response = auth_client.get(BASE)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

    def test_active_filter(self, auth_client, asset, inactive_asset):
        response = auth_client.get(f"{BASE}?active=true")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["code"] == "BTC"

    def test_response_fields(self, auth_client, asset):
        data = auth_client.get(BASE).json()[0]
        assert "id" in data
        assert "code" in data
        assert "name" in data
        assert "is_active" in data


# ---------------------------------------------------------------------------
# POST /api/trading/assets/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestAssetCreate:
    def test_create_asset(self, auth_client):
        response = auth_client.post(BASE, {"code": "ETH", "name": "Ethereum"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["code"] == "ETH"
        assert data["is_active"] is True

    def test_code_uppercased(self, auth_client):
        response = auth_client.post(BASE, {"code": "usdt"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["code"] == "USDT"

    def test_name_optional(self, auth_client):
        response = auth_client.post(BASE, {"code": "DOGE"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_duplicate_code_returns_400(self, auth_client, asset):
        response = auth_client.post(BASE, {"code": "BTC"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_code_returns_400(self, auth_client):
        response = auth_client.post(BASE, {"name": "No Code"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(BASE, {"code": "ETH"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /api/trading/assets/<id>/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestAssetDetail:
    def test_returns_asset(self, auth_client, asset):
        response = auth_client.get(f"{BASE}{asset.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["code"] == "BTC"

    def test_inactive_asset_returned(self, auth_client, inactive_asset):
        response = auth_client.get(f"{BASE}{inactive_asset.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is False

    def test_not_found_returns_404(self, auth_client):
        response = auth_client.get(f"{BASE}99999/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /api/trading/assets/<id>/deactivate/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestAssetDeactivate:
    def test_deactivate_active_asset(self, auth_client, asset):
        response = auth_client.post(f"{BASE}{asset.pk}/deactivate/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is False

    def test_deactivate_idempotent(self, auth_client, inactive_asset):
        response = auth_client.post(f"{BASE}{inactive_asset.pk}/deactivate/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is False

    def test_not_found_returns_404(self, auth_client):
        response = auth_client.post(f"{BASE}99999/deactivate/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /api/trading/assets/<id>/reactivate/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestAssetReactivate:
    def test_reactivate_inactive_asset(self, auth_client, inactive_asset):
        response = auth_client.post(f"{BASE}{inactive_asset.pk}/reactivate/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is True

    def test_reactivate_idempotent(self, auth_client, asset):
        response = auth_client.post(f"{BASE}{asset.pk}/reactivate/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is True

    def test_not_found_returns_404(self, auth_client):
        response = auth_client.post(f"{BASE}99999/reactivate/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
