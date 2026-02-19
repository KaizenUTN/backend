"""
API tests for user profile endpoint.

Tests cover:
- Viewing profile
- Updating profile
- Authentication requirements
"""

import pytest
from rest_framework import status
from apps.users.tests.factories.user_factory import UserFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestProfileEndpoint:
    """Tests for /api/auth/profile/ endpoint."""
    
    url = '/api/auth/profile/'
    
    def test_get_profile_success(self, authenticated_client, user):
        """Test retrieving user profile."""
        response = authenticated_client.get(self.url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == user.id
        assert response.data['email'] == user.email
        assert response.data['username'] == user.username
        assert 'password' not in response.data
    
    def test_get_profile_without_authentication(self, api_client):
        """Test that profile requires authentication."""
        response = api_client.get(self.url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_profile_patch(self, authenticated_client, user):
        """Test updating profile with PATCH."""
        data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        
        response = authenticated_client.patch(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Updated'
        assert response.data['last_name'] == 'Name'
        
        # Verify database was updated
        user.refresh_from_db()
        assert user.first_name == 'Updated'
        assert user.last_name == 'Name'
    
    def test_update_profile_put(self, authenticated_client, user):
        """Test updating profile with PUT."""
        data = {
            'username': user.username,
            'email': user.email,
            'first_name': 'Complete',
            'last_name': 'Update'
        }
        
        response = authenticated_client.put(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Complete'
        assert response.data['last_name'] == 'Update'
    
    def test_update_profile_cannot_change_email(self, authenticated_client, user):
        """Test that email cannot be changed via profile update."""
        original_email = user.email
        
        data = {
            'email': 'newemail@example.com',
            'first_name': 'Test'
        }
        
        response = authenticated_client.patch(self.url, data, format='json')
        
        # Should succeed but email should not change
        assert response.status_code == status.HTTP_200_OK
        
        user.refresh_from_db()
        assert user.email == original_email  # Email should not change
        assert user.first_name == 'Test'  # Other fields should update
    
    def test_update_profile_partial(self, authenticated_client, user):
        """Test partial profile update."""
        original_last_name = user.last_name
        
        data = {'first_name': 'OnlyFirst'}
        
        response = authenticated_client.patch(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'OnlyFirst'
        assert response.data['last_name'] == original_last_name
    
    def test_update_profile_without_authentication(self, api_client):
        """Test that profile update requires authentication."""
        data = {'first_name': 'Should Fail'}
        
        response = api_client.patch(self.url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_profile_shows_full_name(self, authenticated_client, user):
        """Test that profile includes full_name property."""
        user.first_name = 'John'
        user.last_name = 'Doe'
        user.save()
        
        response = authenticated_client.get(self.url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['full_name'] == 'John Doe'
    
    def test_profile_includes_timestamps(self, authenticated_client):
        """Test that profile includes created_at and updated_at."""
        response = authenticated_client.get(self.url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'created_at' in response.data
        assert 'updated_at' in response.data
