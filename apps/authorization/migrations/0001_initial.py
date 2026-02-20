from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Permission",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        help_text='Identificador único. Convención: "<dominio>.<acción>" — ej: "conciliacion.run".',
                        max_length=100,
                        unique=True,
                        verbose_name="Código",
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        help_text="Descripción legible del permiso para uso en backoffice.",
                        max_length=255,
                        verbose_name="Descripción",
                    ),
                ),
            ],
            options={
                "verbose_name": "Permiso",
                "verbose_name_plural": "Permisos",
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text='Nombre único del rol. Ej: "Operador", "Administrador".',
                        max_length=100,
                        unique=True,
                        verbose_name="Nombre",
                    ),
                ),
                (
                    "permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Conjunto de permisos que otorga este rol.",
                        related_name="roles",
                        to="authorization.permission",
                        verbose_name="Permisos",
                    ),
                ),
            ],
            options={
                "verbose_name": "Rol",
                "verbose_name_plural": "Roles",
                "ordering": ["name"],
            },
        ),
    ]
