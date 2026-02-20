"""
Custom assertions for testing.

Provides domain-specific assertion helpers for cleaner tests.
"""

from rest_framework import status


def assert_success_response(response):
    """
    Assert that response is successful (2xx status code).
    
    Args:
        response: Response object
    
    Usage:
        response = client.get('/api/endpoint/')
        assert_success_response(response)
    """
    assert 200 <= response.status_code < 300, (
        f"Expected success response, got {response.status_code}: {response.data}"
    )


def assert_error_response(response, expected_status=None):
    """
    Assert that response is an error (4xx or 5xx status code).
    
    Args:
        response: Response object
        expected_status: Specific expected status code (optional)
    
    Usage:
        response = client.post('/api/endpoint/', {})
        assert_error_response(response, status.HTTP_400_BAD_REQUEST)
    """
    assert response.status_code >= 400, (
        f"Expected error response, got {response.status_code}"
    )
    
    if expected_status:
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}: {response.data}"
        )


def assert_validation_error(response, field_name):
    """
    Assert that response contains validation error for specific field.
    
    Args:
        response: Response object
        field_name: Name of field with error
    
    Usage:
        response = client.post('/api/auth/register/', invalid_data)
        assert_validation_error(response, 'email')
    """
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"Expected 400, got {response.status_code}"
    )
    assert field_name in response.data, (
        f"Expected validation error for '{field_name}', got: {response.data}"
    )


def assert_authenticated_response(response):
    """
    Assert that response contains authentication tokens and user data.
    
    Args:
        response: Response object
    
    Usage:
        response = client.post('/api/auth/login/', credentials)
        assert_authenticated_response(response)
    """
    assert_success_response(response)
    assert 'access' in response.data, "Response should contain 'access' token"
    assert 'refresh' in response.data, "Response should contain 'refresh' token"
    assert 'user' in response.data, "Response should contain 'user' data"


def assert_user_data(data, expected_email=None):
    """
    Assert that user data contains expected fields and values.
    
    Args:
        data: User data dictionary
        expected_email: Expected email (optional)
    
    Usage:
        assert_user_data(response.data['user'], expected_email='test@example.com')
    """
    required_fields = ['id', 'email', 'first_name', 'last_name']
    
    for field in required_fields:
        assert field in data, f"User data should contain '{field}'"
    
    assert 'password' not in data, "User data should not contain password"
    
    if expected_email:
        assert data['email'] == expected_email, (
            f"Expected email '{expected_email}', got '{data['email']}'"
        )


def assert_unauthorized(response):
    """
    Assert that response is 401 Unauthorized.
    
    Args:
        response: Response object
    
    Usage:
        response = client.get('/api/auth/profile/')  # Without auth
        assert_unauthorized(response)
    """
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
        f"Expected 401 Unauthorized, got {response.status_code}"
    )


def assert_forbidden(response):
    """
    Assert that response is 403 Forbidden.
    
    Args:
        response: Response object
    
    Usage:
        response = client.delete('/api/admin/users/')  # Without permission
        assert_forbidden(response)
    """
    assert response.status_code == status.HTTP_403_FORBIDDEN, (
        f"Expected 403 Forbidden, got {response.status_code}"
    )


def assert_not_found(response):
    """
    Assert that response is 404 Not Found.
    
    Args:
        response: Response object
    
    Usage:
        response = client.get('/api/users/99999/')
        assert_not_found(response)
    """
    assert response.status_code == status.HTTP_404_NOT_FOUND, (
        f"Expected 404 Not Found, got {response.status_code}"
    )


def assert_contains_keys(data, *keys):
    """
    Assert that dictionary contains expected keys.
    
    Args:
        data: Dictionary to check
        *keys: Expected keys
    
    Usage:
        assert_contains_keys(response.data, 'access', 'refresh', 'user')
    """
    for key in keys:
        assert key in data, f"Expected key '{key}' in data"


def assert_does_not_contain_keys(data, *keys):
    """
    Assert that dictionary does not contain specified keys.
    
    Args:
        data: Dictionary to check
        *keys: Keys that should not be present
    
    Usage:
        assert_does_not_contain_keys(user_data, 'password', 'password_confirm')
    """
    for key in keys:
        assert key not in data, f"Did not expect key '{key}' in data"
