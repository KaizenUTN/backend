import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Agrega el campo `role` (ForeignKey a authorization.Role) al modelo User.

    Decisiones de diseño:
    - null=True / blank=True: permite migrar sin asignar rol a usuarios
      existentes y también soportar cuentas de servicio sin rol.
    - on_delete=PROTECT: impide borrar un rol que esté asignado a uno o
      más usuarios. Obliga a reasignar usuarios antes de eliminar un rol,
      protegiendo la integridad referencial en entornos semi-críticos.
    """

    dependencies = [
        ("users", "0001_initial"),
        ("authorization", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="role",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="users",
                to="authorization.role",
                verbose_name="Rol",
            ),
        ),
    ]
