"""
API tests: audit logs endpoints
================================
Tests para:
    GET  /api/audit/logs/        — listar logs con filtros
    GET  /api/audit/logs/{id}/   — detalle de un log

Cada grupo verifica:
- Autenticación requerida (401 sin token)
- RBAC: requiere permiso `auditoria.view` (403 sin él)
- Lógica: respuesta, filtros, 404
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditLog, AuditStatus
from apps.authorization.models import Permission, Role
from apps.users.tests.factories.user_factory import UserFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

LIST_URL = "/api/audit/logs/"


def _detail_url(log_id: int) -> str:
    return f"/api/audit/logs/{log_id}/"


def _make_role_with_permission(permission_code: str) -> Role:
    role, _ = Role.objects.get_or_create(name=f"role_{permission_code}")
    perm, _ = Permission.objects.get_or_create(
        code=permission_code,
        defaults={"description": permission_code},
    )
    role.permissions.add(perm)
    return role


def _auth_client(user) -> APIClient:
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token.access_token)}")  # type: ignore[attr-defined]
    return client


@pytest.fixture()
def auditor_user():
    """Usuario con permiso auditoria.view."""
    role = _make_role_with_permission("auditoria.view")
    user = UserFactory(email="auditor@audit-test.com")
    user.role = role
    user.save()
    return user


@pytest.fixture()
def auditor_client(auditor_user):
    return _auth_client(auditor_user)


@pytest.fixture()
def no_perm_user():
    """Usuario autenticado sin permiso auditoria.view."""
    return UserFactory(email="noperm@audit-test.com")


@pytest.fixture()
def no_perm_client(no_perm_user):
    return _auth_client(no_perm_user)


@pytest.fixture()
def sample_log():
    """AuditLog creado directamente en la DB para lectura."""
    return AuditLog.objects.create(
        action="user.created",
        resource="user",
        resource_id="42",
        status=AuditStatus.SUCCESS,
        metadata={"email": "someone@example.com"},
        ip_address="10.0.0.1",
    )


@pytest.fixture()
def sample_failure_log():
    """AuditLog de fallo para tests de filtro."""
    return AuditLog.objects.create(
        action="auth.login",
        resource="session",
        status=AuditStatus.FAILURE,
        ip_address="1.2.3.4",
        metadata={"reason": "invalid_credentials"},
    )


# ---------------------------------------------------------------------------
# GET /api/audit/logs/  — Lista
# ---------------------------------------------------------------------------


class TestAuditLogListView:
    def test_requires_auth(self, api_client, sample_log):
        response = api_client.get(LIST_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_requires_auditoria_view_permission(self, no_perm_client, sample_log):
        """Usuario autenticado sin permiso auditoria.view → 403."""
        response = no_perm_client.get(LIST_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_200_with_permission(self, auditor_client, sample_log):
        response = auditor_client.get(LIST_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_returns_list(self, auditor_client, sample_log):
        response = auditor_client.get(LIST_URL)
        assert isinstance(response.data, list)
        assert len(response.data) >= 1

    def test_response_fields(self, auditor_client, sample_log):
        response = auditor_client.get(LIST_URL)
        log_data = next(d for d in response.data if d["id"] == sample_log.pk)
        expected_fields = {
            "id", "user", "action", "resource", "resource_id",
            "status", "status_display", "metadata", "ip_address",
            "user_agent", "timestamp", "correlation_id",
        }
        assert expected_fields.issubset(set(log_data.keys()))

    def test_user_field_is_none_for_anonymous_log(self, auditor_client, sample_log):
        response = auditor_client.get(LIST_URL)
        log_data = next(d for d in response.data if d["id"] == sample_log.pk)
        assert log_data["user"] is None

    def test_user_field_contains_id_and_email(self, auditor_client, auditor_user):
        """Log con usuario → user muestra id + email."""
        log = AuditLog.objects.create(
            user=auditor_user,
            action="user.listed",
            resource="user",
        )
        response = auditor_client.get(LIST_URL)
        log_data = next(d for d in response.data if d["id"] == log.pk)
        assert log_data["user"]["id"] == auditor_user.pk
        assert log_data["user"]["email"] == auditor_user.email

    def test_status_display_is_human_readable(self, auditor_client, sample_log):
        response = auditor_client.get(LIST_URL)
        log_data = next(d for d in response.data if d["id"] == sample_log.pk)
        assert log_data["status_display"] == "Exitoso"

    def test_status_display_failure(self, auditor_client, sample_failure_log):
        response = auditor_client.get(LIST_URL)
        log_data = next(d for d in response.data if d["id"] == sample_failure_log.pk)
        assert log_data["status_display"] == "Fallido"

    def test_filter_by_status_failure(self, auditor_client, sample_log, sample_failure_log):
        response = auditor_client.get(LIST_URL, {"status": "FAILURE"})
        assert response.status_code == status.HTTP_200_OK
        ids = [d["id"] for d in response.data]
        assert sample_failure_log.pk in ids
        assert sample_log.pk not in ids

    def test_filter_by_status_success(self, auditor_client, sample_log, sample_failure_log):
        response = auditor_client.get(LIST_URL, {"status": "SUCCESS"})
        ids = [d["id"] for d in response.data]
        assert sample_log.pk in ids
        assert sample_failure_log.pk not in ids

    def test_filter_by_action_contains(self, auditor_client, sample_log, sample_failure_log):
        response = auditor_client.get(LIST_URL, {"action": "user.created"})
        ids = [d["id"] for d in response.data]
        assert sample_log.pk in ids
        assert sample_failure_log.pk not in ids

    def test_filter_by_resource_contains(self, auditor_client, sample_log, sample_failure_log):
        response = auditor_client.get(LIST_URL, {"resource": "session"})
        ids = [d["id"] for d in response.data]
        assert sample_failure_log.pk in ids
        assert sample_log.pk not in ids

    def test_filter_by_user_id(self, auditor_client, auditor_user):
        log_with_user = AuditLog.objects.create(
            user=auditor_user,
            action="report.export",
            resource="report",
        )
        AuditLog.objects.create(action="system.startup", resource="system")
        response = auditor_client.get(LIST_URL, {"user_id": auditor_user.pk})
        ids = [d["id"] for d in response.data]
        assert log_with_user.pk in ids
        for d in response.data:
            assert d["user"] is not None
            assert d["user"]["id"] == auditor_user.pk

    def test_filter_by_correlation_id(self, auditor_client):
        cid = uuid.uuid4()
        log1 = AuditLog.objects.create(action="user.created", resource="user", correlation_id=cid)
        AuditLog.objects.create(action="user.created", resource="user")  # otro cid
        response = auditor_client.get(LIST_URL, {"correlation_id": str(cid)})
        ids = [d["id"] for d in response.data]
        assert log1.pk in ids
        assert all(d["correlation_id"] == str(cid) for d in response.data)

    def test_default_ordering_newest_first(self, auditor_client):
        log1 = AuditLog.objects.create(action="first.action", resource="x")
        log2 = AuditLog.objects.create(action="second.action", resource="x")
        response = auditor_client.get(LIST_URL)
        ids = [d["id"] for d in response.data]
        assert ids.index(log2.pk) < ids.index(log1.pk)

    def test_ordering_ascending(self, auditor_client):
        log1 = AuditLog.objects.create(action="first.asc", resource="x")
        log2 = AuditLog.objects.create(action="second.asc", resource="x")
        response = auditor_client.get(LIST_URL, {"ordering": "timestamp", "action": "asc"})
        ids = [d["id"] for d in response.data]
        assert ids.index(log1.pk) < ids.index(log2.pk)

    def test_empty_list_when_no_logs(self, auditor_client):
        AuditLog.objects.all().delete()
        response = auditor_client.get(LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []


# ---------------------------------------------------------------------------
# GET /api/audit/logs/{id}/  — Detalle
# ---------------------------------------------------------------------------


class TestAuditLogDetailView:
    def test_requires_auth(self, api_client, sample_log):
        response = api_client.get(_detail_url(sample_log.pk))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_requires_auditoria_view_permission(self, no_perm_client, sample_log):
        response = no_perm_client.get(_detail_url(sample_log.pk))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_200_with_permission(self, auditor_client, sample_log):
        response = auditor_client.get(_detail_url(sample_log.pk))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_correct_log(self, auditor_client, sample_log):
        response = auditor_client.get(_detail_url(sample_log.pk))
        assert response.data["id"] == sample_log.pk
        assert response.data["action"] == "user.created"
        assert response.data["resource"] == "user"
        assert response.data["resource_id"] == "42"

    def test_metadata_is_returned(self, auditor_client, sample_log):
        response = auditor_client.get(_detail_url(sample_log.pk))
        assert response.data["metadata"] == {"email": "someone@example.com"}

    def test_ip_address_is_returned(self, auditor_client, sample_log):
        response = auditor_client.get(_detail_url(sample_log.pk))
        assert response.data["ip_address"] == "10.0.0.1"

    def test_correlation_id_is_uuid_string(self, auditor_client, sample_log):
        response = auditor_client.get(_detail_url(sample_log.pk))
        cid = response.data["correlation_id"]
        assert uuid.UUID(cid)  # no lanza ValueError si es válido

    def test_returns_404_for_nonexistent_id(self, auditor_client):
        response = auditor_client.get(_detail_url(999999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_404_detail_message(self, auditor_client):
        response = auditor_client.get(_detail_url(999999))
        assert "detail" in response.data
