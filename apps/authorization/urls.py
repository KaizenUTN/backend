from django.urls import path

from .views import (
    ConciliacionRunView,
    ConciliacionDetailView,
    DashboardView,
    AdminPanelView,
    MyPermissionsView,
)

app_name = "authorization"

urlpatterns = [
    # Introspección — permisos del usuario autenticado
    path("authorization/me/permissions/", MyPermissionsView.as_view(), name="my_permissions"),

    # Ejemplo RBAC: permiso único
    path("authorization/conciliacion/run/",    ConciliacionRunView.as_view(),    name="conciliacion_run"),
    path("authorization/conciliacion/",        ConciliacionDetailView.as_view(), name="conciliacion_detail"),

    # Ejemplo RBAC: HAnyPermission (OR)
    path("authorization/dashboard/",           DashboardView.as_view(),          name="dashboard"),

    # Ejemplo RBAC: HasAllPermissions (AND)
    path("authorization/admin/panel/",         AdminPanelView.as_view(),         name="admin_panel"),
]
