"""
Static user data fixtures for testing.

Provides predefined user data dictionaries for consistent testing.
"""

# ---------------------------------------------------------------------------
# Shared constants (avoid duplicated literals)
# ---------------------------------------------------------------------------

TEST_EMAIL: str = 'test@example.com'
TEST_PASSWORD: str = 'TestPassword123!'  # NOSONAR
COMMON_PASSWORD: str = 'Password123!'  # NOSONAR


VALID_USER_DATA = {
    'username': 'testuser',
    'email': TEST_EMAIL,
    'first_name': 'Test',
    'last_name': 'User',
    'password': TEST_PASSWORD  # NOSONAR
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
    'email': 'newuser@example.com',
    'first_name': 'New',
    'last_name': 'User',
    'password': 'SecurePassword123!',
    'password_confirm': 'SecurePassword123!'
}


VALID_LOGIN_DATA = {
    'email': TEST_EMAIL,
    'password': TEST_PASSWORD  # NOSONAR
}


VALID_PASSWORD_CHANGE_DATA = {
    'old_password': TEST_PASSWORD,  # NOSONAR
    'new_password': 'NewPassword456!',  # NOSONAR
    'new_password_confirm': 'NewPassword456!'  # NOSONAR
}


VALID_PROFILE_UPDATE_DATA = {
    'first_name': 'Updated',
    'last_name': 'Name'
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
        'email': TEST_EMAIL,
        'password': TEST_PASSWORD,  # NOSONAR
        'password_confirm': TEST_PASSWORD  # NOSONAR
        # Missing first_name, last_name
    },
    # Password mismatch
    {
        'username': 'testuser',
        'email': TEST_EMAIL,
        'first_name': 'Test',
        'last_name': 'User',
        'password': TEST_PASSWORD,  # NOSONAR
        'password_confirm': 'DifferentPassword456!'  # NOSONAR
    },
    # Invalid email
    {
        'username': 'testuser',
        'email': 'notanemail',
        'first_name': 'Test',
        'last_name': 'User',
        'password': TEST_PASSWORD,  # NOSONAR
        'password_confirm': TEST_PASSWORD  # NOSONAR
    },
]


# Multiple users data for testing

MULTIPLE_USERS_DATA = [
    {
        'username': 'user1',
        'email': 'user1@example.com',
        'first_name': 'User',
        'last_name': 'One',
        'password': COMMON_PASSWORD  # NOSONAR
    },
    {
        'username': 'user2',
        'email': 'user2@example.com',
        'first_name': 'User',
        'last_name': 'Two',
        'password': COMMON_PASSWORD  # NOSONAR
    },
    {
        'username': 'user3',
        'email': 'user3@example.com',
        'first_name': 'User',
        'last_name': 'Three',
        'password': COMMON_PASSWORD  # NOSONAR
    },
]
