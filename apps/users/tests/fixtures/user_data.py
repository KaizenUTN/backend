"""
Static user data fixtures for testing.

Provides predefined user data dictionaries for consistent testing.
"""


VALID_USER_DATA = {
    'username': 'testuser',
    'email': 'test@example.com',
    'first_name': 'Test',
    'last_name': 'User',
    'password': 'TestPassword123!'
}


VALID_ADMIN_DATA = {
    'username': 'adminuser',
    'email': 'admin@example.com',
    'first_name': 'Admin',
    'last_name': 'User',
    'password': 'AdminPassword123!',
    'is_staff': True,
    'is_superuser': True
}


VALID_REGISTRATION_DATA = {
    'username': 'newuser',
    'email': 'newuser@example.com',
    'first_name': 'New',
    'last_name': 'User',
    'password': 'SecurePassword123!',
    'password_confirm': 'SecurePassword123!'
}


VALID_LOGIN_DATA = {
    'email': 'test@example.com',
    'password': 'TestPassword123!'
}


VALID_PASSWORD_CHANGE_DATA = {
    'old_password': 'TestPassword123!',
    'new_password': 'NewPassword456!',
    'new_password_confirm': 'NewPassword456!'
}


VALID_PROFILE_UPDATE_DATA = {
    'first_name': 'Updated',
    'last_name': 'Name',
    'username': 'updateduser'
}


# Invalid data for testing validation

INVALID_EMAIL_DATA = [
    'notanemail',
    'missing@domain',
    '@nodomain.com',
    'spaces in@email.com',
    'double@@domain.com'
]


# Passwords that Django's built-in validators actually reject:
# MinimumLengthValidator rejects < 8 chars
# NumericPasswordValidator rejects entirely numeric strings
# Note: Django does NOT require mixed case by default
WEAK_PASSWORDS = [
    'short',    # Too short (< 8 chars)
    'abc',      # Too short
    '12345678', # Entirely numeric
    '00000000', # Entirely numeric
]


INVALID_REGISTRATION_DATA = [
    # Missing fields
    {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'TestPassword123!',
        'password_confirm': 'TestPassword123!'
        # Missing first_name, last_name
    },
    # Password mismatch
    {
        'username': 'testuser',
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'password': 'TestPassword123!',
        'password_confirm': 'DifferentPassword456!'
    },
    # Invalid email
    {
        'username': 'testuser',
        'email': 'notanemail',
        'first_name': 'Test',
        'last_name': 'User',
        'password': 'TestPassword123!',
        'password_confirm': 'TestPassword123!'
    },
]


# Multiple users data for testing

MULTIPLE_USERS_DATA = [
    {
        'username': 'user1',
        'email': 'user1@example.com',
        'first_name': 'User',
        'last_name': 'One',
        'password': 'Password123!'
    },
    {
        'username': 'user2',
        'email': 'user2@example.com',
        'first_name': 'User',
        'last_name': 'Two',
        'password': 'Password123!'
    },
    {
        'username': 'user3',
        'email': 'user3@example.com',
        'first_name': 'User',
        'last_name': 'Three',
        'password': 'Password123!'
    },
]
