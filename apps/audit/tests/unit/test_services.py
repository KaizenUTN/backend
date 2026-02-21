"""
Tests: audit.services
=====================
Verifica log_action, log_failure y create_audit_entry.

Estrategia:
- Tests de contrato: verifican que los registros se escriben correctamente.
- Test fail-silent: DatabaseError no propaga al caller.
- Test extensibilidad: audit_model swap sin cambiar la firma.
- No se mockea la DB salvo para el test de fail-silent.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import DatabaseError

from apps.audit.models import AuditLog, AuditStatus, BaseAuditLog
from apps.audit.services import create_audit_entry, log_action, log_failure

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def user(db):
    return User.objects.create_user(
        email="svc_auditor@test.com",
        username="svc_auditor",
        password="StrongPass123!",  # noqa: S106 # NOSONAR
    )


# ---------------------------------------------------------------------------
# create_audit_entry — función genérica
# ---------------------------------------------------------------------------


class TestCreateAuditEntry:
    def test_returns_audit_log_instance(self):
        entry = create_audit_entry(action="user.created", resource="user")
        assert isinstance(entry, AuditLog)
        assert entry.pk is not None

    def test_status_success_by_default(self):
        entry = create_audit_entry(action="user.listed", resource="user")
        assert entry is not None
        assert entry.status == AuditStatus.SUCCESS

    def test_user_none_by_default(self):
        entry = create_audit_entry(action="system.startup", resource="system")
        assert entry is not None
        assert entry.user is None

    def test_user_is_stored(self, user):
        entry = create_audit_entry(
            user=user,
            action="user.login",
            resource="session",
        )
        assert entry is not None
        assert entry.user_id == user.pk  # type: ignore[attr-defined]

    def test_metadata_stored(self):
        payload = {"email": "test@example.com", "source": "admin"}
        entry = create_audit_entry(
            action="user.created",
            resource="user",
            metadata=payload,
        )
        assert entry is not None
        entry.refresh_from_db()
        assert entry.metadata == payload

    def test_metadata_defaults_to_empty_dict_when_none(self):
        entry = create_audit_entry(action="user.listed", resource="user", metadata=None)
        assert entry is not None
        assert entry.metadata == {}

    def test_ip_address_stored(self):
        entry = create_audit_entry(
            action="auth.login",
            resource="session",
            ip_address="10.0.0.1",
        )
        assert entry is not None
        assert entry.ip_address == "10.0.0.1"

    def test_user_agent_stored(self):
        ua = "Mozilla/5.0 (compatible; audit-test)"
        entry = create_audit_entry(
            action="auth.login",
            resource="session",
            user_agent=ua,
        )
        assert entry is not None
        assert entry.user_agent == ua

    def test_custom_correlation_id_respected(self):
        cid = uuid.uuid4()
        entry = create_audit_entry(
            action="payment.approved",
            resource="payment",
            correlation_id=cid,
        )
        assert entry is not None
        assert entry.correlation_id == cid

    def test_auto_generates_correlation_id_when_none(self):
        entry = create_audit_entry(action="user.created", resource="user")
        assert entry is not None
        assert isinstance(entry.correlation_id, uuid.UUID)

    def test_resource_id_stored(self):
        entry = create_audit_entry(
            action="user.updated",
            resource="user",
            resource_id="42",
        )
        assert entry is not None
        assert entry.resource_id == "42"

    def test_custom_audit_model_used(self):
        """El parámetro audit_model permite usar distintas clases de log."""
        entry = create_audit_entry(
            audit_model=AuditLog,
            action="custom.action",
            resource="custom",
        )
        assert type(entry) is AuditLog

    def test_fail_silent_on_database_error(self):
        """DatabaseError no se propaga al caller — retorna None."""
        with patch.object(AuditLog, "save", side_effect=DatabaseError("DB unavailable")):
            result = create_audit_entry(action="user.created", resource="user")
        assert result is None

    def test_fail_silent_does_not_raise(self):
        """Verificación explícita: no se lanza ninguna excepción."""
        with patch.object(AuditLog, "save", side_effect=DatabaseError):
            try:
                create_audit_entry(action="user.created", resource="user")
            except DatabaseError:
                pytest.fail("create_audit_entry propagó DatabaseError al caller")

    def test_persisted_entry_is_retrievable(self):
        entry = create_audit_entry(action="user.deactivated", resource="user", resource_id="7")
        assert entry is not None
        fetched = AuditLog.objects.get(pk=entry.pk)
        assert fetched.action == "user.deactivated"
        assert fetched.resource_id == "7"


# ---------------------------------------------------------------------------
# log_action
# ---------------------------------------------------------------------------


class TestLogAction:
    def test_creates_success_entry(self):
        entry = log_action(action="user.created", resource="user")
        assert entry is not None
        assert entry.status == AuditStatus.SUCCESS

    def test_returns_audit_log_instance(self):
        entry = log_action(action="user.listed", resource="user")
        assert isinstance(entry, AuditLog)

    def test_with_user(self, user):
        entry = log_action(user=user, action="user.updated", resource="user", resource_id=str(user.pk))
        assert entry is not None
        assert entry.user_id == user.pk  # type: ignore[attr-defined]

    def test_with_metadata(self):
        entry = log_action(
            action="user.created",
            resource="user",
            metadata={"email": "new@test.com"},
        )
        assert entry is not None
        assert entry.metadata["email"] == "new@test.com"

    def test_anonymous_action(self):
        """Acciones del sistema sin usuario asociado."""
        entry = log_action(action="system.health_check", resource="system")
        assert entry is not None
        assert entry.user is None
        assert entry.status == AuditStatus.SUCCESS

    def test_correlation_id_auto_generated(self):
        entry = log_action(action="user.listed", resource="user")
        assert entry is not None
        assert isinstance(entry.correlation_id, uuid.UUID)

    def test_explicit_correlation_id(self):
        cid = uuid.uuid4()
        entry = log_action(
            action="user.created",
            resource="user",
            correlation_id=cid,
        )
        assert entry is not None
        assert entry.correlation_id == cid

    def test_ip_and_user_agent_stored(self):
        entry = log_action(
            action="auth.login",
            resource="session",
            ip_address="172.16.0.1",
            user_agent="TestAgent/1.0",
        )
        assert entry is not None
        assert entry.ip_address == "172.16.0.1"
        assert entry.user_agent == "TestAgent/1.0"

    def test_fail_silent_on_db_error(self):
        with patch.object(AuditLog, "save", side_effect=DatabaseError):
            result = log_action(action="user.created", resource="user")
        assert result is None


# ---------------------------------------------------------------------------
# log_failure
# ---------------------------------------------------------------------------


class TestLogFailure:
    def test_creates_failure_entry(self):
        entry = log_failure(action="auth.login", resource="session")
        assert entry is not None
        assert entry.status == AuditStatus.FAILURE

    def test_returns_audit_log_instance(self):
        entry = log_failure(action="auth.login", resource="session")
        assert isinstance(entry, AuditLog)

    def test_with_reason_in_metadata(self):
        entry = log_failure(
            action="auth.login",
            resource="session",
            metadata={"reason": "invalid_credentials"},
        )
        assert entry is not None
        assert entry.metadata["reason"] == "invalid_credentials"

    def test_anonymous_failure(self):
        """Fallo sin usuario (ej: intento no autenticado)."""
        entry = log_failure(
            action="auth.login",
            resource="session",
            ip_address="1.2.3.4",
        )
        assert entry is not None
        assert entry.user is None
        assert entry.status == AuditStatus.FAILURE

    def test_with_user(self, user):
        """Fallo con usuario conocido (ej: acción no autorizada)."""
        entry = log_failure(
            user=user,
            action="report.export",
            resource="report",
            metadata={"reason": "insufficient_permissions"},
        )
        assert entry is not None
        assert entry.user_id == user.pk  # type: ignore[attr-defined]
        assert entry.status == AuditStatus.FAILURE

    def test_fail_silent_on_db_error(self):
        with patch.object(AuditLog, "save", side_effect=DatabaseError):
            result = log_failure(action="auth.login", resource="session")
        assert result is None

    def test_persisted_failure_is_retrievable(self):
        entry = log_failure(
            action="auth.brute_force",
            resource="session",
            ip_address="1.2.3.4",
        )
        assert entry is not None
        fetched = AuditLog.objects.get(pk=entry.pk)
        assert fetched.status == AuditStatus.FAILURE
        assert fetched.action == "auth.brute_force"


# ---------------------------------------------------------------------------
# Extensibilidad: múltiples entradas con correlation_id compartido
# ---------------------------------------------------------------------------


class TestCorrelationIdPattern:
    def test_same_correlation_id_across_multiple_logs(self):
        """
        Patrón event-driven: una operación compuesta genera múltiples
        eventos correlacionados por el mismo UUID.
        """
        cid = uuid.uuid4()

        log_action(
            action="user.created",
            resource="user",
            resource_id="99",
            correlation_id=cid,
        )
        log_action(
            action="role.assigned",
            resource="role",
            resource_id="1",
            correlation_id=cid,
        )
        log_action(
            action="notification.sent",
            resource="notification",
            resource_id="99",
            correlation_id=cid,
        )

        logs = AuditLog.objects.filter(correlation_id=cid)
        assert logs.count() == 3
        actions = set(logs.values_list("action", flat=True))
        assert actions == {"user.created", "role.assigned", "notification.sent"}
