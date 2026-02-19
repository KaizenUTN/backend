"""
Unit tests for User model.

Tests cover:
- User creation and validation
- Password hashing
- Model properties and methods
- Field constraints
- Database operations
"""

import pytest
import time
from django.db import IntegrityError
from apps.users.models import User
from apps.users.tests.factories.user_factory import UserFactory, create_user

pytestmark = pytest.mark.unit


class TestUserModel:
    """Tests for User model functionality."""
    
    @pytest.mark.django_db
    def test_create_user(self):
        """Test basic user creation."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User'
        )
        
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.first_name == 'Test'
        assert user.last_name == 'User'
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
    
    @pytest.mark.django_db
    def test_create_superuser(self):
        """Test superuser creation."""
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='AdminPassword123!'
        )
        
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.is_active is True
    
    @pytest.mark.django_db
    def test_user_email_unique(self):
        """Test that email must be unique."""
        User.objects.create_user(
            username='user1',
            email='test@example.com',
            password='Password123!'
        )
        
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username='user2',
                email='test@example.com',  # Duplicate email
                password='Password123!'
            )
    
    @pytest.mark.django_db
    def test_user_username_unique(self):
        """Test that username must be unique."""
        User.objects.create_user(
            username='testuser',
            email='test1@example.com',
            password='Password123!'
        )
        
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username='testuser',  # Duplicate username
                email='test2@example.com',
                password='Password123!'
            )
    
    @pytest.mark.django_db
    def test_password_is_hashed(self):
        """Test that password is properly hashed."""
        password = 'TestPassword123!'
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password=password
        )
        
        # Password should not be stored in plain text
        assert user.password != password
        # Password should be hashed (any hasher)
        assert user.check_password(password) is True
        assert user.check_password('wrongpassword') is False
    
    @pytest.mark.django_db
    def test_user_full_name_property(self):
        """Test full_name property."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!',
            first_name='John',
            last_name='Doe'
        )
        
        assert user.full_name == 'John Doe'
    
    @pytest.mark.django_db
    def test_user_full_name_empty(self):
        """Test full_name falls back to email when first/last name are empty."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!'
        )
        
        # Model returns email as fallback when names are empty
        assert user.full_name == 'test@example.com'
    
    @pytest.mark.django_db
    def test_user_str_representation(self):
        """Test string representation of user."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!'
        )
        
        # Custom User model uses email as __str__
        assert str(user) == 'test@example.com'
    
    @pytest.mark.django_db
    def test_user_email_is_username_field(self):
        """Test that email is used as USERNAME_FIELD for authentication."""
        assert User.USERNAME_FIELD == 'email'
    
    @pytest.mark.django_db
    def test_user_required_fields(self):
        """Test REQUIRED_FIELDS configuration."""
        expected_fields = ['username', 'first_name', 'last_name']
        assert User.REQUIRED_FIELDS == expected_fields
    
    @pytest.mark.django_db
    def test_user_timestamps(self):
        """Test that created_at and updated_at are set."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!'
        )
        
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.created_at <= user.updated_at
    
    @pytest.mark.django_db
    def test_user_updated_at_changes(self):
        """Test that updated_at changes when user is modified."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!'
        )
        
        original_updated_at = user.updated_at
        
        # Small delay to ensure updated_at timestamp advances (SQLite resolution)
        time.sleep(0.01)
        
        # Modify user
        user.first_name = 'Updated'
        user.save()
        
        user.refresh_from_db()
        assert user.updated_at > original_updated_at
    
    @pytest.mark.django_db
    def test_inactive_user(self):
        """Test creating an inactive user."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!',
            is_active=False
        )
        
        assert user.is_active is False


class TestUserModelWithFactory:
    """Tests using factory_boy for cleaner test data."""
    
    @pytest.mark.django_db
    def test_user_factory_creates_valid_user(self):
        """Test that UserFactory creates a valid user."""
        user = UserFactory()
        
        assert user.pk is not None
        assert user.email
        assert user.username
        assert user.is_active is True
    
    @pytest.mark.django_db
    def test_user_factory_with_custom_data(self):
        """Test UserFactory with custom data."""
        user = UserFactory(
            email='custom@example.com',
            first_name='Custom',
            last_name='Name'
        )
        
        assert user.email == 'custom@example.com'
        assert user.first_name == 'Custom'
        assert user.last_name == 'Name'
    
    @pytest.mark.django_db
    def test_create_multiple_users_with_factory(self):
        """Test creating multiple users with factory."""
        users = UserFactory.create_batch(5)
        
        assert len(users) == 5
        # All should have unique emails
        emails = [user.email for user in users]
        assert len(emails) == len(set(emails))
    
    @pytest.mark.django_db
    def test_user_factory_password_hashing(self):
        """Test that factory properly hashes passwords."""
        user = UserFactory()
        
        # Password should be hashed (not stored as plaintext)
        assert user.password != 'TestPassword123!'
        # Default password should work via check_password
        assert user.check_password('TestPassword123!') is True
