"""
Custom API client utilities for testing.

Provides helper methods for common API operations in tests.
"""

from rest_framework.test import APIClient as DRFAPIClient
from rest_framework_simplejwt.tokens import RefreshToken


class APIClient(DRFAPIClient):
    """
    Extended API client with additional helper methods for testing.
    
    Usage:
        client = APIClient()
        client.authenticate(user)
        response = client.get('/api/endpoint/')
    """
    
    def authenticate(self, user):
        """
        Authenticate client with user using force_authenticate.
        
        Args:
            user: User instance to authenticate
        
        Usage:
            client.authenticate(user)
            response = client.get('/api/auth/profile/')
        """
        self.force_authenticate(user=user)
    
    def authenticate_with_token(self, user):
        """
        Authenticate client with JWT token in Authorization header.
        
        Args:
            user: User instance to generate token for
        
        Returns:
            dict: Dictionary with access and refresh tokens
        
        Usage:
            tokens = client.authenticate_with_token(user)
            response = client.get('/api/auth/profile/')
        """
        refresh = RefreshToken.for_user(user)
        self.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
        
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user
        }
    
    def unauthenticate(self):
        """
        Remove authentication from client.
        
        Usage:
            client.authenticate(user)
            # ... make requests ...
            client.unauthenticate()
            # ... make unauthenticated requests ...
        """
        self.force_authenticate(user=None)
        self.credentials()  # Clear credentials
    
    def login_user(self, email, password):
        """
        Login user via API and set authentication token.
        
        Args:
            email: User's email
            password: User's password
        
        Returns:
            Response: Login response
        
        Usage:
            response = client.login_user('test@example.com', 'password')
            if response.status_code == 200:
                # Client is now authenticated
                profile = client.get('/api/auth/profile/')
        """
        response = self.post(
            '/api/auth/login/',
            {'email': email, 'password': password},
            format='json'
        )
        
        if response.status_code == 200 and 'access' in response.data:
            self.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        
        return response
    
    def register_user(self, username, email, password, first_name='Test', last_name='User'):
        """
        Register user via API and set authentication token.
        
        Args:
            username: Username
            email: Email address
            password: Password
            first_name: First name (default: 'Test')
            last_name: Last name (default: 'User')
        
        Returns:
            Response: Registration response
        
        Usage:
            response = client.register_user('newuser', 'new@test.com', 'Pass123!')
            if response.status_code == 201:
                # Client is now authenticated
                profile = client.get('/api/auth/profile/')
        """
        response = self.post(
            '/api/auth/register/',
            {
                'username': username,
                'email': email,
                'password': password,
                'password_confirm': password,
                'first_name': first_name,
                'last_name': last_name
            },
            format='json'
        )
        
        if response.status_code == 201 and 'access' in response.data:
            self.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        
        return response


def get_auth_header(user):
    """
    Generate Authorization header with JWT token for user.
    
    Args:
        user: User instance
    
    Returns:
        dict: Header dictionary
    
    Usage:
        headers = get_auth_header(user)
        response = client.get('/api/endpoint/', **headers)
    """
    refresh = RefreshToken.for_user(user)
    return {'HTTP_AUTHORIZATION': f'Bearer {str(refresh.access_token)}'}


def get_tokens_for_user(user):
    """
    Generate JWT tokens for user.
    
    Args:
        user: User instance
    
    Returns:
        dict: Dictionary with access and refresh tokens
    
    Usage:
        tokens = get_tokens_for_user(user)
        access = tokens['access']
        refresh = tokens['refresh']
    """
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh)
    }
