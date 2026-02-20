"""
playground.urls
===============
URLs de prueba para demostrar autenticación y RBAC.

Prefijo base: /api/playground/

Escenarios
----------
A. Sin autenticación   → /public/  /quien-llama/
B. Solo autenticación  → /solo-autenticado/
C. HasPermission       → /permiso/conciliacion-run/  /permiso/conciliacion-export/
                          /permiso/reportes-export/  /permiso/usuarios-delete/
                          /permiso/admin/
D. HasAnyPermission    → /or/todos/          /or/solo-admin/
E. HasAllPermissions   → /and/run-export/    /and/admin-completo/
F. Introspección       → /yo/               /matriz/
"""

from django.urls import path

from .views import (
    AccessMatrixView,
    AnonymousInfoView,
    AuthenticatedOnlyView,
    PermisoAdminFull,
    PermisoAndAdminView,
    PermisoAndView,
    PermisoOrRestrictivoView,
    PermisoOrView,
    PermisoReportesExport,
    PermisoConciliacionExport,
    PermisoConciliacionRun,
    PermisoUsuariosDelete,
    PublicView,
    WhoAmIView,
)

app_name = "playground"

urlpatterns = [
    # ------------------------------------------------------------------
    # Escenario A — Sin autenticación
    # ------------------------------------------------------------------
    path("playground/public/",       PublicView.as_view(),        name="public"),
    path("playground/quien-llama/",  AnonymousInfoView.as_view(), name="quien-llama"),

    # ------------------------------------------------------------------
    # Escenario B — Solo autenticación (cualquier rol)
    # ------------------------------------------------------------------
    path("playground/solo-autenticado/", AuthenticatedOnlyView.as_view(), name="solo-autenticado"),

    # ------------------------------------------------------------------
    # Escenario C — HasPermission (permiso único)
    # ------------------------------------------------------------------
    # solo Administrador
    path("playground/permiso/conciliacion-run/",      PermisoConciliacionRun.as_view(),      name="permiso-conciliacion-run"),
    # solo Administrador
    path("playground/permiso/conciliacion-export/",   PermisoConciliacionExport.as_view(),   name="permiso-conciliacion-export"),
    # solo Administrador
    path("playground/permiso/reportes-export/",  PermisoReportesExport.as_view(), name="permiso-reportes-export"),
    # Solo Administrador  (método DELETE)
    path("playground/permiso/usuarios-delete/",  PermisoUsuariosDelete.as_view(), name="permiso-usuarios-delete"),
    # Solo Administrador
    path("playground/permiso/admin/",            PermisoAdminFull.as_view(),      name="permiso-admin"),

    # ------------------------------------------------------------------
    # Escenario D — HasAnyPermission (lógica OR)
    # ------------------------------------------------------------------
    # OR permisivo: Operador y Administrador tienen acceso
    path("playground/or/todos/",          PermisoOrView.as_view(),           name="or-todos"),
    # OR restrictivo: solo Administrador
    path("playground/or/solo-admin/", PermisoOrRestrictivoView.as_view(), name="or-solo-admin"),

    # ------------------------------------------------------------------
    # Escenario E — HasAllPermissions (lógica AND)
    # ------------------------------------------------------------------
    # AND: conciliacion.run AND reportes.export  → solo Administrador
    path("playground/and/run-export/",    PermisoAndView.as_view(),      name="and-run-export"),
    # AND: usuarios.create AND usuarios.delete  → solo Admin  (método DELETE)
    path("playground/and/admin-completo/", PermisoAndAdminView.as_view(), name="and-admin-completo"),

    # ------------------------------------------------------------------
    # Escenario F — Introspección
    # ------------------------------------------------------------------
    path("playground/yo/",     WhoAmIView.as_view(),      name="whoami"),
    path("playground/matriz/", AccessMatrixView.as_view(), name="access-matrix"),
]
