"""
Tests para authorization.services
===================================
Pruebas unitarias para la función central `user_has_permission`
y la función auxiliar `get_user_permissions`.

Estrategia: objetos DoubleTambién se usan mocks simples para evitar
dependencias de base de datos en tests estrictamente unitarios,
y tests de integración con base de datos para los casos reales.
"""

import pytest
from unittest.mock import MagicMock, PropertyMock

from apps.authorization.services import get_user_permissions, user_has_permission

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(
    is_authenticated: bool = True,
    is_active: bool = True,
    role=None,
) -> MagicMock:
    """Crea un mock de User con los atributos mínimos necesarios."""
    user = MagicMock()
    user.is_authenticated = is_authenticated
    user.is_active = is_active
    user.role = role
    return user


def make_role(*permission_codes: str) -> MagicMock:
    """Crea un mock de Role cuyo queryset de permissions filtra por códigos."""
    role = MagicMock()
    role.permissions.filter.return_value.exists.side_effect = (
        lambda: True  # se evalúa en has_permission; mock below
    )
    # Configuramos filter().exists() para devolver True solo si el código está en la lista.
    def filter_side_effect(code):
        exists_mock = MagicMock()
        exists_mock.exists.return_value = code in permission_codes
        return exists_mock

    role.permissions.filter.side_effect = filter_side_effect

    # Para get_user_permissions usamos values_list().
    role.permissions.values_list.return_value = list(permission_codes)
    return role


# ---------------------------------------------------------------------------
# Tests: user_has_permission
# ---------------------------------------------------------------------------

class TestUserHasPermission:

    def test_returns_false_for_none_user(self):
        assert user_has_permission(None, "conciliacion.run") is False

    def test_returns_false_for_anonymous_user(self):
        user = make_user(is_authenticated=False)
        assert user_has_permission(user, "conciliacion.run") is False

    def test_returns_false_for_inactive_user(self):
        role = make_role("conciliacion.run")
        user = make_user(is_active=False, role=role)
        assert user_has_permission(user, "conciliacion.run") is False

    def test_returns_false_when_user_has_no_role(self):
        user = make_user(role=None)
        assert user_has_permission(user, "conciliacion.run") is False

    def test_returns_true_when_role_has_permission(self):
        role = make_role("conciliacion.run")
        user = make_user(role=role)
        assert user_has_permission(user, "conciliacion.run") is True

    def test_returns_false_when_role_lacks_permission(self):
        role = make_role("conciliacion.view")
        user = make_user(role=role)
        assert user_has_permission(user, "conciliacion.run") is False

    def test_returns_false_for_empty_permission_code(self):
        role = make_role("conciliacion.run")
        user = make_user(role=role)
        assert user_has_permission(user, "") is False

    def test_is_case_sensitive(self):
        """El código del permiso es case-sensitive."""
        role = make_role("Conciliacion.Run")
        user = make_user(role=role)
        assert user_has_permission(user, "conciliacion.run") is False


# ---------------------------------------------------------------------------
# Tests: get_user_permissions
# ---------------------------------------------------------------------------

class TestGetUserPermissions:

    def test_returns_empty_list_for_none_user(self):
        assert get_user_permissions(None) == []

    def test_returns_empty_list_for_anonymous_user(self):
        user = make_user(is_authenticated=False)
        assert get_user_permissions(user) == []

    def test_returns_empty_list_for_inactive_user(self):
        role = make_role("conciliacion.run")
        user = make_user(is_active=False, role=role)
        assert get_user_permissions(user) == []

    def test_returns_empty_list_when_user_has_no_role(self):
        user = make_user(role=None)
        assert get_user_permissions(user) == []

    def test_returns_permission_codes_for_user_with_role(self):
        codes = ("conciliacion.run", "conciliacion.view", "dashboard.view")
        role = make_role(*codes)
        user = make_user(role=role)
        result = get_user_permissions(user)
        assert set(result) == set(codes)
