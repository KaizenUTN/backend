"""
Agregador de todas las URLs bajo el prefijo /api/.
Se incluye desde config/urls.py como un único bloque.
"""

from django.urls import include, path

urlpatterns = [
    # Autenticación e identidad
    path("", include("apps.users.urls")),
    # Control de acceso (RBAC)
    path("", include("apps.authorization.urls")),
    # Auditoría del sistema
    path("", include("apps.audit.urls")),
    # Brokerage
    path("", include("apps.brokerage.urls")),
    # Playground (endpoints de prueba)
    path("", include("apps.playground.urls")),
]
