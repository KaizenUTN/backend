from django.db import models
from django.contrib.auth.models import AbstractUser


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