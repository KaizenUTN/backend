"""
Unit tests for users.services.

Each service function is tested in isolation against a real DB
(django_db) — no mocking, so transactional semantics are verified too.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.authorization.models import Permission, Role
from apps.users.models import User
from apps.users.services import create_user, deactivate_user, reset_password, update_user
from apps.users.tests.factories.user_factory import UserFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def role_operador(db):
    """Rol Operador sin permisos — suficiente para testear FK."""
    return Role.objects.create(name='Operador')


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_creates_user_with_basic_fields(self):
        user = create_user(
            email='nuevo@example.com',
            first_name='Ana',
            last_name='García',
            password='SecurePass123!',  # noqa: S106 # NOSONAR
        )

        assert user.pk is not None
        assert user.email == 'nuevo@example.com'
        assert user.first_name == 'Ana'
        assert user.last_name == 'García'
        assert user.is_active is True

    def test_password_is_hashed(self):
        user = create_user(
            email='hash@example.com',
            first_name='H',
            last_name='H',
            password='SecurePass123!',  # noqa: S106 # NOSONAR
        )
        assert user.check_password('SecurePass123!')
        # El campo password almacena el hash, no el texto plano
        assert user.password != 'SecurePass123!'

    def test_username_derived_from_email(self):
        user = create_user(
            email='juanperez@example.com',
            first_name='Juan',
            last_name='Pérez',
            password='SecurePass456!',  # noqa: S106 # NOSONAR
        )
        assert user.username.startswith('juanperez')

    def test_duplicate_email_raises(self):
        UserFactory(email='dup@example.com')
        with pytest.raises(ValidationError, match='email'):
            create_user(
                email='dup@example.com',
                first_name='X',
                last_name='Y',
                password='SecurePass123!',  # noqa: S106 # NOSONAR
            )

    def test_weak_password_raises(self):
        with pytest.raises(ValidationError):
            create_user(
                email='weak@example.com',
                first_name='W',
                last_name='P',
                password='123',  # noqa: S106 # NOSONAR
            )

    def test_can_set_role(self, role_operador):
        user = create_user(
            email='withrole@example.com',
            first_name='R',
            last_name='R',
            password='SecurePass123!',  # noqa: S106 # NOSONAR
            role_id=role_operador.pk,
        )
        assert user.role_id == role_operador.pk

    def test_can_create_inactive(self):
        user = create_user(
            email='inactive@example.com',
            first_name='I',
            last_name='I',
            password='SecurePass123!',  # noqa: S106 # NOSONAR
            is_active=False,
        )
        assert user.is_active is False

    def test_username_collision_resolved(self):
        """Si el username base ya existe, se añade un sufijo numérico."""
        # Forzar un usuario con username='maria' exacto para provocar colisión
        existing = UserFactory(email='maria@example.com')
        existing.username = 'maria'
        existing.save()
        # El segundo usuario con mismo prefijo de email debe recibir 'maria1'
        user2 = create_user(
            email='maria@other.com',
            first_name='Maria',
            last_name='B',
            password='SecurePass123!',  # noqa: S106 # NOSONAR
        )
        assert user2.username.startswith('maria')
        assert user2.username != 'maria'


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------

class TestUpdateUser:
    def test_update_first_name(self):
        user = UserFactory(first_name='Antiguo')
        updated = update_user(user=user, first_name='Nuevo')
        assert updated.first_name == 'Nuevo'
        user.refresh_from_db()
        assert user.first_name == 'Nuevo'

    def test_update_last_name(self):
        user = UserFactory(last_name='Apellido')
        updated = update_user(user=user, last_name='NuevoApellido')
        assert updated.last_name == 'NuevoApellido'

    def test_update_role(self, role_operador):
        user = UserFactory()
        updated = update_user(user=user, role_id=role_operador.pk)
        assert updated.role_id == role_operador.pk
        user.refresh_from_db()
        assert user.role_id == role_operador.pk

    def test_update_multiple_fields(self, role_operador):
        user = UserFactory(first_name='A', last_name='B')
        updated = update_user(
            user=user,
            first_name='C',
            last_name='D',
            role_id=role_operador.pk,
        )
        assert updated.first_name == 'C'
        assert updated.last_name == 'D'
        assert updated.role_id == role_operador.pk

    def test_no_fields_is_noop(self):
        user = UserFactory(first_name='Same')
        token_v = user.token_version
        update_user(user=user)
        user.refresh_from_db()
        assert user.first_name == 'Same'
        assert user.token_version == token_v


# ---------------------------------------------------------------------------
# deactivate_user
# ---------------------------------------------------------------------------

class TestDeactivateUser:
    def test_sets_inactive(self):
        user = UserFactory(is_active=True)
        deactivate_user(user=user)
        user.refresh_from_db()
        assert user.is_active is False

    def test_increments_token_version(self):
        user = UserFactory()
        original_version = user.token_version
        deactivate_user(user=user)
        user.refresh_from_db()
        assert user.token_version == original_version + 1

    def test_persisted_to_db(self):
        user = UserFactory(is_active=True)
        deactivate_user(user=user)
        from_db = User.objects.get(pk=user.pk)
        assert from_db.is_active is False


# ---------------------------------------------------------------------------
# reset_password
# ---------------------------------------------------------------------------

class TestResetPassword:
    def test_returns_string(self):
        user = UserFactory()
        temp = reset_password(user=user)
        assert isinstance(temp, str)
        assert len(temp) >= 16

    def test_new_password_authenticates(self):
        user = UserFactory()
        temp = reset_password(user=user)
        user.refresh_from_db()
        assert user.check_password(temp)

    def test_old_password_no_longer_works(self):
        user = UserFactory()
        reset_password(user=user)
        user.refresh_from_db()
        assert not user.check_password('TestPassword123!')

    def test_increments_token_version(self):
        user = UserFactory()
        original_version = user.token_version
        reset_password(user=user)
        user.refresh_from_db()
        assert user.token_version == original_version + 1

    def test_each_call_generates_different_password(self):
        user = UserFactory()
        p1 = reset_password(user=user)
        p2 = reset_password(user=user)
        assert p1 != p2
