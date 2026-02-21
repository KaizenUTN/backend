"""
brokerage.models
================
Modelos base del módulo de brokerage.

Contenido actual:
  - Client  — contraparte operacional identificada por CUIT.
  - Asset   — instrumento/activo negociable (crypto, FX, etc.).

Diseño deliberado:
  - Sin referencias a apps.users ni apps.audit en esta etapa.
  - Sin lógica financiera (Transaction, Order, Balance) todavía.
  - Campos mínimos necesarios para identificar contrapartes e instrumentos.
  - Preparado para extender: basta agregar ForeignKey a Client/Asset en
    los modelos que vengan (Transaction, Position, etc.).
"""

from __future__ import annotations

from django.db import models


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------


class ClientStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Activo"
    BLOCKED = "BLOCKED", "Bloqueado"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Client(models.Model):
    """
    Contraparte operacional del brokerage.

    Identificada de forma única por su CUIT (Clave Única de Identificación
    Tributaria), que es el identificador fiscal estándar en Argentina para
    personas físicas y jurídicas que operen instrumentos financieros.

    Notas de diseño:
    - `cuit` es el identificador de negocio (único, indexado).
    - `status` determina si la contraparte puede operar. Un cliente BLOCKED
      no debe poder generar órdenes ni transacciones nuevas.
    - `created_at` es inmutable (auto_now_add) para trazabilidad.
    - Sin FK a users en esta etapa: la vinculación con identidad se hará
      en una iteración posterior cuando se defina el flujo de onboarding.
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
        app_label = "brokerage"
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["cuit"], name="brokerage_client_cuit_idx"),
            models.Index(fields=["status"], name="brokerage_client_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.cuit})"

    @property
    def is_active(self) -> bool:
        return self.status == ClientStatus.ACTIVE


class Asset(models.Model):
    """
    Instrumento / activo negociable.

    Representa cualquier activo que pueda ser comprado, vendido o transferido
    en el sistema (criptomonedas, pares FX, instrumentos de renta fija, etc.).

    Notas de diseño:
    - `code` es el símbolo de mercado (BTC, ETH, USDT, ARS, USD, etc.).
      Único e indexado para búsquedas O(1) por ticker.
    - `name` es el nombre legible para UI/reportes.
    - `is_active` permite desactivar un activo sin borrarlo, preservando
      el historial de transacciones previas que lo referencien.
    - Sin campos de precio/volumen: esos datos pertenecen a Market Data,
      que se modelará por separado.
    """

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Código",
        help_text="Símbolo de mercado. Ej: BTC, ETH, USDT, ARS, USD.",
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Nombre",
        help_text="Nombre completo del activo. Ej: Bitcoin, Ethereum.",
        blank=True,
        default="",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
        help_text=(
            "Si False, el activo no acepta nuevas operaciones pero mantiene "
            "el historial histórico intacto."
        ),
    )

    class Meta:
        app_label = "brokerage"
        verbose_name = "Activo"
        verbose_name_plural = "Activos"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["code"], name="brokerage_asset_code_idx"),
            models.Index(fields=["is_active"], name="brokerage_asset_active_idx"),
        ]

    def __str__(self) -> str:
        return self.code
