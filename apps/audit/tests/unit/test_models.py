"""
Tests: audit.models
===================
Verifica la estructura y comportamiento de BaseAuditLog y AuditLog.

Estrategia:
- AuditLog es la única clase concreta de esta app; se usa directamente.
- La herencia de BaseAuditLog se verifica inspeccionando sus campos.
- Se verifica que abstract=True hace que BaseAuditLog no tenga tabla.
"""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.audit.models import AuditLog, AuditStatus, BaseAuditLog

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def user(db):
    return User.objects.create_user(
        email="auditor@test.com",
        username="auditor",
        password="StrongPass123!",  # noqa: S106 # NOSONAR
    )


# ---------------------------------------------------------------------------
# BaseAuditLog (estructura abstract)
# ---------------------------------------------------------------------------


class TestBaseAuditLog:
    def test_is_abstract(self):
        assert BaseAuditLog._meta.abstract is True

    def test_required_fields_exist(self):
        field_names = {f.name for f in BaseAuditLog._meta.get_fields()}
        expected = {"user", "action", "resource", "resource_id", "status", "metadata", "ip_address", "user_agent", "timestamp", "correlation_id"}
        assert expected.issubset(field_names)

    def test_status_choices(self):
        assert AuditStatus.SUCCESS.label == "Exitoso"
        assert AuditStatus.FAILURE.label == "Fallido"


# ---------------------------------------------------------------------------
# AuditLog (clase concreta)
# ---------------------------------------------------------------------------


class TestAuditLogCreation:
    def test_create_with_minimum_fields(self):
        log = AuditLog.objects.create(
            action="user.created",
            resource="user",
        )
        assert log.pk is not None

    def test_user_is_nullable(self):
        log = AuditLog.objects.create(
            action="system.startup",
            resource="system",
        )
        assert log.user is None

    def test_create_with_user(self, user):
        log = AuditLog.objects.create(
            user=user,
            action="user.login",
            resource="session",
        )
        assert log.user_id == user.pk  # type: ignore[attr-defined]

    def test_status_defaults_to_success(self):
        log = AuditLog.objects.create(action="report.generated", resource="report")
        assert log.status == AuditStatus.SUCCESS

    def test_metadata_defaults_to_empty_dict(self):
        log = AuditLog.objects.create(action="user.listed", resource="user")
        assert log.metadata == {}

    def test_resource_id_defaults_to_empty_string(self):
        log = AuditLog.objects.create(action="user.viewed", resource="user")
        assert log.resource_id == ""

    def test_user_agent_defaults_to_empty_string(self):
        log = AuditLog.objects.create(action="auth.login", resource="session")
        assert log.user_agent == ""

    def test_timestamp_is_auto_populated(self):
        log = AuditLog.objects.create(action="user.created", resource="user")
        assert log.timestamp is not None

    def test_correlation_id_is_auto_generated_uuid(self):
        log = AuditLog.objects.create(action="user.created", resource="user")
        assert isinstance(log.correlation_id, uuid.UUID)

    def test_two_logs_have_different_correlation_ids(self):
        log1 = AuditLog.objects.create(action="user.created", resource="user")
        log2 = AuditLog.objects.create(action="user.created", resource="user")
        assert log1.correlation_id != log2.correlation_id

    def test_custom_correlation_id_is_respected(self):
        cid = uuid.uuid4()
        log = AuditLog.objects.create(
            action="payment.approved",
            resource="payment",
            correlation_id=cid,
        )
        assert log.correlation_id == cid

    def test_failure_status_persisted(self):
        log = AuditLog.objects.create(
            action="auth.login",
            resource="session",
            status=AuditStatus.FAILURE,
        )
        log.refresh_from_db()
        assert log.status == AuditStatus.FAILURE

    def test_metadata_stored_as_json(self):
        payload = {"email": "test@example.com", "role_id": 42}
        log = AuditLog.objects.create(
            action="user.created",
            resource="user",
            metadata=payload,
        )
        log.refresh_from_db()
        assert log.metadata == payload

    def test_ip_address_stored(self):
        log = AuditLog.objects.create(
            action="auth.login",
            resource="session",
            ip_address="192.168.1.100",
        )
        assert log.ip_address == "192.168.1.100"

    def test_ip_address_ipv6(self):
        log = AuditLog.objects.create(
            action="auth.login",
            resource="session",
            ip_address="2001:db8::1",
        )
        assert log.ip_address is not None


class TestAuditLogStr:
    def test_str_with_user(self, user):
        log = AuditLog.objects.create(
            user=user,
            action="user.updated",
            resource="user",
            status=AuditStatus.SUCCESS,
        )
        result = str(log)
        assert f"user:{user.pk}" in result
        assert "user.updated" in result
        assert "SUCCESS" in result

    def test_str_without_user(self):
        log = AuditLog.objects.create(
            action="system.startup",
            resource="system",
        )
        result = str(log)
        assert "anonymous" in result
        assert "system.startup" in result


class TestAuditLogOrdering:
    def test_default_ordering_is_newest_first(self):
        log1 = AuditLog.objects.create(action="action.first", resource="x")
        log2 = AuditLog.objects.create(action="action.second", resource="x")
        logs = list(AuditLog.objects.all())
        # newest primero
        assert logs[0].pk == log2.pk
        assert logs[1].pk == log1.pk

    def test_user_deleted_sets_null_on_audit(self, user):
        log = AuditLog.objects.create(user=user, action="user.login", resource="session")
        user.delete()
        log.refresh_from_db()
        assert log.user is None
