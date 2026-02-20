from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    # Auth (identity)
    login_view,
    register_view,
    logout_view,
    profile_view,
    change_password_view,
    # Admin de usuarios
    UserListCreateView,
    UserDetailUpdateView,
    UserDeactivateView,
    UserResetPasswordView,
)

app_name = 'users'

urlpatterns = [
    # ------------------------------------------------------------------
    # Identity — Autenticación JWT
    # ------------------------------------------------------------------
    path('auth/login/',           login_view,                     name='login'),
    path('auth/register/',        register_view,                  name='register'),
    path('auth/logout/',          logout_view,                    name='logout'),
    path('auth/refresh/',         TokenRefreshView.as_view(),     name='token_refresh'),
    path('auth/profile/',         profile_view,                   name='profile'),
    path('auth/change-password/', change_password_view,           name='change_password'),

    # ------------------------------------------------------------------
    # Administración de Usuarios
    # Requieren permisos RBAC del módulo authorization.
    # ------------------------------------------------------------------
    path('users/',                    UserListCreateView.as_view(),  name='user-list-create'),
    path('users/<int:user_id>/',      UserDetailUpdateView.as_view(), name='user-detail-update'),
    path('users/<int:user_id>/deactivate/',     UserDeactivateView.as_view(),    name='user-deactivate'),
    path('users/<int:user_id>/reset-password/', UserResetPasswordView.as_view(), name='user-reset-password'),
]
