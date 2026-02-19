"""
User model factory for testing.

This module provides factory classes for creating User instances
with realistic fake data using factory_boy and Faker.
"""

import factory
from factory.django import DjangoModelFactory
from faker import Faker
from django.contrib.auth import get_user_model

fake = Faker()
User = get_user_model()


class UserFactory(DjangoModelFactory):
    """
    Factory for creating User instances with fake data.
    
    Usage:
        # Create a user with defaults
        user = UserFactory()
        
        # Create a user with custom data
        user = UserFactory(email='custom@example.com')
        
        # Create multiple users
        users = UserFactory.create_batch(5)
        
        # Build a user without saving to database
        user = UserFactory.build()
        
        # Create a superuser
        admin = UserFactory(is_staff=True, is_superuser=True)
    """
    
    class Meta:
        model = User
        django_get_or_create = ('email',)  # Avoid duplicates
    
    # Basic fields
    username = factory.Sequence(lambda n: f'user_{n}_{fake.user_name()}')
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    first_name = factory.LazyAttribute(lambda _: fake.first_name())
    last_name = factory.LazyAttribute(lambda _: fake.last_name())
    
    # Password (use post_generation to properly hash it)
    password = factory.PostGenerationMethodCall('set_password', 'TestPassword123!')
    
    # Account status
    is_active = True
    is_staff = False
    is_superuser = False
    
    # Timestamps are handled by Django auto_now_add and auto_now


class AdminUserFactory(UserFactory):
    """
    Factory for creating admin/staff users.
    
    Usage:
        admin = AdminUserFactory()
        assert admin.is_staff and admin.is_superuser
    """
    
    username = factory.Sequence(lambda n: f'admin_{n}')
    email = factory.Sequence(lambda n: f'admin{n}@example.com')
    is_staff = True
    is_superuser = True


class InactiveUserFactory(UserFactory):
    """
    Factory for creating inactive users.
    
    Usage:
        inactive = InactiveUserFactory()
        assert not inactive.is_active
    """
    
    is_active = False


# Traits for flexible user creation
class UserWithTraitsFactory(UserFactory):
    """
    User factory with traits for common scenarios.
    
    Usage:
        # Create an admin
        admin = UserWithTraitsFactory(admin=True)
        
        # Create an inactive user
        inactive = UserWithTraitsFactory(inactive=True)
        
        # Create a user with custom name
        user = UserWithTraitsFactory(
            first_name='John',
            last_name='Doe'
        )
    """
    
    class Params:
        # Traits
        admin = factory.Trait(
            is_staff=True,
            is_superuser=True,
            username=factory.Sequence(lambda n: f'admin_{n}')
        )
        
        inactive = factory.Trait(
            is_active=False
        )
        
        staff = factory.Trait(
            is_staff=True,
            username=factory.Sequence(lambda n: f'staff_{n}')
        )


# Convenience functions
def create_user(**kwargs):
    """
    Create a user with custom attributes.
    
    Args:
        **kwargs: User attributes to override defaults
    
    Returns:
        User: Created user instance
    
    Usage:
        user = create_user(email='test@example.com')
        admin = create_user(is_superuser=True)
    """
    return UserFactory(**kwargs)


def create_users(count=3, **kwargs):
    """
    Create multiple users.
    
    Args:
        count: Number of users to create
        **kwargs: User attributes to override defaults
    
    Returns:
        list: List of created user instances
    
    Usage:
        users = create_users(5)
        admins = create_users(3, is_superuser=True)
    """
    return UserFactory.create_batch(count, **kwargs)


def create_admin(**kwargs):
    """
    Create an admin user.
    
    Args:
        **kwargs: User attributes to override defaults
    
    Returns:
        User: Created admin user instance
    
    Usage:
        admin = create_admin()
        admin = create_admin(email='admin@company.com')
    """
    return AdminUserFactory(**kwargs)
