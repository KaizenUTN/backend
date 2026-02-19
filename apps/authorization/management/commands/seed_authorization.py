"""
Management command: seed_authorization
=======================================
Carga la estructura base de roles y permisos del sistema RBAC.

Uso:
    python manage.py seed_authorization
    python manage.py seed_authorization --clear   # Borra todo y recrea

Diseño:
  - Idempotente: ejecutarlo múltiples veces no crea duplicados.
  - --clear: útil para entornos de staging/CI donde se necesita
    un estado conocido. NUNCA usar en producción sin respaldo previo.
  - Los permisos y roles se definen en el propio comando para tener
    la lógica de seed versionada en el repositorio.
"""

from django.core.management.base import BaseCommand, CommandParser

from apps.authorization.models import Permission, Role


# ---------------------------------------------------------------------------
# Definición de datos iniciales
# ---------------------------------------------------------------------------

PERMISSIONS: list[dict] = [
    # Conciliación
    {"code": "conciliacion.run",    "description": "Ejecutar el proceso de conciliación automática"},
    {"code": "conciliacion.view",   "description": "Ver resultados y estado de conciliaciones"},
    {"code": "conciliacion.export", "description": "Exportar reportes de conciliación"},
    # Usuarios
    {"code": "usuarios.view",       "description": "Ver listado de usuarios del sistema"},
    {"code": "usuarios.create",     "description": "Crear nuevos usuarios"},
    {"code": "usuarios.edit",       "description": "Editar datos de usuarios existentes"},
    {"code": "usuarios.delete",     "description": "Eliminar usuarios del sistema"},
    # Reportes
    {"code": "reportes.view",       "description": "Ver reportes del sistema"},
    {"code": "reportes.export",     "description": "Exportar reportes en distintos formatos"},
    # Dashboard
    {"code": "dashboard.view",      "description": "Ver el panel de métricas principal"},
    # Admin
    {"code": "admin.full",          "description": "Acceso completo al panel de administración"},
]

ROLES: list[dict] = [
    {
        "name": "Solo Lectura",
        "permissions": ["conciliacion.view", "reportes.view", "dashboard.view"],
    },
    {
        "name": "Analista",
        "permissions": ["conciliacion.run", "conciliacion.view", "reportes.view", "dashboard.view"],
    },
    {
        "name": "Supervisor",
        "permissions": [
            "conciliacion.run",
            "conciliacion.view",
            "conciliacion.export",
            "reportes.view",
            "reportes.export",
            "dashboard.view",
        ],
    },
    {
        "name": "Administrador",
        "permissions": [p["code"] for p in PERMISSIONS],  # todos los permisos
    },
]


class Command(BaseCommand):
    help = "Carga la estructura base de roles y permisos del sistema RBAC."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Elimina todos los roles y permisos existentes antes de crear los nuevos.",
        )

    def handle(self, *args, **options) -> None:
        if options["clear"]:
            Role.objects.all().delete()
            Permission.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Roles y permisos eliminados."))

        # ── 1. Crear / actualizar permisos ──────────────────────────────────
        self.stdout.write("\nSincronizando permisos...")
        created_perms = 0
        for pdata in PERMISSIONS:
            _, created = Permission.objects.update_or_create(
                code=pdata["code"],
                defaults={"description": pdata["description"]},
            )
            if created:
                created_perms += 1
                self.stdout.write(f"  [+] {pdata['code']}")
            else:
                self.stdout.write(f"  [=] {pdata['code']} (ya existía)")

        self.stdout.write(
            self.style.SUCCESS(f"  {created_perms} permiso(s) creado(s).")
        )

        # ── 2. Crear / actualizar roles y asignar permisos ──────────────────
        self.stdout.write("\nSincronizando roles...")
        created_roles = 0
        for rdata in ROLES:
            role, created = Role.objects.get_or_create(name=rdata["name"])
            perms = Permission.objects.filter(code__in=rdata["permissions"])
            role.permissions.set(perms)

            if created:
                created_roles += 1
                self.stdout.write(
                    f"  [+] {rdata['name']} ({perms.count()} permisos)"
                )
            else:
                self.stdout.write(
                    f"  [=] {rdata['name']} — permisos actualizados ({perms.count()})"
                )

        self.stdout.write(
            self.style.SUCCESS(f"  {created_roles} rol(es) creado(s).")
        )

        self.stdout.write(self.style.SUCCESS("\n✓ seed_authorization completado.\n"))
