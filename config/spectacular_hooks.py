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
