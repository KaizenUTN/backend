"""
config.spectacular_hooks
========================
Preprocessing hooks para drf-spectacular.

Referenciados desde SPECTACULAR_SETTINGS['PREPROCESSING_HOOKS'] en base.py.
"""

from __future__ import annotations


def exclude_playground(endpoints: list, **kwargs) -> list:
    """
    Excluye todos los endpoints bajo /api/playground/ del schema OpenAPI generado.
    Los endpoints siguen funcionando en runtime; solo dejan de aparecer en Swagger.
    """
    return [
        (path, path_regex, method, callback)
        for path, path_regex, method, callback in endpoints
        if not path.startswith("/api/playground/")
    ]


_EXCLUDED_PATHS = {
    "/api/auth/refresh/",           # TokenRefreshView — genera el grupo "auth" en Swagger
    "/api/authorization/me/permissions/",  # MyPermissionsView — genera "RBAC — Introspección"
}


def exclude_internal_endpoints(endpoints: list, **kwargs) -> list:
    """
    Excluye endpoints internos/técnicos que no deben exponerse en la documentación pública.
    """
    return [
        (path, path_regex, method, callback)
        for path, path_regex, method, callback in endpoints
        if path not in _EXCLUDED_PATHS
    ]
