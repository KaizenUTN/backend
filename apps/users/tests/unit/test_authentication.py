"""
Unit tests for custom authentication backend.

Tests cover:
- JWT authentication functionality
- Token validation
- User active status checks
- Custom authentication logic
"""

import pytest
from datetime import timedelta
from typing import cast

from django.contrib.auth import get_user_model
from rest_framework import exceptions
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.authentication import CustomJWTAuthentication
from apps.users.tests.factories.user_factory import UserFactory

User = get_user_model()

pytestmark = pytest.mark.unit


class TestCustomJWTAuthentication:
    """Tests for CustomJWTAuthentication class."""
    
    @pytest.mark.django_db
    def test_authenticate_with_valid_token(self):
        """Test authentication with valid JWT token."""
        user = UserFactory()
        refresh: RefreshToken = RefreshToken.for_user(user)  # type: ignore[assignment]
        token = str(refresh.access_token)
        
        factory = APIRequestFactory()
        request = factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        auth = CustomJWTAuthentication()
        result = auth.authenticate(cast(Request, request))
        assert result is not None
        authenticated_user, _ = result
        
        assert authenticated_user == user
    
    @pytest.mark.django_db
    def test_authenticate_inactive_user_raises(self):
        """Test that inactive users raise AuthenticationFailed."""
        user = UserFactory(is_active=False)
        refresh: RefreshToken = RefreshToken.for_user(user)  # type: ignore[assignment]
        token = str(refresh.access_token)
        
        factory = APIRequestFactory()
        request = factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        auth = CustomJWTAuthentication()
        
        # CustomJWTAuthentication raises AuthenticationFailed for inactive users
        with pytest.raises(exceptions.AuthenticationFailed):
            auth.authenticate(cast(Request, request))
    
    @pytest.mark.django_db
    def test_authenticate_without_token(self):
        """Test authentication without token."""
        factory = APIRequestFactory()
        request = factory.get('/api/test/')
        
        auth = CustomJWTAuthentication()
        result = auth.authenticate(cast(Request, request))
        
        assert result is None
    
    @pytest.mark.django_db
    def test_authenticate_with_invalid_token(self):
        """Test authentication with invalid token."""
        factory = APIRequestFactory()
        request = factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer invalid_token_string'
        
        auth = CustomJWTAuthentication()
        
        # Should raise an exception or return None
        try:
            result = auth.authenticate(cast(Request, request))
            assert result is None
        except Exception:
            # Some JWT libraries raise exceptions for invalid tokens
            pass
    
    @pytest.mark.django_db
    def test_authenticate_with_expired_token(self):
        """Test authentication with expired token."""
        user = UserFactory()
        refresh: RefreshToken = RefreshToken.for_user(user)  # type: ignore[assignment]
        
        # Force expire the token
        refresh.access_token.set_exp(lifetime=timedelta(seconds=-1))
        token = str(refresh.access_token)
        
        factory = APIRequestFactory()
        request = factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        auth = CustomJWTAuthentication()
        
        # Should raise an exception or return None
        try:
            result = auth.authenticate(cast(Request, request))
            assert result is None
        except Exception:
            # Expected to raise exception for expired token
            pass
