"""
trading.models
==============
Modelos del módulo de trading.

Entidades:
  - Client         — contraparte operacional identificada por CUIT.
  - Asset          — criptoactivo negociable (BTC, ETH, USDT, etc.).
  - FiatCurrency   — moneda fiat de liquidación (ARS, USD).
  - Order          — intención de compra/venta a precio límite (nivel exchange).
  - Transaction    — operación contable ejecutada e inmutable.

Principios de diseño:
  - `Transaction` es INMUTABLE: representa un hecho contable ya ocurrido.
    Save solo permite INSERT, nunca UPDATE.
  - `total` es una propiedad calculada, no se persiste en DB para evitar
    inconsistencias entre precio_unitario * cantidad y el valor almacenado.
  - `AuditoriaTransaccion` NO existe aquí: se usa apps.audit para trazabilidad.
  - Nombres en inglés para consistencia con el resto del proyecto.
  - on_delete=PROTECT en todas las FK contables: no se puede borrar un Asset
    o Client si tiene transacciones vinculadas.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------


class ClientStatus(models.TextChoices):
    ACTIVE  = "ACTIVE",  "Activo"
    BLOCKED = "BLOCKED", "Bloqueado"


class TransactionType(models.TextChoices):
    BUY  = "BUY",  "Compra"
    SELL = "SELL", "Venta"


class OrderStatus(models.TextChoices):
    PENDING   = "PENDING",   "Pendiente"
    FILLED    = "FILLED",    "Ejecutada"
    PARTIAL   = "PARTIAL",   "Parcialmente ejecutada"
    CANCELLED = "CANCELLED", "Cancelada"


class TransactionStatus(models.TextChoices):
    CONFIRMED = "CONFIRMED", "Confirmada"
    PENDING   = "PENDING",   "Pendiente"
    FAILED    = "FAILED",    "Fallida"
    REVERSED  = "REVERSED",  "Revertida"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class Client(models.Model):
    """
    Contraparte operacional del brokerage.

    Identificada de forma única por su CUIT (Clave Única de Identificación
    Tributaria), identificador fiscal estándar en Argentina.

    - Un cliente BLOCKED no puede generar órdenes ni transacciones nuevas.
    - No se puede eliminar si tiene transacciones vinculadas (PROTECT).
    """

    cuit = models.CharField(
        max_length=13,
        unique=True,
        verbose_name="CUIT",
        help_text="Formato: XX-XXXXXXXX-X. Identificador fiscal único.",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Nombre / Razón social",
    )
    email = models.EmailField(
        blank=True,
        default="",
        verbose_name="Email",
    )
    status = models.CharField(
        max_length=10,
        choices=ClientStatus.choices,
        default=ClientStatus.ACTIVE,
        verbose_name="Estado",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de alta",
    )

    class Meta:
        app_label = "trading"
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["cuit"],   name="trading_client_cuit_idx"),
            models.Index(fields=["status"], name="trading_client_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.cuit})"

    @property
    def is_active(self) -> bool:
        return self.status == ClientStatus.ACTIVE


# ---------------------------------------------------------------------------
# Asset (criptoactivos)
# ---------------------------------------------------------------------------


class Asset(models.Model):
    """
    Criptoactivo negociable (BTC, ETH, USDT, etc.).

    - No se puede eliminar si tiene transacciones vinculadas (PROTECT).
    - `is_active=False` permite desactivar sin borrar el historial.
    """

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Código",
        help_text="Símbolo de mercado. Ej: BTC, ETH, USDT.",
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Nombre",
        help_text="Nombre completo. Ej: Bitcoin, Ethereum.",
        blank=True,
        default="",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
        help_text="Si False, no acepta nuevas operaciones pero mantiene historial.",
    )

    class Meta:
        app_label = "trading"
        verbose_name = "Activo"
        verbose_name_plural = "Activos"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["code"],      name="trading_asset_code_idx"),
            models.Index(fields=["is_active"], name="trading_asset_active_idx"),
        ]

    def __str__(self) -> str:
        return self.code


# ---------------------------------------------------------------------------
# FiatCurrency (monedas de liquidación)
# ---------------------------------------------------------------------------


class FiatCurrency(models.Model):
    """
    Moneda fiat de liquidación (ARS, USD).

    Separada de Asset deliberadamente: las reglas de negocio son distintas.
    Un activo crypto puede operar en múltiples monedas fiat.
    """

    code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="Código ISO",
        help_text="Código ISO 4217. Ej: ARS, USD.",
    )
    name = models.CharField(
        max_length=50,
        verbose_name="Nombre",
        help_text="Ej: Peso Argentino, Dólar Estadounidense.",
        blank=True,
        default="",
    )
    is_active = models.BooleanField(default=True, verbose_name="¿Activa?")

    class Meta:
        app_label = "trading"
        verbose_name = "Moneda Fiat"
        verbose_name_plural = "Monedas Fiat"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


# ---------------------------------------------------------------------------
# Order (intención de operación — nivel exchange)
# ---------------------------------------------------------------------------


class Order(models.Model):
    """
    Intención de compra/venta a precio límite.

    Representa la orden antes de ser ejecutada. Una Order puede derivar
    en cero, una o múltiples Transactions (ejecución parcial).

    Estados:
      PENDING   → recibida, no ejecutada aún.
      PARTIAL   → ejecutada parcialmente.
      FILLED    → ejecutada en su totalidad.
      CANCELLED → cancelada antes de completarse.
    """

    client          = models.ForeignKey(Client,       on_delete=models.PROTECT, verbose_name="Cliente",        related_name="orders")
    asset           = models.ForeignKey(Asset,        on_delete=models.PROTECT, verbose_name="Activo",         related_name="orders")
    fiat_currency   = models.ForeignKey(FiatCurrency, on_delete=models.PROTECT, verbose_name="Moneda fiat",    related_name="orders")
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices, verbose_name="Tipo")
    limit_price     = models.DecimalField(
        max_digits=20, decimal_places=8,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        verbose_name="Precio límite",
    )
    quantity        = models.DecimalField(
        max_digits=20, decimal_places=8,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        verbose_name="Cantidad",
    )
    status          = models.CharField(
        max_length=10,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        verbose_name="Estado",
    )
    created_at      = models.DateTimeField(auto_now_add=True, verbose_name="Creada en")
    updated_at      = models.DateTimeField(auto_now=True,     verbose_name="Actualizada en")

    class Meta:
        app_label = "trading"
        verbose_name = "Orden"
        verbose_name_plural = "Órdenes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client", "status"],           name="trad_order_client_status_idx"),
            models.Index(fields=["asset", "transaction_type"],  name="trading_order_asset_type_idx"),
            models.Index(fields=["status", "created_at"],       name="trading_order_status_ts_idx"),
        ]

    def __str__(self) -> str:
        return f"Order #{self.pk} — {self.get_transaction_type_display()} {self.quantity} {self.asset} @ {self.limit_price} {self.fiat_currency}"

    @property
    def notional(self) -> Decimal:
        """Valor nocional de la orden: precio_límite × cantidad."""
        return self.limit_price * self.quantity


# ---------------------------------------------------------------------------
# Transaction (operación contable ejecutada — INMUTABLE)
# ---------------------------------------------------------------------------


class Transaction(models.Model):
    """
    Operación contable ejecutada. INMUTABLE por diseño.

    Representa un hecho financiero ya ocurrido: no se modifica nunca.
    Para revertir una operación se crea una nueva Transaction de signo contrario.

    `total` es una propiedad calculada (unit_price × quantity) — no se
    persiste en DB para evitar inconsistencias. El valor siempre se deriva
    de los campos fuente.

    La trazabilidad de quién ejecutó la transacción queda en apps.audit,
    no en este modelo.
    """

    client           = models.ForeignKey(Client,       on_delete=models.PROTECT,  verbose_name="Cliente",     related_name="transactions")
    order            = models.ForeignKey(Order,        on_delete=models.SET_NULL, verbose_name="Orden",       related_name="transactions", null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices, verbose_name="Tipo")
    asset            = models.ForeignKey(Asset,        on_delete=models.PROTECT,  verbose_name="Activo",      related_name="transactions")
    fiat_currency    = models.ForeignKey(FiatCurrency, on_delete=models.PROTECT,  verbose_name="Moneda fiat", related_name="transactions")
    unit_price       = models.DecimalField(
        max_digits=20, decimal_places=8,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        verbose_name="Precio unitario",
        help_text="Precio de ejecución en moneda fiat al momento de la operación.",
    )
    quantity         = models.DecimalField(
        max_digits=20, decimal_places=8,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        verbose_name="Cantidad",
        help_text="Cantidad del activo operado.",
    )
    status           = models.CharField(
        max_length=10,
        choices=TransactionStatus.choices,
        default=TransactionStatus.CONFIRMED,
        verbose_name="Estado",
    )
    blockchain_hash  = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Hash blockchain",
        help_text="Hash de la transacción on-chain, si aplica.",
    )
    created_at       = models.DateTimeField(auto_now_add=True, verbose_name="Ejecutada en")

    class Meta:
        app_label = "trading"
        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client", "created_at"],        name="trading_tx_client_ts_idx"),
            models.Index(fields=["asset", "transaction_type"],   name="trading_tx_asset_type_idx"),
            models.Index(fields=["status", "created_at"],        name="trading_tx_status_ts_idx"),
            models.Index(fields=["fiat_currency", "created_at"], name="trading_tx_fiat_ts_idx"),
        ]

    # ------------------------------------------------------------------
    # Inmutabilidad — una transacción ejecutada no se modifica nunca
    # ------------------------------------------------------------------

    def save(self, *args, **kwargs) -> None:
        if self.pk is not None:
            raise PermissionError(
                f"Las transacciones son inmutables. "
                f"No se puede modificar Transaction (pk={self.pk}). "
                "Para revertir, creá una nueva transacción de signo contrario."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> None:
        raise PermissionError(
            f"Las transacciones son inmutables. "
            f"No se puede eliminar Transaction (pk={self.pk})."
        )

    # ------------------------------------------------------------------
    # Propiedades calculadas
    # ------------------------------------------------------------------

    @property
    def total(self) -> Decimal:
        """Monto total en moneda fiat: unit_price × quantity."""
        return self.unit_price * self.quantity

    def __str__(self) -> str:
        return (
            f"Tx #{self.pk} — {self.get_transaction_type_display()} "
            f"{self.quantity} {self.asset} @ {self.unit_price} {self.fiat_currency} "
            f"= {self.total}"
        )
