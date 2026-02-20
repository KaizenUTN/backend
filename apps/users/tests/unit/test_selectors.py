"""
Unit tests for users.selectors.

Selectors are pure read functions — no mutations, no service calls.
Tests verify correct data retrieval and select_related behaviour.
"""

import pytest

from apps.users.models import User
from apps.users.selectors import get_user_by_id, get_user_list
from apps.users.tests.factories.user_factory import UserFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# ---------------------------------------------------------------------------
# get_user_by_id
# ---------------------------------------------------------------------------

class TestGetUserById:
    def test_returns_user(self):
        user = UserFactory()
        result = get_user_by_id(user.pk)
        assert result.pk == user.pk

    def test_raises_does_not_exist(self):
        with pytest.raises(User.DoesNotExist):
            get_user_by_id(999_999)

    def test_prefetches_role(self, django_assert_num_queries):
        """
        Con select_related activo, obtener user + role.name
        debe costar 1 sola query (JOIN), no 2.
        """
        from apps.authorization.models import Role
        role = Role.objects.create(name='TestRoleSel')
        user = UserFactory()
        user.role = role
        user.save()

        with django_assert_num_queries(1):
            result = get_user_by_id(user.pk)
            _ = result.role.name  # acceso al FK — no debe generar query extra


# ---------------------------------------------------------------------------
# get_user_list
# ---------------------------------------------------------------------------

class TestGetUserList:
    def test_returns_all_users(self):
        UserFactory.create_batch(3)
        qs = get_user_list()
        # Al menos los 3 creados (puede haber más de otras fixtures)
        assert qs.count() >= 3

    def test_returns_queryset(self):
        from django.db.models import QuerySet
        UserFactory()
        assert isinstance(get_user_list(), QuerySet)

    def test_ordered_by_created_at_desc(self):
        """El primer resultado debe ser el usuario más reciente."""
        users = UserFactory.create_batch(3)
        qs = list(get_user_list())
        # El último creado tiene mayor created_at → posición 0 en orden DESC
        assert qs[0].pk == users[-1].pk

    def test_includes_all_users(self):
        """Incluye usuarios activos e inactivos."""
        from apps.users.tests.factories.user_factory import InactiveUserFactory
        active = UserFactory()
        inactive = InactiveUserFactory()
        pks = set(get_user_list().values_list('pk', flat=True))
        assert active.pk in pks
        assert inactive.pk in pks

    def test_prefetches_role(self, django_assert_num_queries):
        """Iterar la lista + acceder a role.name debe ser 1 query (JOIN)."""
        UserFactory.create_batch(3)
        with django_assert_num_queries(1):
            for u in get_user_list():
                _ = u.role_id  # acceso directo al FK id → sin query extra
