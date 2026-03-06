"""
apps/trading/tests/conftest.py
================================
Fixtures compartidas para todos los tests del módulo trading.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.trading.models import (
    Asset,
    Client,
    ClientStatus,
    FiatCurrency,
    Order,
    OrderStatus,
    Transaction,
    TransactionStatus,
    TransactionType,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="brokerage_tester",
        email="broker@test.com",
        password="TestPass123!",
        first_name="Test",
        last_name="Broker",
    )


@pytest.fixture
def auth_client(user):
    """APIClient autenticado con JWT Bearer."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ---------------------------------------------------------------------------
# Brokerage model fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client_obj(db):
    return Client.objects.create(
        cuit="20-12345678-9",
        name="Empresa Test S.A.",
        email="test@empresa.com",
        status=ClientStatus.ACTIVE,
    )


@pytest.fixture
def blocked_client(db):
    return Client.objects.create(
        cuit="30-99999999-9",
        name="Empresa Bloqueada S.R.L.",
        status=ClientStatus.BLOCKED,
    )


@pytest.fixture
def asset(db):
    return Asset.objects.create(code="BTC", name="Bitcoin", is_active=True)


@pytest.fixture
def inactive_asset(db):
    return Asset.objects.create(code="LUNA", name="Terra Luna", is_active=False)


@pytest.fixture
def fiat_currency(db):
    return FiatCurrency.objects.create(code="ARS", name="Peso Argentino", is_active=True)


@pytest.fixture
def inactive_fiat(db):
    return FiatCurrency.objects.create(code="EUR", name="Euro", is_active=False)


@pytest.fixture
def order(db, client_obj, asset, fiat_currency):
    return Order.objects.create(
        client=client_obj,
        asset=asset,
        fiat_currency=fiat_currency,
        transaction_type=TransactionType.BUY,
        limit_price=Decimal("50000.00000000"),
        quantity=Decimal("0.01000000"),
        status=OrderStatus.PENDING,
    )


@pytest.fixture
def filled_order(db, client_obj, asset, fiat_currency):
    return Order.objects.create(
        client=client_obj,
        asset=asset,
        fiat_currency=fiat_currency,
        transaction_type=TransactionType.BUY,
        limit_price=Decimal("50000.00000000"),
        quantity=Decimal("0.01000000"),
        status=OrderStatus.FILLED,
    )


@pytest.fixture
def cancelled_order(db, client_obj, asset, fiat_currency):
    return Order.objects.create(
        client=client_obj,
        asset=asset,
        fiat_currency=fiat_currency,
        transaction_type=TransactionType.SELL,
        limit_price=Decimal("50000.00000000"),
        quantity=Decimal("0.01000000"),
        status=OrderStatus.CANCELLED,
    )


@pytest.fixture
def transaction_obj(db, client_obj, asset, fiat_currency, order):
    return Transaction.objects.create(
        client=client_obj,
        asset=asset,
        fiat_currency=fiat_currency,
        order=order,
        transaction_type=TransactionType.BUY,
        unit_price=Decimal("50000.00000000"),
        quantity=Decimal("0.01000000"),
        status=TransactionStatus.CONFIRMED,
    )
