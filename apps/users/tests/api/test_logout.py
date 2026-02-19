"""
API tests for user logout endpoint.

Tests cover:
- Successful logout
- Token blacklisting
- Unauthorized access
"""

import pytest
from rest_framework import status
from apps.users.tests.factories.user_factory import UserFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestLogoutEndpoint:
    """Tests for POST /api/auth/logout/ endpoint."""
    
    url = '/api/auth/logout/'
    
    def test_logout_success(self, api_client_with_token, tokens):
        """Test successful logout."""
        data = {'refresh': tokens['refresh']}
        
        response = api_client_with_token.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
    
    def test_logout_blacklists_token(self, api_client, tokens):
        """Test that logout blacklists the refresh token."""
        # Set authorization header
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        
        data = {'refresh': tokens['refresh']}
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Try to use the refresh token again
        refresh_url = '/api/auth/refresh/'
        refresh_response = api_client.post(
            refresh_url,
            {'refresh': tokens['refresh']},
            format='json'
        )
        
        # Should fail because token is blacklisted
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_logout_without_authentication(self, api_client):
        """Test logout without authentication token."""
        data = {'refresh': 'some_refresh_token'}
        
        response = api_client.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_logout_missing_refresh_token(self, api_client_with_token):
        """Test logout without providing refresh token."""
        response = api_client_with_token.post(self.url, {}, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_logout_invalid_refresh_token(self, api_client_with_token):
        """Test logout with invalid refresh token."""
        data = {'refresh': 'invalid_token_string'}
        
        response = api_client_with_token.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_logout_with_already_blacklisted_token(self, api_client_with_token, tokens):
        """Test logout with already blacklisted token."""
        # First logout
        data = {'refresh': tokens['refresh']}
        api_client_with_token.post(self.url, data, format='json')
        
        # Try to logout again with same token
        response = api_client_with_token.post(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
