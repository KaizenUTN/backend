"""
Pytest configuration and global fixtures.

This file contains pytest configuration and fixtures that are available
to all test modules without needing to import them explicitly.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.fixture
def api_client():
    """
    DRF API client for making API requests in tests.
    
    Usage:
        def test_something(api_client):
            response = api_client.get('/api/endpoint/')
    """
    return APIClient()


@pytest.fixture
def django_client():
    """
    Django test client for making requests.
    
    Usage:
        def test_something(django_client):
            response = django_client.get('/admin/')
    """
    return Client()


@pytest.fixture
def test_password():
    """Common password for test users."""
    return "TestPassword123!"


@pytest.fixture
def create_user(db, test_password):
    """
    Factory fixture to create users with default or custom data.
    
    Usage:
        def test_something(create_user):
            user = create_user(username='testuser')
            user = create_user(email='custom@email.com', is_staff=True)
    """
    def make_user(**kwargs):
        kwargs.setdefault('password', test_password)
        kwargs.setdefault('username', f'testuser_{User.objects.count()}')
        kwargs.setdefault('email', f'test{User.objects.count()}@example.com')
        kwargs.setdefault('first_name', 'Test')
        kwargs.setdefault('last_name', 'User')
        
        password = kwargs.pop('password')
        user = User.objects.create(**kwargs)
        user.set_password(password)
        user.save()
        return user
    
    return make_user


@pytest.fixture
def user(create_user):
    """
    Standard test user.
    
    Usage:
        def test_something(user):
            assert user.is_active
    """
    return create_user()


@pytest.fixture
def admin_user(create_user):
    """
    Admin/superuser for tests requiring elevated permissions.
    
    Usage:
        def test_something(admin_user):
            assert admin_user.is_superuser
    """
    return create_user(
        username='admin',
        email='admin@example.com',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def authenticated_client(api_client, user, test_password):
    """
    API client with authenticated user (includes JWT token).
    
    Usage:
        def test_something(authenticated_client):
            response = authenticated_client.get('/api/auth/profile/')
    """
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def tokens(user):
    """
    JWT tokens (access and refresh) for a test user.
    
    Usage:
        def test_something(tokens):
            access = tokens['access']
            refresh = tokens['refresh']
    """
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': user
    }


@pytest.fixture
def api_client_with_token(api_client, tokens):
    """
    API client with JWT token in Authorization header.
    
    Usage:
        def test_something(api_client_with_token):
            response = api_client_with_token.get('/api/auth/profile/')
    """
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return api_client


@pytest.fixture
def multiple_users(create_user):
    """
    Create multiple test users.
    
    Usage:
        def test_something(multiple_users):
            users = multiple_users(5)  # Creates 5 users
    """
    def make_users(count=3):
        return [create_user() for _ in range(count)]
    
    return make_users


# Pytest markers for organizing tests
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for workflows"
    )
    config.addinivalue_line(
        "markers", "api: API endpoint tests"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take a long time to run"
    )
    config.addinivalue_line(
        "markers", "auth: Authentication and authorization tests"
    )


# Database optimization for faster tests
@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Optimize database setup for tests.
    This runs once per test session.
    """
    with django_db_blocker.unblock():
        # Add any database setup here if needed
        pass
