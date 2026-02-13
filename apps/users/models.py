from django.db import models
from django.contrib.auth.models import AbstractUser




class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('operador', 'Operador'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.username