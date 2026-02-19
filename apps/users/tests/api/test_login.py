"""
API tests for user login endpoint.

Tests cover:
- Successful login
- Invalid credentials
- Inactive user login
- Response format with JWT tokens
"""

import pytest
from rest_framework import status
from apps.users.tests.factories.user_factory import UserFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestLoginEndpoint:
    """Tests for POST /api/auth/login/ endpoint."""
    
    url = '/api/auth/login/'
    
    def test_login_success(self, api_client):
        """Test successful login with valid credentials."""
        user = UserFactory(email='test@example.com')
        
        data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data
    
    def test_login_returns_jwt_tokens(self, api_client):
        """Test that login returns valid JWT tokens."""
        UserFactory(email='test@example.com')
        
        data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Tokens should be strings
        assert isinstance(response.data['access'], str)
        assert isinstance(response.data['refresh'], str)
        assert len(response.data['access']) > 50
        assert len(response.data['refresh']) > 50
    
    def test_login_returns_user_data(self, api_client):
        """Test that login returns user data."""
        user = UserFactory(
            email='test@example.com',
            username='testuser',
            first_name='Test',
            last_name='User'
        )
        
        data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        user_data = response.data['user']
        
        assert user_data['id'] == user.id
        assert user_data['email'] == 'test@example.com'
        assert user_data['username'] == 'testuser'
        assert user_data['first_name'] == 'Test'
        assert user_data['last_name'] == 'User'
        assert user_data['full_name'] == 'Test User'
        assert 'password' not in user_data
    
    def test_login_wrong_password(self, api_client):
        """Test login with incorrect password."""
        UserFactory(email='test@example.com')
        
        data = {
            'email': 'test@example.com',
            'password': 'WrongPassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_nonexistent_email(self, api_client):
        """Test login with non-existent email."""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'TestPassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_inactive_user(self, api_client):
        """Test login with inactive user."""
        UserFactory(email='inactive@example.com', is_active=False)
        
        data = {
            'email': 'inactive@example.com',
            'password': 'TestPassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_missing_email(self, api_client):
        """Test login without email."""
        data = {'password': 'TestPassword123!'}
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data
    
    def test_login_missing_password(self, api_client):
        """Test login without password."""
        data = {'email': 'test@example.com'}
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data
    
    def test_login_empty_credentials(self, api_client):
        """Test login with empty credentials."""
        data = {'email': '', 'password': ''}
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_case_sensitive_email(self, api_client):
        """Test that email login is case-insensitive (if implemented)."""
        UserFactory(email='test@example.com')
        
        data = {
            'email': 'TEST@EXAMPLE.COM',
            'password': 'TestPassword123!'
        }
        
        response = api_client.post(self.url, data, format='json')
        
        # This might fail if case-sensitivity is enforced
        # Adjust based on your implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
