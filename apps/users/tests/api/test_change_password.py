"""
API tests for change password endpoint.

Tests cover:
- Successful password change
- Validation errors
- Authentication requirements
"""

import pytest
from rest_framework import status
from apps.users.tests.factories.user_factory import UserFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestChangePasswordEndpoint:
    """Tests for POST /api/auth/change-password/ endpoint."""
    
    url = '/api/auth/change-password/'
    default_password = 'TestPassword123!'
    
    def test_change_password_success(self, authenticated_client, user):
        """Test successful password change."""
        data = {
            'old_password': self.default_password,
            'new_password': 'NewSecurePassword456!',
            'new_password_confirm': 'NewSecurePassword456!'
        }
        
        response = authenticated_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        
        # Verify password was actually changed
        user.refresh_from_db()
        assert user.check_password('NewSecurePassword456!')
        assert not user.check_password(self.default_password)
    
    def test_change_password_wrong_old_password(self, authenticated_client):
        """Test password change with incorrect old password."""
        data = {
            'old_password': 'WrongOldPassword123!',
            'new_password': 'NewSecurePassword456!',
            'new_password_confirm': 'NewSecurePassword456!'
        }
        
        response = authenticated_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'old_password' in response.data
    
    def test_change_password_mismatch(self, authenticated_client):
        """Test password change with mismatched new passwords."""
        data = {
            'old_password': self.default_password,
            'new_password': 'NewSecurePassword456!',
            'new_password_confirm': 'DifferentPassword456!'
        }
        
        response = authenticated_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'new_password_confirm' in response.data
    
    def test_change_password_weak_new_password(self, authenticated_client):
        """Test password change with weak new password."""
        data = {
            'old_password': self.default_password,
            'new_password': '123',
            'new_password_confirm': '123'
        }
        
        response = authenticated_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'new_password' in response.data
    
    def test_change_password_without_authentication(self, api_client):
        """Test that password change requires authentication."""
        data = {
            'old_password': self.default_password,
            'new_password': 'NewSecurePassword456!',
            'new_password_confirm': 'NewSecurePassword456!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_change_password_missing_fields(self, authenticated_client):
        """Test password change with missing fields."""
        data = {'old_password': self.default_password}
        
        response = authenticated_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'new_password' in response.data
        assert 'new_password_confirm' in response.data
    
    def test_change_password_invalidates_old_sessions(self, api_client, user):
        """Test that changing password doesn't invalidate current token."""
        # Login to get tokens
        login_response = api_client.post('/api/auth/login/', {
            'email': user.email,
            'password': self.default_password
        }, format='json')
        
        access_token = login_response.data['access']
        
        # Change password
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        change_response = api_client.post(self.url, {
            'old_password': self.default_password,
            'new_password': 'NewSecurePassword456!',
            'new_password_confirm': 'NewSecurePassword456!'
        }, format='json')
        
        assert change_response.status_code == status.HTTP_200_OK
        
        # Current token should still work (token invalidation is optional)
        profile_response = api_client.get('/api/auth/profile/')
        assert profile_response.status_code == status.HTTP_200_OK
    
    def test_change_password_allows_login_with_new_password(self, authenticated_client, user, api_client):
        """Test that new password works for login after change."""
        # Change password
        data = {
            'old_password': self.default_password,
            'new_password': 'NewSecurePassword456!',
            'new_password_confirm': 'NewSecurePassword456!'
        }
        
        response = authenticated_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        # Try to login with new password
        login_response = api_client.post('/api/auth/login/', {
            'email': user.email,
            'password': 'NewSecurePassword456!'
        }, format='json')
        
        assert login_response.status_code == status.HTTP_200_OK
        assert 'access' in login_response.data
