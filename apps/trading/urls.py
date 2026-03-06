from django.urls import path

from .views import (
    AssetDeactivateView,
    AssetDetailView,
    AssetListCreateView,
    AssetReactivateView,
    ClientBlockView,
    ClientDetailView,
    ClientListCreateView,
    ClientUnblockView,
    FiatCurrencyDeactivateView,
    FiatCurrencyDetailView,
    FiatCurrencyListCreateView,
    FiatCurrencyReactivateView,
    OrderCancelView,
    OrderDetailView,
    OrderListCreateView,
    TransactionDetailView,
    TransactionListCreateView,
)

app_name = "trading"

urlpatterns = [
    # ------------------------------------------------------------------
    # Clients
    # ------------------------------------------------------------------
    path("trading/clients/",                          ClientListCreateView.as_view(),  name="client-list-create"),
    path("trading/clients/<int:client_id>/",          ClientDetailView.as_view(),      name="client-detail"),
    path("trading/clients/<int:client_id>/block/",    ClientBlockView.as_view(),       name="client-block"),
    path("trading/clients/<int:client_id>/unblock/",  ClientUnblockView.as_view(),     name="client-unblock"),

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------
    path("trading/assets/",                              AssetListCreateView.as_view(),   name="asset-list-create"),
    path("trading/assets/<int:asset_id>/",               AssetDetailView.as_view(),       name="asset-detail"),
    path("trading/assets/<int:asset_id>/deactivate/",    AssetDeactivateView.as_view(),   name="asset-deactivate"),
    path("trading/assets/<int:asset_id>/reactivate/",    AssetReactivateView.as_view(),   name="asset-reactivate"),

    # ------------------------------------------------------------------
    # Fiat Currencies
    # ------------------------------------------------------------------
    path("trading/fiat-currencies/",                            FiatCurrencyListCreateView.as_view(),  name="fiat-list-create"),
    path("trading/fiat-currencies/<int:fiat_id>/",              FiatCurrencyDetailView.as_view(),      name="fiat-detail"),
    path("trading/fiat-currencies/<int:fiat_id>/deactivate/",   FiatCurrencyDeactivateView.as_view(),  name="fiat-deactivate"),
    path("trading/fiat-currencies/<int:fiat_id>/reactivate/",   FiatCurrencyReactivateView.as_view(),  name="fiat-reactivate"),

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    path("trading/orders/",                         OrderListCreateView.as_view(), name="order-list-create"),
    path("trading/orders/<int:order_id>/",          OrderDetailView.as_view(),     name="order-detail"),
    path("trading/orders/<int:order_id>/cancel/",   OrderCancelView.as_view(),     name="order-cancel"),

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------
    path("trading/transactions/",              TransactionListCreateView.as_view(), name="transaction-list-create"),
    path("trading/transactions/<int:tx_id>/",  TransactionDetailView.as_view(),     name="transaction-detail"),
]

