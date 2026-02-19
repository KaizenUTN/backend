"""
Integration tests for complete authentication flow.

Tests cover:
- Complete user journey from registration to logout
- Token refresh workflows
- Multiple user interactions
- Real-world scenarios
"""

import pytest
from rest_framework import status

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestAuthenticationFlow:
    """Tests for complete authentication workflows."""
    
    def test_complete_user_journey(self, api_client):
        """Test complete user journey: register -> login -> profile -> logout."""
        # Step 1: Register
        register_data = {
            'username': 'journeyuser',
            'email': 'journey@example.com',
            'first_name': 'Journey',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        register_response = api_client.post(
            '/api/auth/register/',
            register_data,
            format='json'
        )
        
        assert register_response.status_code == status.HTTP_201_CREATED
        access_token = register_response.data['access']
        refresh_token = register_response.data['refresh']
        
        # Step 2: Access profile with token
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_response = api_client.get('/api/auth/profile/')
        
        assert profile_response.status_code == status.HTTP_200_OK
        assert profile_response.data['email'] == 'journey@example.com'
        
        # Step 3: Update profile
        update_response = api_client.patch(
            '/api/auth/profile/',
            {'first_name': 'Updated'},
            format='json'
        )
        
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data['first_name'] == 'Updated'
        
        # Step 4: Change password
        change_password_response = api_client.post(
            '/api/auth/change-password/',
            {
                'old_password': 'SecurePassword123!',
                'new_password': 'NewPassword456!',
                'new_password_confirm': 'NewPassword456!'
            },
            format='json'
        )
        
        assert change_password_response.status_code == status.HTTP_200_OK
        
        # Step 5: Logout
        logout_response = api_client.post(
            '/api/auth/logout/',
            {'refresh': refresh_token},
            format='json'
        )
        
        assert logout_response.status_code == status.HTTP_200_OK
        
        # Step 6: Verify cannot use blacklisted token
        refresh_response = api_client.post(
            '/api/auth/refresh/',
            {'refresh': refresh_token},
            format='json'
        )
        
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_register_and_immediate_login(self, api_client):
        """Test registering and immediately logging in."""
        # Register
        register_data = {
            'username': 'immediateuser',
            'email': 'immediate@example.com',
            'first_name': 'Immediate',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        register_response = api_client.post(
            '/api/auth/register/',
            register_data,
            format='json'
        )
        
        assert register_response.status_code == status.HTTP_201_CREATED
        
        # Login with same credentials
        login_response = api_client.post(
            '/api/auth/login/',
            {
                'email': 'immediate@example.com',
                'password': 'SecurePassword123!'
            },
            format='json'
        )
        
        assert login_response.status_code == status.HTTP_200_OK
        assert 'access' in login_response.data
    
    def test_token_refresh_workflow(self, api_client, user):
        """Test token refresh workflow."""
        # Login
        login_response = api_client.post(
            '/api/auth/login/',
            {
                'email': user.email,
                'password': 'TestPassword123!'
            },
            format='json'
        )
        
        assert login_response.status_code == status.HTTP_200_OK
        old_access = login_response.data['access']
        refresh_token = login_response.data['refresh']
        
        # Use access token
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {old_access}')
        profile_response = api_client.get('/api/auth/profile/')
        assert profile_response.status_code == status.HTTP_200_OK
        
        # Refresh token to get new access token
        refresh_response = api_client.post(
            '/api/auth/refresh/',
            {'refresh': refresh_token},
            format='json'
        )
        
        assert refresh_response.status_code == status.HTTP_200_OK
        new_access = refresh_response.data['access']
        assert new_access != old_access
        
        # Use new access token
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access}')
        profile_response2 = api_client.get('/api/auth/profile/')
        assert profile_response2.status_code == status.HTTP_200_OK
    
    def test_multiple_users_concurrent_access(self, api_client, multiple_users):
        """Test multiple users can access their profiles simultaneously."""
        users = multiple_users(3)
        tokens = []
        
        # Login all users and collect tokens
        for user in users:
            login_response = api_client.post(
                '/api/auth/login/',
                {
                    'email': user.email,
                    'password': 'TestPassword123!'
                },
                format='json'
            )
            
            assert login_response.status_code == status.HTTP_200_OK
            tokens.append(login_response.data['access'])
        
        # Each user accesses their profile
        for i, (user, token) in enumerate(zip(users, tokens)):
            api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            profile_response = api_client.get('/api/auth/profile/')
            
            assert profile_response.status_code == status.HTTP_200_OK
            assert profile_response.data['id'] == user.id
    
    def test_password_change_requires_relogin(self, api_client, user):
        """Test workflow where password change affects login."""
        # Login
        login_response = api_client.post(
            '/api/auth/login/',
            {
                'email': user.email,
                'password': 'TestPassword123!'
            },
            format='json'
        )
        
        access_token = login_response.data['access']
        
        # Change password
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        change_response = api_client.post(
            '/api/auth/change-password/',
            {
                'old_password': 'TestPassword123!',
                'new_password': 'NewPassword456!',
                'new_password_confirm': 'NewPassword456!'
            },
            format='json'
        )
        
        assert change_response.status_code == status.HTTP_200_OK
        
        # Try to login with old password (should fail)
        old_login_response = api_client.post(
            '/api/auth/login/',
            {
                'email': user.email,
                'password': 'TestPassword123!'
            },
            format='json'
        )
        
        assert old_login_response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Login with new password (should succeed)
        new_login_response = api_client.post(
            '/api/auth/login/',
            {
                'email': user.email,
                'password': 'NewPassword456!'
            },
            format='json'
        )
        
        assert new_login_response.status_code == status.HTTP_200_OK
    
    def test_profile_update_persistence(self, api_client, user):
        """Test that profile updates persist across sessions."""
        # Login
        login_response = api_client.post(
            '/api/auth/login/',
            {
                'email': user.email,
                'password': 'TestPassword123!'
            },
            format='json'
        )
        
        access_token = login_response.data['access']
        
        # Update profile
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        update_response = api_client.patch(
            '/api/auth/profile/',
            {
                'first_name': 'Persistent',
                'last_name': 'Update'
            },
            format='json'
        )
        
        assert update_response.status_code == status.HTTP_200_OK
        
        # Logout
        logout_response = api_client.post(
            '/api/auth/logout/',
            {'refresh': login_response.data['refresh']},
            format='json'
        )
        
        assert logout_response.status_code == status.HTTP_200_OK
        
        # Login again
        new_login_response = api_client.post(
            '/api/auth/login/',
            {
                'email': user.email,
                'password': 'TestPassword123!'
            },
            format='json'
        )
        
        new_access = new_login_response.data['access']
        
        # Check profile still has updates
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access}')
        profile_response = api_client.get('/api/auth/profile/')
        
        assert profile_response.status_code == status.HTTP_200_OK
        assert profile_response.data['first_name'] == 'Persistent'
        assert profile_response.data['last_name'] == 'Update'
