from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    login_view,
    register_view,
    logout_view,
    profile_view,
    change_password_view
)

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', login_view, name='login'),
    path('auth/register/', register_view, name='register'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User profile endpoints
    path('auth/profile/', profile_view, name='profile'),
    path('auth/change-password/', change_password_view, name='change_password'),
]