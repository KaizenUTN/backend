"""
API tests for user registration endpoint.

Tests cover:
- Successful registration
- Validation errors
- Duplicate user handling
- Response format
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from apps.users.tests.factories.user_factory import UserFactory

User = get_user_model()

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestRegisterEndpoint:
    """Tests for POST /api/auth/register/ endpoint."""
    
    url = '/api/auth/register/'
    
    def test_register_success(self, api_client):
        """Test successful user registration."""
        data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data
        
        # Verify user was created
        user = User.objects.get(email='newuser@example.com')
        assert user.first_name == 'New'
        assert user.check_password('SecurePassword123!')
    
    def test_register_returns_jwt_tokens(self, api_client):
        """Test that registration returns valid JWT tokens."""
        data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Access token should be a string
        assert isinstance(response.data['access'], str)
        assert len(response.data['access']) > 50
        
        # Refresh token should be a string
        assert isinstance(response.data['refresh'], str)
        assert len(response.data['refresh']) > 50
    
    def test_register_returns_user_data(self, api_client):
        """Test that registration returns user data."""
        data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        user_data = response.data['user']
        
        assert user_data['email'] == 'test@example.com'
        assert user_data['first_name'] == 'Test'
        assert user_data['last_name'] == 'User'
        assert user_data['full_name'] == 'Test User'
        assert 'password' not in user_data
    
    def test_register_password_mismatch(self, api_client):
        """Test registration with mismatched passwords."""
        data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'DifferentPassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password_confirm' in response.data
    
    def test_register_duplicate_email(self, api_client):
        """Test registration with existing email."""
        UserFactory(email='existing@example.com')
        
        data = {
            'email': 'existing@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data
    
    def test_register_duplicate_username_handled(self, api_client):
        """Test that two users with the same email prefix can both register.
        Username is auto-generated from email; collisions are resolved internally."""
        # First user: username auto-generated as 'shared'
        resp1 = api_client.post(self.url, {
            'email': 'shared@example.com',
            'first_name': 'First',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }, format='json')
        assert resp1.status_code == status.HTTP_201_CREATED

        # Second user with the same prefix: collision resolved to 'shared1'
        resp2 = api_client.post(self.url, {
            'email': 'shared@other.com',
            'first_name': 'Second',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }, format='json')
        assert resp2.status_code == status.HTTP_201_CREATED
    
    def test_register_missing_required_fields(self, api_client):
        """Test registration with missing required fields."""
        data = {
            'email': 'test@example.com'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'first_name' in response.data
        assert 'last_name' in response.data
        assert 'password' in response.data
    
    def test_register_weak_password(self, api_client):
        """Test registration with weak password."""
        data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': '123',  # NOSONAR
            'password_confirm': '123'  # NOSONAR
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data
    
    def test_register_invalid_email(self, api_client):
        """Test registration with invalid email format."""
        data = {
            'email': 'invalid-email',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data
