from django.urls import path

from .views import AuditLogDetailView, AuditLogListView

app_name = "audit"

urlpatterns = [
    # ------------------------------------------------------------------
    # Auditoría — solo lectura, solo Administrador
    # ------------------------------------------------------------------
    path("audit/logs/",          AuditLogListView.as_view(),   name="audit-log-list"),
    path("audit/logs/<int:log_id>/", AuditLogDetailView.as_view(), name="audit-log-detail"),
]
