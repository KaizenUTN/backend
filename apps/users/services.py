"""
users.services
==============
Lógica de negocio para administración de usuarios.

Responsabilidades:
- Alta, edición, desactivación y reset de contraseña.
- Toda mutación crítica usa transacciones atómicas.
- NO contiene lógica de autenticación (login/JWT).
- NO valida permisos (eso lo hace authorization).

Integración futura:
- TODO: Emitir evento de auditoría en cada operación (ej: AuditService.log).
- TODO: Envío de email en reset_password (ej: NotificationService.send_temp_password).
"""

from __future__ import annotations

import secrets
import string

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import User


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _unique_username(email: str) -> str:
    """Deriva un username único del email (campo interno, no expuesto en API)."""
    base = email.split('@')[0]
    candidate = base
    counter = 1
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base}{counter}"
        counter += 1
    return candidate


def _generate_temp_password(length: int = 16) -> str:
    """Contraseña temporal criptográficamente segura."""
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ---------------------------------------------------------------------------
# Operaciones públicas
# ---------------------------------------------------------------------------

@transaction.atomic
def create_user(
    *,
    email: str,
    first_name: str,
    last_name: str,
    password: str,
    role_id: int | None = None,
    is_active: bool = True,
) -> User:
    """
    Crea un usuario desde el panel de administración.

    A diferencia del registro público, permite asignar rol y estado inicial.
    Lanza ValidationError si el email ya existe o la contraseña no cumple políticas.
    """
    if User.objects.filter(email=email).exists():
        raise ValidationError({'email': 'Ya existe un usuario con este email.'})

    user = User(
        email=email,
        username=_unique_username(email),
        first_name=first_name,
        last_name=last_name,
        is_active=is_active,
    )
    if role_id is not None:
        user.role_id = role_id

    validate_password(password, user)
    user.set_password(password)
    user.save()
    return user


@transaction.atomic
def update_user(
    *,
    user: User,
    first_name: str | None = None,
    last_name: str | None = None,
    role_id: int | None = None,
) -> User:
    """
    Actualiza datos administrativos de un usuario.

    Solo modifica los campos que se pasen explícitamente (semántica PATCH).
    No permite cambiar is_active ni password desde aquí (operaciones dedicadas).
    """
    fields: list[str] = ['updated_at']

    if first_name is not None:
        user.first_name = first_name
        fields.append('first_name')
    if last_name is not None:
        user.last_name = last_name
        fields.append('last_name')
    if role_id is not None:
        user.role_id = role_id
        fields.append('role_id')

    if len(fields) > 1:
        user.save(update_fields=fields)

    return user


@transaction.atomic
def deactivate_user(*, user: User) -> User:
    """
    Desactiva un usuario (soft delete — is_active=False).

    Incrementa token_version para invalidar todos sus JWTs activos sin esperar
    a que expiren naturalmente.
    """
    user.is_active = False
    user.token_version += 1
    user.save(update_fields=['is_active', 'token_version', 'updated_at'])

    return user


@transaction.atomic
def reset_password(*, user: User) -> str:
    """
    Genera y asigna una contraseña temporal al usuario.

    Incrementa token_version para forzar re-login en todos los dispositivos.
    Retorna la contraseña en texto plano para que el caller la notifique al usuario.

    Caller es responsable de comunicar la nueva contraseña de forma segura.
    """
    temp_password = _generate_temp_password()
    user.set_password(temp_password)
    user.token_version += 1
    user.save(update_fields=['password', 'token_version', 'updated_at'])

    # TODO: NotificationService.send_temp_password(user=user, password=temp_password)
    return temp_password
