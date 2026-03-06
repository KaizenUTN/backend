"""
API tests for trading fiat currency endpoints.

Endpoints covered:
  GET    /api/trading/fiat-currencies/
  POST   /api/trading/fiat-currencies/
  GET    /api/trading/fiat-currencies/<id>/
  POST   /api/trading/fiat-currencies/<id>/deactivate/
  POST   /api/trading/fiat-currencies/<id>/reactivate/
"""
from __future__ import annotations

import pytest
from rest_framework import status

BASE = "/api/trading/fiat-currencies/"


@pytest.mark.api
@pytest.mark.django_db
class TestFiatList:
    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.get(BASE).status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_list(self, auth_client):
        assert auth_client.get(BASE).json() == []

    def test_returns_all(self, auth_client, fiat_currency, inactive_fiat):
        response = auth_client.get(BASE)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

    def test_active_filter(self, auth_client, fiat_currency, inactive_fiat):
        response = auth_client.get(f"{BASE}?active=true")
        data = response.json()
        assert len(data) == 1
        assert data[0]["code"] == "ARS"

    def test_response_fields(self, auth_client, fiat_currency):
        data = auth_client.get(BASE).json()[0]
        for field in ("id", "code", "name", "is_active"):
            assert field in data


@pytest.mark.api
@pytest.mark.django_db
class TestFiatCreate:
    def test_create_fiat(self, auth_client):
        response = auth_client.post(
            BASE, {"code": "USD", "name": "Dólar"}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["code"] == "USD"
        assert data["is_active"] is True

    def test_code_uppercased(self, auth_client):
        response = auth_client.post(BASE, {"code": "brl"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["code"] == "BRL"

    def test_duplicate_code_returns_400(self, auth_client, fiat_currency):
        response = auth_client.post(BASE, {"code": "ARS"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_code_returns_400(self, auth_client):
        response = auth_client.post(BASE, {"name": "Sin código"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.post(BASE, {"code": "USD"}).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
@pytest.mark.django_db
class TestFiatDetail:
    def test_returns_fiat(self, auth_client, fiat_currency):
        response = auth_client.get(f"{BASE}{fiat_currency.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["code"] == "ARS"

    def test_not_found_returns_404(self, auth_client):
        assert auth_client.get(f"{BASE}99999/").status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.api
@pytest.mark.django_db
class TestFiatDeactivate:
    def test_deactivates(self, auth_client, fiat_currency):
        response = auth_client.post(f"{BASE}{fiat_currency.pk}/deactivate/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is False

    def test_idempotent(self, auth_client, inactive_fiat):
        response = auth_client.post(f"{BASE}{inactive_fiat.pk}/deactivate/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is False

    def test_not_found_returns_404(self, auth_client):
        assert auth_client.post(f"{BASE}99999/deactivate/").status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.api
@pytest.mark.django_db
class TestFiatReactivate:
    def test_reactivates(self, auth_client, inactive_fiat):
        response = auth_client.post(f"{BASE}{inactive_fiat.pk}/reactivate/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is True

    def test_idempotent(self, auth_client, fiat_currency):
        response = auth_client.post(f"{BASE}{fiat_currency.pk}/reactivate/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is True

    def test_not_found_returns_404(self, auth_client):
        assert auth_client.post(f"{BASE}99999/reactivate/").status_code == status.HTTP_404_NOT_FOUND
