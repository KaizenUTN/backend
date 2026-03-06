"""
API tests for trading client endpoints.

Endpoints covered:
  GET    /api/trading/clients/
  POST   /api/trading/clients/
  GET    /api/trading/clients/<id>/
  PATCH  /api/trading/clients/<id>/
  POST   /api/trading/clients/<id>/block/
  POST   /api/trading/clients/<id>/unblock/
"""
from __future__ import annotations

import pytest
from rest_framework import status

BASE = "/api/trading/clients/"


# ---------------------------------------------------------------------------
# GET /api/trading/clients/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestClientList:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(BASE)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_empty_list(self, auth_client):
        response = auth_client.get(BASE)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_returns_clients(self, auth_client, client_obj, blocked_client):
        response = auth_client.get(BASE)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

    def test_response_fields(self, auth_client, client_obj):
        response = auth_client.get(BASE)
        data = response.json()[0]
        assert "id" in data
        assert "cuit" in data
        assert "name" in data
        assert "email" in data
        assert "status" in data
        assert "is_active" in data
        assert "created_at" in data


# ---------------------------------------------------------------------------
# POST /api/trading/clients/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestClientCreate:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(BASE, {"cuit": "20-11111111-1", "name": "Test"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_valid_client(self, auth_client):
        payload = {"cuit": "20-11111111-1", "name": "Empresa SA"}
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["cuit"] == "20-11111111-1"
        assert data["name"] == "Empresa SA"
        assert data["status"] == "ACTIVE"
        assert data["is_active"] is True

    def test_create_with_email(self, auth_client):
        payload = {"cuit": "20-22222222-2", "name": "Con Email", "email": "ceo@co.com"}
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["email"] == "ceo@co.com"

    def test_duplicate_cuit_returns_400(self, auth_client, client_obj):
        payload = {"cuit": client_obj.cuit, "name": "Otro"}
        response = auth_client.post(BASE, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cuit" in response.json()

    def test_missing_cuit_returns_400(self, auth_client):
        response = auth_client.post(BASE, {"name": "Sin CUIT"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_name_returns_400(self, auth_client):
        response = auth_client.post(BASE, {"cuit": "20-33333333-3"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# GET /api/trading/clients/<id>/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestClientDetail:
    def test_returns_client(self, auth_client, client_obj):
        response = auth_client.get(f"{BASE}{client_obj.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["cuit"] == client_obj.cuit

    def test_not_found_returns_404(self, auth_client):
        response = auth_client.get(f"{BASE}99999/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, api_client, client_obj):
        response = api_client.get(f"{BASE}{client_obj.pk}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# PATCH /api/trading/clients/<id>/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestClientUpdate:
    def test_update_name(self, auth_client, client_obj):
        response = auth_client.patch(
            f"{BASE}{client_obj.pk}/", {"name": "Nuevo Nombre"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Nuevo Nombre"

    def test_update_email(self, auth_client, client_obj):
        response = auth_client.patch(
            f"{BASE}{client_obj.pk}/", {"email": "new@email.com"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["email"] == "new@email.com"

    def test_empty_name_returns_400(self, auth_client, client_obj):
        response = auth_client.patch(
            f"{BASE}{client_obj.pk}/", {"name": "  "}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_not_found_returns_404(self, auth_client):
        response = auth_client.patch(f"{BASE}99999/", {"name": "X"}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, api_client, client_obj):
        response = api_client.patch(f"{BASE}{client_obj.pk}/", {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# POST /api/trading/clients/<id>/block/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestClientBlock:
    def test_block_active_client(self, auth_client, client_obj):
        response = auth_client.post(f"{BASE}{client_obj.pk}/block/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "BLOCKED"
        assert data["is_active"] is False

    def test_block_idempotent(self, auth_client, blocked_client):
        response = auth_client.post(f"{BASE}{blocked_client.pk}/block/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "BLOCKED"

    def test_block_not_found_returns_404(self, auth_client):
        response = auth_client.post(f"{BASE}99999/block/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, api_client, client_obj):
        response = api_client.post(f"{BASE}{client_obj.pk}/block/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# POST /api/trading/clients/<id>/unblock/
# ---------------------------------------------------------------------------

@pytest.mark.api
@pytest.mark.django_db
class TestClientUnblock:
    def test_unblock_blocked_client(self, auth_client, blocked_client):
        response = auth_client.post(f"{BASE}{blocked_client.pk}/unblock/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ACTIVE"
        assert data["is_active"] is True

    def test_unblock_idempotent(self, auth_client, client_obj):
        response = auth_client.post(f"{BASE}{client_obj.pk}/unblock/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ACTIVE"

    def test_unblock_not_found_returns_404(self, auth_client):
        response = auth_client.post(f"{BASE}99999/unblock/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
