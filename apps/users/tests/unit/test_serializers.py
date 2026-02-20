"""
Unit tests for serializers.

Tests cover:
- Serializer validation
- Field requirements
- Custom validation logic
- Serialization and deserialization
- Error messages
"""

import pytest
from django.contrib.auth import get_user_model
from apps.users.serializers import (
    UserSerializer,
    LoginSerializer,
    RegisterSerializer,
    ChangePasswordSerializer
)
from apps.users.tests.factories.user_factory import UserFactory

User = get_user_model()

pytestmark = pytest.mark.unit


class TestUserSerializer:
    """Tests for UserSerializer."""
    
    @pytest.mark.django_db
    def test_serialize_user(self):
        """Test serializing a user instance."""
        user = UserFactory(
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        serializer = UserSerializer(user)
        data = serializer.data
        
        assert data['id'] == user.id
        assert data['email'] == 'test@example.com'
        assert data['first_name'] == 'Test'
        assert data['last_name'] == 'User'
        assert data['full_name'] == 'Test User'
        assert data['is_active'] is True
        assert 'password' not in data  # Password should never be serialized
    
    @pytest.mark.django_db
    def test_user_serializer_read_only_fields(self):
        """Test that certain fields are read-only."""
        user = UserFactory()
        data = {
            'id': 999,  # Should be ignored
            'created_at': '2020-01-01T00:00:00Z',  # Should be ignored
            'is_active': False,  # Should be ignored
            'first_name': 'Updated'
        }
        
        serializer = UserSerializer(user, data=data, partial=True)
        assert serializer.is_valid()
        serializer.save()
        
        user.refresh_from_db()
        assert user.id != 999
        assert user.is_active is True  # Should not change
        assert user.first_name == 'Updated'


class TestLoginSerializer:
    """Tests for LoginSerializer."""
    
    @pytest.mark.django_db
    def test_valid_login(self):
        """Test login with valid credentials."""
        user = UserFactory(email='test@example.com')
        
        data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        }
        
        serializer = LoginSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['user'] == user
    
    @pytest.mark.django_db
    def test_login_with_wrong_password(self):
        """Test login with incorrect password."""
        UserFactory(email='test@example.com')
        
        data = {
            'email': 'test@example.com',
            'password': 'WrongPassword123!'
        }
        
        serializer = LoginSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors
    
    @pytest.mark.django_db
    def test_login_with_nonexistent_email(self):
        """Test login with email that doesn't exist."""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'TestPassword123!'
        }
        
        serializer = LoginSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors
    
    @pytest.mark.django_db
    def test_login_with_inactive_user(self):
        """Test login with inactive user."""
        UserFactory(email='test@example.com', is_active=False)
        
        data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        }
        
        serializer = LoginSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors
    
    def test_login_missing_email(self):
        """Test login without email."""
        data = {'password': 'TestPassword123!'}
        
        serializer = LoginSerializer(data=data)
        assert not serializer.is_valid()
        assert 'email' in serializer.errors
    
    def test_login_missing_password(self):
        """Test login without password."""
        data = {'email': 'test@example.com'}
        
        serializer = LoginSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors


class TestRegisterSerializer:
    """Tests for RegisterSerializer."""
    
    @pytest.mark.django_db
    def test_valid_registration(self):
        """Test registration with valid data."""
        data = {
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
    
    @pytest.mark.django_db
    def test_create_user_from_valid_data(self):
        """Test creating user from serializer."""
        data = {
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid()
        
        user = serializer.save()
        assert user.email == 'new@example.com'
        assert user.check_password('SecurePassword123!')
        assert user.is_active is True
        # Username is auto-generated from email prefix
        assert user.username is not None
        assert 'new' in user.username

    @pytest.mark.django_db
    def test_create_user_assigns_default_role(self):
        """Test that registration assigns the 'Operador' role when it exists."""
        from apps.authorization.models import Role, Permission
        perm = Permission.objects.create(code='dashboard.view', description='Ver dashboard')
        role = Role.objects.create(name='Operador')
        role.permissions.set([perm])

        data = {
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid()
        user = serializer.save()

        assert user.role is not None
        assert user.role.name == 'Operador'

    @pytest.mark.django_db
    def test_create_user_no_role_when_role_missing(self):
        """Test that user is created without role when 'Operador' role doesn't exist."""
        data = {
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid()
        user = serializer.save()

        assert user.role is None

    @pytest.mark.django_db
    def test_registration_password_mismatch(self):
        """Test registration with mismatched passwords."""
        data = {
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'DifferentPassword123!'
        }
        
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password_confirm' in serializer.errors
    
    @pytest.mark.django_db
    def test_registration_duplicate_email(self):
        """Test registration with existing email."""
        UserFactory(email='existing@example.com')
        
        data = {
            'email': 'existing@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert 'email' in serializer.errors
    
    @pytest.mark.django_db
    def test_registration_duplicate_username(self):
        """Test that when two users share the same email prefix, username collision is resolved."""
        User.objects.create_user(
            username='newuser',
            email='other@example.com',
            password='pass',
            first_name='Other',
            last_name='User'
        )

        data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        # Collision resolved: username becomes 'newuser1'
        assert user.username == 'newuser1'
    
    @pytest.mark.django_db
    def test_registration_weak_password(self):
        """Test registration with weak password."""
        data = {
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': '123',  # Too weak
            'password_confirm': '123'
        }
        
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors
    
    @pytest.mark.django_db
    def test_registration_missing_required_fields(self):
        """Test registration with missing required fields."""
        data = {
            'email': 'new@example.com'
        }
        
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert 'first_name' in serializer.errors
        assert 'last_name' in serializer.errors
        assert 'password' in serializer.errors


class TestChangePasswordSerializer:
    """Tests for ChangePasswordSerializer."""
    
    @pytest.mark.django_db
    def test_valid_password_change(self, user):
        """Test changing password with valid data."""
        data = {
            'old_password': 'TestPassword123!',
            'new_password': 'NewSecurePassword456!',
            'new_password_confirm': 'NewSecurePassword456!'
        }
        
        # Create a mock request with user
        class MockRequest:
            pass
        
        request = MockRequest()
        request.user = user
        
        serializer = ChangePasswordSerializer(
            data=data,
            context={'request': request}
        )
        
        assert serializer.is_valid(), serializer.errors
    
    @pytest.mark.django_db
    def test_password_change_wrong_old_password(self, user):
        """Test password change with incorrect old password."""
        data = {
            'old_password': 'WrongPassword123!',
            'new_password': 'NewSecurePassword456!',
            'new_password_confirm': 'NewSecurePassword456!'
        }
        
        class MockRequest:
            pass
        
        request = MockRequest()
        request.user = user
        
        serializer = ChangePasswordSerializer(
            data=data,
            context={'request': request}
        )
        
        assert not serializer.is_valid()
        assert 'old_password' in serializer.errors
    
    @pytest.mark.django_db
    def test_password_change_mismatch(self, user):
        """Test password change with mismatched new passwords."""
        data = {
            'old_password': 'TestPassword123!',
            'new_password': 'NewSecurePassword456!',
            'new_password_confirm': 'DifferentPassword456!'
        }
        
        class MockRequest:
            pass
        
        request = MockRequest()
        request.user = user
        
        serializer = ChangePasswordSerializer(
            data=data,
            context={'request': request}
        )
        
        assert not serializer.is_valid()
        assert 'new_password_confirm' in serializer.errors
    
    @pytest.mark.django_db
    def test_password_change_weak_new_password(self, user):
        """Test password change with weak new password."""
        data = {
            'old_password': 'TestPassword123!',
            'new_password': '123',  # Too weak
            'new_password_confirm': '123'
        }
        
        class MockRequest:
            pass
        
        request = MockRequest()
        request.user = user
        
        serializer = ChangePasswordSerializer(
            data=data,
            context={'request': request}
        )
        
        assert not serializer.is_valid()
        assert 'new_password' in serializer.errors
