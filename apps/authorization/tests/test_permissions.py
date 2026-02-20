"""
Tests para authorization.permissions (DRF BasePermission)
============================================================
Pruebas unitarias de las clases de permiso DRF:
  - HasPermission
  - HasAnyPermission
  - HasAllPermissions
"""

import pytest
from unittest.mock import MagicMock, patch

from apps.authorization.permissions import HasAllPermissions, HasAnyPermission, HasPermission

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_request(user=None) -> MagicMock:
    request = MagicMock()
    request.user = user or MagicMock()
    return request


# ---------------------------------------------------------------------------
# Tests: HasPermission factory
# ---------------------------------------------------------------------------

class TestHasPermission:

    def test_returns_a_class(self):
        klass = HasPermission("conciliacion.run")
        assert isinstance(klass, type)

    def test_class_is_instantiable_by_drf(self):
        """DRF llama permission_class() sin argumentos; debe funcionar."""
        klass = HasPermission("conciliacion.run")
        instance = klass()
        assert hasattr(instance, "has_permission")

    def test_has_descriptive_name(self):
        klass = HasPermission("conciliacion.run")
        assert "conciliacion.run" in klass.__name__

    def test_has_permission_returns_true_when_service_returns_true(self):
        klass = HasPermission("conciliacion.run")
        instance = klass()
        request = make_request()

        with patch(
            "apps.authorization.permissions.user_has_permission", return_value=True
        ) as mock_service:
            result = instance.has_permission(request, MagicMock())

        assert result is True
        mock_service.assert_called_once_with(request.user, "conciliacion.run")

    def test_has_permission_returns_false_when_service_returns_false(self):
        klass = HasPermission("conciliacion.run")
        instance = klass()
        request = make_request()

        with patch(
            "apps.authorization.permissions.user_has_permission", return_value=False
        ):
            result = instance.has_permission(request, MagicMock())

        assert result is False

    def test_different_codes_produce_different_classes(self):
        klass_a = HasPermission("conciliacion.run")
        klass_b = HasPermission("reportes.export")
        assert klass_a is not klass_b
        assert klass_a.__name__ != klass_b.__name__

    def test_message_contains_permission_code(self):
        klass = HasPermission("conciliacion.run")
        instance = klass()
        message = getattr(instance, "message", "")
        assert "conciliacion.run" in message


# ---------------------------------------------------------------------------
# Tests: HasAnyPermission
# ---------------------------------------------------------------------------

class TestHasAnyPermission:

    def _make_instance(self, *codes):
        return HasAnyPermission(*codes)()

    def test_returns_true_if_user_has_first_permission(self):
        instance = self._make_instance("perm.a", "perm.b")
        request = make_request()

        def side_effect(user, code):
            return code == "perm.a"

        with patch("apps.authorization.permissions.user_has_permission", side_effect=side_effect):
            assert instance.has_permission(request, MagicMock()) is True

    def test_returns_true_if_user_has_second_permission(self):
        instance = self._make_instance("perm.a", "perm.b")
        request = make_request()

        def side_effect(user, code):
            return code == "perm.b"

        with patch("apps.authorization.permissions.user_has_permission", side_effect=side_effect):
            assert instance.has_permission(request, MagicMock()) is True

    def test_returns_false_if_user_has_none(self):
        instance = self._make_instance("perm.a", "perm.b")
        request = make_request()

        with patch("apps.authorization.permissions.user_has_permission", return_value=False):
            assert instance.has_permission(request, MagicMock()) is False


# ---------------------------------------------------------------------------
# Tests: HasAllPermissions
# ---------------------------------------------------------------------------

class TestHasAllPermissions:

    def _make_instance(self, *codes):
        return HasAllPermissions(*codes)()

    def test_returns_true_if_user_has_all(self):
        instance = self._make_instance("perm.a", "perm.b")
        request = make_request()

        with patch("apps.authorization.permissions.user_has_permission", return_value=True):
            assert instance.has_permission(request, MagicMock()) is True

    def test_returns_false_if_user_lacks_one(self):
        instance = self._make_instance("perm.a", "perm.b")
        request = make_request()

        def side_effect(user, code):
            return code == "perm.a"

        with patch("apps.authorization.permissions.user_has_permission", side_effect=side_effect):
            assert instance.has_permission(request, MagicMock()) is False

    def test_returns_false_if_user_has_none(self):
        instance = self._make_instance("perm.a", "perm.b")
        request = make_request()

        with patch("apps.authorization.permissions.user_has_permission", return_value=False):
            assert instance.has_permission(request, MagicMock()) is False
