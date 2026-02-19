from django.db import models


class Permission(models.Model):
    """
    Permiso atómico del sistema.

    El campo `code` identifica el permiso de forma única y debe seguir
    la convención <dominio>.<acción>, por ejemplo:
        "conciliacion.run"
        "conciliacion.view"
        "usuarios.create"
        "reportes.export"

    Esto permite agrupar permisos por dominio funcional y escalar
    sin colisiones de nombres.
    """

    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Código",
        help_text='Identificador único. Convención: "<dominio>.<acción>" — ej: "conciliacion.run".',
    )
    description = models.CharField(
        max_length=255,
        verbose_name="Descripción",
        help_text="Descripción legible del permiso para uso en backoffice.",
    )

    class Meta:
        app_label = "authorization"
        verbose_name = "Permiso"
        verbose_name_plural = "Permisos"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.description}"


class Role(models.Model):
    """
    Rol del sistema.  Agrupa un conjunto de permisos que se asignan
    de manera conjunta a un usuario.

    Diseño deliberado:
    - Un usuario tiene exactamente UN rol (ForeignKey en User).
    - Un rol puede tener N permisos (ManyToMany).
    - Cambiar el rol de un usuario surte efecto inmediato en la próxima
      verificación de permisos, sin necesidad de renovar tokens.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre",
        help_text='Nombre único del rol. Ej: "Analista", "Supervisor", "Admin".',
    )
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="roles",
        verbose_name="Permisos",
        help_text="Conjunto de permisos que otorga este rol.",
    )

    class Meta:
        app_label = "authorization"
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
