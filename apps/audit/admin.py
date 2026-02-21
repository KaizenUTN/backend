"""
audit.admin
===========
Registro de modelos de auditoría en el panel de administración.

Los logs de auditoría son INMUTABLES: no se pueden crear, modificar
ni eliminar desde la interfaz de admin. Solo se consultan.

Para agregar nuevas clases de auditoría al admin:

    from apps.audit.admin import BaseAuditLogAdmin
    from apps.payments.models import FinancialAuditLog

    @admin.register(FinancialAuditLog)
    class FinancialAuditLogAdmin(BaseAuditLogAdmin):
        list_display = BaseAuditLogAdmin.list_display + ["amount", "currency"]
        list_filter = BaseAuditLogAdmin.list_filter + ["currency"]
        readonly_fields = BaseAuditLogAdmin.readonly_fields + ["amount", "currency"]
"""

from django.contrib import admin

from .models import AuditLog


class BaseAuditLogAdmin(admin.ModelAdmin):
    """
    Admin base para todos los modelos de auditoría.

    Read-only por diseño: los logs de auditoría son registros históricos
    inmutables. Cualquier modificación comprometería su integridad.
    Extender esta clase para adminís de subclases concretas.
    """

    list_display = [
        "timestamp",
        "action",
        "resource",
        "resource_id",
        "status",
        "user",
        "ip_address",
        "correlation_id",
    ]
    list_filter = ["status", "action", "resource"]
    search_fields = ["action", "resource", "resource_id", "user__email", "correlation_id"]
    readonly_fields = [
        "timestamp",
        "correlation_id",
        "user",
        "action",
        "resource",
        "resource_id",
        "status",
        "metadata",
        "ip_address",
        "user_agent",
    ]
    ordering = ["-timestamp"]
    date_hierarchy = "timestamp"
    show_full_result_count = False  # evita COUNT(*) costoso en tablas grandes

    def has_add_permission(self, request) -> bool:  # noqa: ANN001
        return False

    def has_change_permission(self, request, obj=None) -> bool:  # noqa: ANN001
        return False

    def has_delete_permission(self, request, obj=None) -> bool:  # noqa: ANN001
        return False


@admin.register(AuditLog)
class AuditLogAdmin(BaseAuditLogAdmin):
    """Admin para el log de auditoría general."""
