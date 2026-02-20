"""
API tests for admin users endpoints.

Tests cover:
- GET  /api/users/                  — listar usuarios
- POST /api/users/                  — crear usuario
- GET  /api/users/{id}/             — obtener usuario
- PATCH /api/users/{id}/            — editar usuario
- POST /api/users/{id}/deactivate/  — desactivar usuario
- POST /api/users/{id}/reset-password/ — reset de contraseña

Cada grupo verifica autenticación, permisos RBAC y lógica de negocio.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authorization.models import Permission, Role
from apps.users.tests.factories.user_factory import UserFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _make_admin_role(permissions: list[str]) -> Role:
    """Crea un rol Administrador con los permisos indicados."""
    role, _ = Role.objects.get_or_create(name='Administrador_test')
    for code in permissions:
        perm, _ = Permission.objects.get_or_create(
            code=code,
            defaults={'description': code},
        )
        role.permissions.add(perm)
    return role


def _auth_client(user) -> APIClient:
    """Retorna un APIClient autenticado con JWT del usuario dado."""
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
    return client


@pytest.fixture()
def full_admin():
    """Usuario Administrador con todos los permisos de usuarios.*"""
    role = _make_admin_role([
        'usuarios.view',
        'usuarios.create',
        'usuarios.edit',
        'usuarios.delete',
    ])
    user = UserFactory(email='fulladmin@test.com')
    user.role = role
    user.save()
    return user


@pytest.fixture()
def admin_client(full_admin):
    """APIClient autenticado como full_admin."""
    return _auth_client(full_admin)


@pytest.fixture()
def view_only_admin():
    """Usuario con solo usuarios.view."""
    role = _make_admin_role(['usuarios.view'])
    user = UserFactory(email='viewonly@test.com')
    user.role = role
    user.save()
    return user


@pytest.fixture()
def view_client(view_only_admin):
    return _auth_client(view_only_admin)


@pytest.fixture()
def target_user():
    """Usuario de prueba sobre el que se operará."""
    return UserFactory(email='target@test.com', first_name='Target', last_name='User')


# ---------------------------------------------------------------------------
# GET /api/users/  — Listar usuarios
# ---------------------------------------------------------------------------

class TestUserListView:
    url = '/api/users/'

    def test_requires_auth(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_requires_permission(self, authenticated_client):
        """Usuario autenticado sin permiso usuarios.view → 403."""
        response = authenticated_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_paginated_list(self, admin_client):
        UserFactory.create_batch(3)
        response = admin_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'count' in response.data

    def test_filter_by_email(self, admin_client):
        UserFactory(email='unique_filter@example.com')
        response = admin_client.get(self.url, {'email': 'unique_filter'})
        assert response.status_code == status.HTTP_200_OK
        emails = [u['email'] for u in response.data['results']]
        assert all('unique_filter' in e for e in emails)

    def test_filter_by_is_active_false(self, admin_client):
        from apps.users.tests.factories.user_factory import InactiveUserFactory
        inactive = InactiveUserFactory(email='inactive_filter@example.com')
        response = admin_client.get(self.url, {'is_active': 'false'})
        assert response.status_code == status.HTTP_200_OK
        pks = [u['id'] for u in response.data['results']]
        assert inactive.pk in pks

    def test_response_contains_expected_fields(self, admin_client, target_user):
        response = admin_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        result = next(u for u in response.data['results'] if u['id'] == target_user.pk)
        assert 'email' in result
        assert 'first_name' in result
        assert 'last_name' in result
        assert 'is_active' in result
        assert 'role_name' in result


# ---------------------------------------------------------------------------
# POST /api/users/  — Crear usuario
# ---------------------------------------------------------------------------

class TestUserCreateView:
    url = '/api/users/'

    def test_requires_auth(self, api_client):
        response = api_client.post(self.url, {}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_requires_create_permission(self, view_client):
        """Solo usuarios.view no alcanza para crear."""
        data = {
            'email': 'new@example.com',
            'first_name': 'N',
            'last_name': 'N',
            'password': 'SecurePass123!',
        }
        response = view_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_success(self, admin_client):
        data = {
            'email': 'brand_new@example.com',
            'first_name': 'Brand',
            'last_name': 'New',
            'password': 'SecurePass123!',
        }
        response = admin_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['email'] == 'brand_new@example.com'
        assert 'id' in response.data

    def test_create_with_role(self, admin_client):
        role = _make_admin_role([])
        data = {
            'email': 'withrole@example.com',
            'first_name': 'R',
            'last_name': 'R',
            'password': 'SecurePass123!',
            'role_id': role.pk,
        }
        response = admin_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['role'] == role.pk

    def test_duplicate_email_returns_400(self, admin_client, target_user):
        data = {
            'email': target_user.email,
            'first_name': 'D',
            'last_name': 'D',
            'password': 'SecurePass123!',
        }
        response = admin_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_required_field_returns_400(self, admin_client):
        data = {'email': 'missing@example.com'}
        response = admin_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# GET /api/users/{id}/  — Obtener usuario
# ---------------------------------------------------------------------------

class TestUserDetailView:
    def _url(self, pk: int) -> str:
        return f'/api/users/{pk}/'

    def test_requires_auth(self, api_client, target_user):
        response = api_client.get(self._url(target_user.pk))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_user(self, admin_client, target_user):
        response = admin_client.get(self._url(target_user.pk))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == target_user.pk
        assert response.data['email'] == target_user.email

    def test_not_found_returns_404(self, admin_client):
        response = admin_client.get(self._url(999_999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_response_fields(self, admin_client, target_user):
        response = admin_client.get(self._url(target_user.pk))
        for field in ('id', 'email', 'first_name', 'last_name', 'is_active', 'role_name'):
            assert field in response.data


# ---------------------------------------------------------------------------
# PATCH /api/users/{id}/  — Editar usuario
# ---------------------------------------------------------------------------

class TestUserUpdateView:
    def _url(self, pk: int) -> str:
        return f'/api/users/{pk}/'

    def test_requires_edit_permission(self, view_client, target_user):
        response = view_client.patch(
            self._url(target_user.pk),
            {'first_name': 'Nuevo'},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_patch_first_name(self, admin_client, target_user):
        response = admin_client.patch(
            self._url(target_user.pk),
            {'first_name': 'Actualizado'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Actualizado'
        target_user.refresh_from_db()
        assert target_user.first_name == 'Actualizado'

    def test_patch_role(self, admin_client, target_user):
        role = _make_admin_role([])
        response = admin_client.patch(
            self._url(target_user.pk),
            {'role_id': role.pk},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['role'] == role.pk

    def test_patch_not_found_returns_404(self, admin_client):
        response = admin_client.patch(
            self._url(999_999),
            {'first_name': 'X'},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_empty_patch_is_valid(self, admin_client, target_user):
        """PATCH sin campos es semánticamente válido (no modifica nada)."""
        response = admin_client.patch(self._url(target_user.pk), {}, format='json')
        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# POST /api/users/{id}/deactivate/  — Desactivar usuario
# ---------------------------------------------------------------------------

class TestUserDeactivateView:
    def _url(self, pk: int) -> str:
        return f'/api/users/{pk}/deactivate/'

    def test_requires_delete_permission(self, view_client, target_user):
        response = view_client.post(self._url(target_user.pk))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_deactivate_success(self, admin_client, target_user):
        response = admin_client.post(self._url(target_user.pk))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_active'] is False
        target_user.refresh_from_db()
        assert target_user.is_active is False

    def test_deactivate_increments_token_version(self, admin_client, target_user):
        original_version = target_user.token_version
        admin_client.post(self._url(target_user.pk))
        target_user.refresh_from_db()
        assert target_user.token_version == original_version + 1

    def test_deactivate_already_inactive_returns_400(self, admin_client):
        from apps.users.tests.factories.user_factory import InactiveUserFactory
        inactive = InactiveUserFactory(email='alreadyinactive@test.com')
        response = admin_client.post(self._url(inactive.pk))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_deactivate_not_found_returns_404(self, admin_client):
        response = admin_client.post(self._url(999_999))
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /api/users/{id}/reset-password/  — Reset de contraseña
# ---------------------------------------------------------------------------

class TestUserResetPasswordView:
    def _url(self, pk: int) -> str:
        return f'/api/users/{pk}/reset-password/'

    def test_requires_edit_permission(self, view_client, target_user):
        response = view_client.post(self._url(target_user.pk))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reset_returns_temp_password(self, admin_client, target_user):
        response = admin_client.post(self._url(target_user.pk))
        assert response.status_code == status.HTTP_200_OK
        assert 'temp_password' in response.data
        assert isinstance(response.data['temp_password'], str)
        assert len(response.data['temp_password']) >= 16

    def test_reset_returns_user_object(self, admin_client, target_user):
        response = admin_client.post(self._url(target_user.pk))
        assert 'user' in response.data
        assert response.data['user']['id'] == target_user.pk

    def test_reset_password_actually_changes_password(self, admin_client, target_user):
        response = admin_client.post(self._url(target_user.pk))
        temp = response.data['temp_password']
        target_user.refresh_from_db()
        assert target_user.check_password(temp)

    def test_reset_increments_token_version(self, admin_client, target_user):
        original_version = target_user.token_version
        admin_client.post(self._url(target_user.pk))
        target_user.refresh_from_db()
        assert target_user.token_version == original_version + 1

    def test_reset_not_found_returns_404(self, admin_client):
        response = admin_client.post(self._url(999_999))
        assert response.status_code == status.HTTP_404_NOT_FOUND
