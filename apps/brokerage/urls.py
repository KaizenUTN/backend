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
)

app_name = "brokerage"

urlpatterns = [
    # ------------------------------------------------------------------
    # Clients
    # ------------------------------------------------------------------
    path("brokerage/clients/",                    ClientListCreateView.as_view(), name="client-list-create"),
    path("brokerage/clients/<int:client_id>/",    ClientDetailView.as_view(),     name="client-detail"),
    path("brokerage/clients/<int:client_id>/block/",   ClientBlockView.as_view(), name="client-block"),
    path("brokerage/clients/<int:client_id>/unblock/", ClientUnblockView.as_view(), name="client-unblock"),

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------
    path("brokerage/assets/",                    AssetListCreateView.as_view(), name="asset-list-create"),
    path("brokerage/assets/<int:asset_id>/",     AssetDetailView.as_view(),     name="asset-detail"),
    path("brokerage/assets/<int:asset_id>/deactivate/", AssetDeactivateView.as_view(), name="asset-deactivate"),
    path("brokerage/assets/<int:asset_id>/reactivate/", AssetReactivateView.as_view(), name="asset-reactivate"),
]
