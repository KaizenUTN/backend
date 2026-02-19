# Testing Guide - Users App

## Structure

Los tests están organizados dentro de cada aplicación siguiendo las mejores prácticas de Django:

```
apps/
└── users/
    └── tests/
        ├── __init__.py
        ├── conftest.py              # Fixtures específicas de users
        ├── README.md                # Esta documentación
        ├── factories/               # Factories para test data
        │   ├── __init__.py
        │   └── user_factory.py
        ├── fixtures/                # Datos estáticos
        │   ├── __init__.py
        │   └── user_data.py
        ├── utils/                   # Utilidades de testing
        │   ├── __init__.py
        │   ├── api_client.py
        │   └── assertions.py
        ├── unit/                    # Tests unitarios
        │   ├── __init__.py
        │   ├── test_models.py
        │   ├── test_serializers.py
        │   └── test_authentication.py
        ├── api/                     # Tests de API
        │   ├── __init__.py
        │   ├── test_register.py
        │   ├── test_login.py
        │   ├── test_logout.py
        │   ├── test_profile.py
        │   └── test_change_password.py
        ├── integration/             # Tests de integración
        │   ├── __init__.py
        │   └── test_auth_flow.py
        └── examples/                # Ejemplos de patrones
            ├── __init__.py
            └── test_patterns_example.py
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run only users app tests
```bash
pytest apps/users/tests/
```

### Run specific test types in users app
```bash
# Unit tests only
pytest apps/users/tests/unit/ -m unit

# API tests only
pytest apps/users/tests/api/ -m api

# Integration tests only
pytest apps/users/tests/integration/ -m integration

# Authentication tests only
pytest apps/users/tests/ -m auth
```

### Run tests in specific files/directories
```bash
# Run all unit tests
pytest apps/users/tests/unit/

# Run specific test file
pytest apps/users/tests/api/test_register.py

# Run specific test class
pytest apps/users/tests/unit/test_models.py::TestUserModel

# Run specific test method
pytest apps/users/tests/unit/test_models.py::TestUserModel::test_create_user
```

### Coverage Reports
```bash
# Run tests with coverage for users app
pytest apps/users/tests/ --cov=apps.users

# Generate HTML coverage report
pytest apps/users/tests/ --cov=apps.users --cov-report=html

# Open coverage report (Windows)
start htmlcov/index.html
```

### Useful Options
```bash
# Verbose output
pytest apps/users/tests/ -v

# Stop on first failure
pytest apps/users/tests/ -x

# Show local variables in tracebacks
pytest apps/users/tests/ -l

# Run last failed tests
pytest apps/users/tests/ --lf

# Run only changed tests
pytest apps/users/tests/ --ff

# Run tests in parallel (requires pytest-xdist)
pytest apps/users/tests/ -n auto

# Disable warnings
pytest apps/users/tests/ --disable-warnings
```

## Test Structure

Esta app de users contiene tests para:
- **Modelos**: User model (18 tests)
- **Serializers**: UserSerializer, RegisterSerializer, LoginSerializer, ChangePasswordSerializer (30+ tests)
- **Authentication**: CustomJWTAuthentication backend (5 tests)
- **API Endpoints**: Register, Login, Logout, Profile, Change Password (43 tests)
- **Integration**: Complete authentication flows (7 tests)

Total: **103+ tests**

```
tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # Global fixtures
├── factories/                  # Factory classes for test data
│   ├── __init__.py
│   └── user_factory.py         # User model factories
├── fixtures/                   # Static test data
│   ├── __init__.py
│   └── user_data.py            # User data fixtures
├── utils/                      # Test utilities
│   ├── __init__.py
│   ├── api_client.py           # Custom API client helpers
│   └── assertions.py           # Custom assertion helpers
├── unit/                       # Unit tests
│   ├── __init__.py
│   ├── test_models.py          # Model tests
│   ├── test_serializers.py     # Serializer tests
│   └── test_authentication.py  # Authentication backend tests
├── api/                        # API endpoint tests
│   ├── __init__.py
│   ├── test_register.py        # Registration endpoint
│   ├── test_login.py           # Login endpoint
│   ├── test_logout.py          # Logout endpoint
│   ├── test_profile.py         # Profile endpoint
│   └── test_change_password.py # Password change endpoint
└── integration/                # Integration tests
    ├── __init__.py
    └── test_auth_flow.py       # Complete authentication flows
```

## Writing Tests

### Using Fixtures
```python
def test_user_creation(user):
    """Test using the user fixture from conftest.py"""
    assert user.is_active
    assert user.email
apps.users.tests.factories.user_factory import UserFactory

def test_with_factory():
    """Test using UserFactory to create test data"""
    user = UserFactory(first_name='John', last_name='Doe')
    assert user.full_name == 'John Doe'
    
    # Create multiple users
    users = UserFactory.create_batch(5)
    assert len(users) == 5
```

### Using Custom API Client
```python
from apps.users.tests.utils.api_client import APIClient

def test_with_custom_client():
    """Test using custom API client helpers"""
    client = APIClient()
    
    # Register and login in one call
    response = client.register_user(
        'testuser',
        'test@example.com',
        'Password123!'
    )
    
    # Client is now authenticated
    profile = client.get('/api/auth/profile/')
    assert profile.status_code == 200
```

### Using Custom Assertions
```python
from apps.users.
    
    # Client is now authenticated
    profile = client.get('/api/auth/profile/')
    assert profile.status_code == 200
```

### Using Custom Assertions
```python
from tests.utils.assertions import (
    assert_success_response,
    assert_authenticated_response,
    assert_validation_error
)

def test_with_assertions(api_client, user):
    """Test using custom assertion helpers"""
    response = api_client.post('/api/auth/login/', {
        'email': user.email,
        'password': 'TestPassword123!'
    })
    
    # Clean, readable assertions
    assert_authenticated_response(response)
```

## Test Markers

Tests are marked with custom markers to enable selective execution:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.focus` - Tests to focus on during development

## Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
   ```python
   def test_user_cannot_register_with_duplicate_email()
   ```

2. **AAA Pattern**: Structure tests with Arrange-Act-Assert
   ```python
   def test_example():
       # Arrange: Set up test data
       user = UserFactory()
       
       # Act: Perform the action
       result = user.full_name
       
       # Assert: Verify the result
       assert result == f"{user.first_name} {user.last_name}"
   ```

3. **Use Fixtures**: Leverage conftest.py fixtures for common setup
4. **Use Factories**: Use factory_boy for flexible test data creation
5. **Isolate Tests**: Each test should be independent
6. **Test One Thing**: Each test should verify one specific behavior
7. **Use Markers**: Mark tests appropriately for selective execution

## Code Coverage Goals

- **Overall Coverage**: Target 90%+ coverage
- **Critical Paths**: 100% coverage for authentication and security
- **Models**: 100% coverage for custom methods
- **Serializers**: 100% coverage for custom validation
- **Views**: 90%+ coverage for business logic

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

```bash
# CI command
pytest --cov --cov-report=xml --junit-xml=test-results.xml
```

## Troubleshooting

### Database Issues
```bash
# Run with migrations if needed
pytest --no-migrations=False

# Create test database
python manage.py migrate --settings=config.settings.test
```

### Import Errors
```bash
# Ensure DJANGO_SETTINGS_MODULE is set
export DJANGO_SETTINGS_MODULE=config.settings.test

# Or use pytest.ini configuration (already configured)
```

### Slow Tests
```bash
# Identify slow tests
pytest --durations=10

# Skip slow tests
pytest -m "not slow"
```
