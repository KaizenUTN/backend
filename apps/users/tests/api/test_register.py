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
            'username': 'newuser',
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
        assert user.username == 'newuser'
        assert user.first_name == 'New'
        assert user.check_password('SecurePassword123!')
    
    def test_register_returns_jwt_tokens(self, api_client):
        """Test that registration returns valid JWT tokens."""
        data = {
            'username': 'testuser',
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
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        user_data = response.data['user']
        
        assert user_data['username'] == 'testuser'
        assert user_data['email'] == 'test@example.com'
        assert user_data['first_name'] == 'Test'
        assert user_data['last_name'] == 'User'
        assert user_data['full_name'] == 'Test User'
        assert 'password' not in user_data
    
    def test_register_password_mismatch(self, api_client):
        """Test registration with mismatched passwords."""
        data = {
            'username': 'testuser',
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
            'username': 'newuser',
            'email': 'existing@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data
    
    def test_register_duplicate_username(self, api_client):
        """Test registration with existing username."""
        UserFactory(username='existinguser')
        
        data = {
            'username': 'existinguser',
            'email': 'new@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'username' in response.data
    
    def test_register_missing_required_fields(self, api_client):
        """Test registration with missing required fields."""
        data = {
            'username': 'testuser',
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
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': '123',
            'password_confirm': '123'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data
    
    def test_register_invalid_email(self, api_client):
        """Test registration with invalid email format."""
        data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data
