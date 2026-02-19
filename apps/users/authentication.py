from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication
    Extiende la autenticación JWT para agregar validaciones personalizadas
    """
    
    def authenticate(self, request):
        """
        Autentica la request usando JWT
        """
        # Llamar al método de autenticación base
        result = super().authenticate(request)
        
        if result is None:
            return None
        
        user, token = result
        
        # Validación adicional: verificar si el usuario está activo
        if not user.is_active:
            raise exceptions.AuthenticationFailed('Usuario inactivo')
        
        return user, token
