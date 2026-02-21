from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager


class UserManager(DjangoUserManager):
    """
    Manager que usa email como identificador principal.

    Sobrescribe create_user / create_superuser para que `username`
    no sea un argumento posicional obligatorio.  Si no se provee,
    se deriva automáticamente del email.
    """

    def _create_user(self, email: str | None, password: str | None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio.")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str | None = None, password: str | None = None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str | None = None, password: str | None = None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("El superusuario debe tener is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("El superusuario debe tener is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Modelo de usuario personalizado - Solo para autenticación básica.

    El campo `role` conecta este modelo de identidad con el módulo de
    autorización RBAC (apps.authorization).  La dependencia es unidireccional:
    identity → authorization; el módulo authorization NO importa nada de identity.
    """
    email = models.EmailField(unique=True, verbose_name='Email')

    # ── Autorización RBAC ─────────────────────────────────────────────────
    # String reference evita importación circular entre apps.
    # null/blank=True permite usuarios sin rol (cuentas de servicio, superusers).
    # PROTECT impide borrar un rol mientras tenga usuarios asignados.
    role = models.ForeignKey(
        'authorization.Role',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='users',
        verbose_name='Rol',
    )
    role_id: int | None  # atributo shadow generado por ForeignKey; anotado para Pylance

    # ── Versionado de tokens ────────────────────────────────────────────
    # Se incrementa al desactivar la cuenta o resetear contraseña.
    # El backend puede validar token.version == user.token_version para
    # invalidar todos los JWTs emitidos antes del cambio.
    token_version = models.PositiveIntegerField(
        default=0,
        verbose_name='Versión de token',
    )

    # Campos de auditoría básica
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    # Campo requerido para autenticación
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()  # type: ignore[assignment]

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        """Retorna el nombre completo del usuario"""
        return f"{self.first_name} {self.last_name}".strip() or self.email