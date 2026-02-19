"""
Example test demonstrating all testing patterns and best practices.

This file serves as a reference for writing new tests.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.tests.factories.user_factory import UserFactory
from apps.users.tests.fixtures.user_data import (
    VALID_REGISTRATION_DATA,
    VALID_PASSWORD_CHANGE_DATA,
    WEAK_PASSWORDS
)
from apps.users.tests.utils.assertions import (
    assert_success_response,
    assert_authenticated_response,
    assert_validation_error,
    assert_user_data
)
from apps.users.tests.utils.api_client import get_tokens_for_user

User = get_user_model()


# Mark this test file
pytestmark = [pytest.mark.unit, pytest.mark.auth]


class TestExamplePatterns:
    """
    Example test class demonstrating common patterns.
    
    Patterns covered:
    - Using fixtures from conftest.py
    - Using factories for test data
    - Using static fixtures for data
    - Using custom assertions
    - Using custom API client helpers
    - Parametrized tests
    - Testing error cases
    - Testing with authentication
    """
    
    # PATTERN 1: Using fixtures from conftest.py
    def test_using_fixtures(self, user, api_client):
        """Example: Using global fixtures."""
        # The 'user' fixture provides a pre-created user
        assert user.is_active
        assert user.email
        
        # The 'api_client' fixture provides an API client
        response = api_client.get('/api/auth/profile/')
        # Note: This will fail without auth - use authenticated_client instead
    
    # PATTERN 2: Using authenticated fixtures
    def test_using_authenticated_client(self, authenticated_client):
        """Example: Using authenticated client fixture."""
        # authenticated_client has a user already authenticated
        response = authenticated_client.get('/api/auth/profile/')
        assert_success_response(response)
        assert 'email' in response.data
    
    # PATTERN 3: Using factories
    @pytest.mark.django_db
    def test_using_factories(self):
        """Example: Using factories to create test data."""
        # Create a user with specific attributes
        user = UserFactory(
            first_name='John',
            last_name='Doe',
            email='john@example.com'
        )
        
        assert user.full_name == 'John Doe'
        assert user.email == 'john@example.com'
        
        # Create multiple users
        users = UserFactory.create_batch(5)
        assert User.objects.count() == 6  # 5 batch + 1 above
        
        # Create admin user
        admin = UserFactory(is_staff=True, is_superuser=True)
        assert admin.is_superuser
    
    # PATTERN 4: Using static fixtures
    @pytest.mark.django_db
    def test_using_static_fixtures(self, api_client):
        """Example: Using static data fixtures."""
        # Use pre-defined data from fixtures
        response = api_client.post(
            '/api/auth/register/',
            VALID_REGISTRATION_DATA,
            format='json'
        )
        
        assert_success_response(response)
    
    # PATTERN 5: Using custom assertions
    @pytest.mark.django_db
    def test_using_custom_assertions(self, api_client, user):
        """Example: Using custom assertion helpers."""
        response = api_client.post(
            '/api/auth/login/',
            {
                'email': user.email,
                'password': 'TestPassword123!'
            },
            format='json'
        )
        
        # Clean, readable assertions
        assert_authenticated_response(response)
        assert_user_data(response.data['user'], expected_email=user.email)
    
    # PATTERN 6: Parametrized tests
    @pytest.mark.django_db
    @pytest.mark.parametrize('weak_password', WEAK_PASSWORDS)
    def test_parametrized_weak_passwords(self, api_client, weak_password):
        """Example: Testing multiple inputs with parametrize."""
        data = VALID_REGISTRATION_DATA.copy()
        data['password'] = weak_password
        data['password_confirm'] = weak_password
        
        response = api_client.post(
            '/api/auth/register/',
            data,
            format='json'
        )
        
        assert_validation_error(response, 'password')
    
    # PATTERN 7: Testing error cases
    @pytest.mark.django_db
    def test_error_handling(self, api_client):
        """Example: Testing error responses."""
        # Test missing required fields
        response = api_client.post(
            '/api/auth/register/',
            {'username': 'onlyusername'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data
        assert 'password' in response.data
    
    # PATTERN 8: Complex workflow test
    @pytest.mark.django_db
    def test_complete_workflow(self, api_client):
        """Example: Testing a complete user workflow."""
        # Step 1: Register
        register_data = {
            'username': 'workflowuser',
            'email': 'workflow@example.com',
            'first_name': 'Work',
            'last_name': 'Flow',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }
        
        register_response = api_client.post(
            '/api/auth/register/',
            register_data,
            format='json'
        )
        
        assert_authenticated_response(register_response)
        access_token = register_response.data['access']
        
        # Step 2: Access profile with token
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_response = api_client.get('/api/auth/profile/')
        
        assert_success_response(profile_response)
        assert profile_response.data['email'] == 'workflow@example.com'
        
        # Step 3: Update profile
        update_response = api_client.patch(
            '/api/auth/profile/',
            {'first_name': 'Updated'},
            format='json'
        )
        
        assert_success_response(update_response)
        assert update_response.data['first_name'] == 'Updated'
    
    # PATTERN 9: Using create_user fixture
    @pytest.mark.django_db
    def test_using_create_user_fixture(self, create_user, api_client):
        """Example: Using the create_user fixture factory."""
        # create_user is a fixture that returns a function
        user = create_user(
            username='customuser',
            email='custom@example.com',
            password='CustomPass123!'
        )
        
        # Login with the custom user
        response = api_client.post(
            '/api/auth/login/',
            {
                'email': 'custom@example.com',
                'password': 'CustomPass123!'
            },
            format='json'
        )
        
        assert_authenticated_response(response)
    
    # PATTERN 10: Using utility functions
    @pytest.mark.django_db
    def test_using_utility_functions(self, user, api_client):
        """Example: Using utility helper functions."""
        # Get tokens for user
        tokens = get_tokens_for_user(user)
        
        # Use the token to authenticate
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}"
        )
        
        response = api_client.get('/api/auth/profile/')
        assert_success_response(response)
    
    # PATTERN 11: Testing with multiple users
    @pytest.mark.django_db
    def test_multiple_users(self, multiple_users):
        """Example: Testing with multiple users."""
        # multiple_users is a fixture factory that creates N users
        users = multiple_users(3)
        
        assert len(users) == 3
        assert User.objects.count() == 3
        
        # Each user has unique email
        emails = [u.email for u in users]
        assert len(set(emails)) == 3  # All unique


# Example of standalone test functions (not in a class)

@pytest.mark.django_db
def test_standalone_example(user):
    """Example: Standalone test function (not in a class)."""
    assert user.is_active


@pytest.mark.django_db
@pytest.mark.slow
def test_marked_as_slow(api_client):
    """Example: Test marked as slow for selective execution."""
    # This test can be skipped with: pytest -m "not slow"
    pass


@pytest.mark.django_db
@pytest.mark.focus
def test_marked_for_focus():
    """Example: Test marked for focus during development."""
    # Run only focused tests with: pytest -m focus
    pass


# Example of testing model methods
@pytest.mark.unit
@pytest.mark.django_db
class TestModelMethods:
    """Example: Testing custom model methods."""
    
    def test_user_full_name(self):
        """Test User.full_name property."""
        user = UserFactory(first_name='John', last_name='Doe')
        assert user.full_name == 'John Doe'
    
    def test_user_string_representation(self):
        """Test User.__str__ method."""
        user = UserFactory(email='test@example.com')
        assert str(user) == 'test@example.com'


# Example of testing serializer validation
@pytest.mark.unit
@pytest.mark.django_db
class TestSerializerValidation:
    """Example: Testing serializer validation."""
    
    def test_password_mismatch_validation(self):
        """Test that password_confirm must match password."""
        from apps.users.serializers import RegisterSerializer
        
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'Password123!',
            'password_confirm': 'DifferentPassword!'
        }
        
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        # RegisterSerializer raises error on 'password_confirm' key
        assert 'password_confirm' in serializer.errors


# Example of testing API endpoints
@pytest.mark.api
@pytest.mark.django_db
class TestAPIEndpoints:
    """Example: Testing API endpoints."""
    
    def test_register_endpoint(self, api_client):
        """Test POST /api/auth/register/"""
        response = api_client.post(
            '/api/auth/register/',
            VALID_REGISTRATION_DATA,
            format='json'
        )
        
        assert_authenticated_response(response)
    
    def test_login_endpoint(self, api_client, user):
        """Test POST /api/auth/login/"""
        response = api_client.post(
            '/api/auth/login/',
            {
                'email': user.email,
                'password': 'TestPassword123!'
            },
            format='json'
        )
        
        assert_authenticated_response(response)
    
    def test_profile_endpoint_requires_auth(self, api_client):
        """Test GET /api/auth/profile/ requires authentication."""
        response = api_client.get('/api/auth/profile/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# Example of integration test
@pytest.mark.integration
@pytest.mark.django_db
class TestIntegrationWorkflow:
    """Example: Integration test for complete workflow."""
    
    def test_user_lifecycle(self, api_client):
        """Test complete user lifecycle: register -> login -> update -> logout."""
        # This is just a simple example - see test_auth_flow.py for full examples
        
        # Register
        register_response = api_client.post(
            '/api/auth/register/',
            VALID_REGISTRATION_DATA,
            format='json'
        )
        
        assert_authenticated_response(register_response)
        
        # Verify can access protected endpoint
        access_token = register_response.data['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        profile_response = api_client.get('/api/auth/profile/')
        assert_success_response(profile_response)
