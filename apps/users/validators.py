"""
Validadores de contraseña personalizados.

Complementan los 4 validadores estándar de Django configurados
en AUTH_PASSWORD_VALIDATORS con requisitos de complejidad.
"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordComplexityValidator:
    """
    Valida que la contraseña cumpla requisitos de complejidad mínima:

    - Al menos una letra mayúscula (A-Z)
    - Al menos una letra minúscula (a-z)
    - Al menos un número (0-9)
    - Al menos un carácter especial (@$!%*?&#^_\-.)
    """

    SPECIAL_CHARS = r"@$!%*?&#^_\-."

    def validate(self, password: str, user=None) -> None:
        errors = []

        if not re.search(r"[A-Z]", password):
            errors.append(
                ValidationError(
                    _("La contraseña debe contener al menos una letra mayúscula."),
                    code="password_no_upper",
                )
            )

        if not re.search(r"[a-z]", password):
            errors.append(
                ValidationError(
                    _("La contraseña debe contener al menos una letra minúscula."),
                    code="password_no_lower",
                )
            )

        if not re.search(r"\d", password):
            errors.append(
                ValidationError(
                    _("La contraseña debe contener al menos un número."),
                    code="password_no_digit",
                )
            )

        if not re.search(rf"[{self.SPECIAL_CHARS}]", password):
            errors.append(
                ValidationError(
                    _(
                        "La contraseña debe contener al menos un carácter especial "
                        f"({self.SPECIAL_CHARS.replace(chr(92), '')})."
                    ),
                    code="password_no_special",
                )
            )

        if errors:
            raise ValidationError(errors)

    def get_help_text(self) -> str:
        return _(
            "Tu contraseña debe contener al menos: "
            "una mayúscula, una minúscula, un número "
            f"y un carácter especial ({self.SPECIAL_CHARS.replace(chr(92), '')})."
        )
