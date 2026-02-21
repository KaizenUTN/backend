"""
Fixtures compartidas para los tests del módulo audit.
"""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """APIClient no autenticado — para verificar que los endpoints requieren auth."""
    return APIClient()
