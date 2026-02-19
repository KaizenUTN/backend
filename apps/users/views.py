from typing import cast

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    ChangePasswordSerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    User login endpoint
    POST /api/auth/login/
    Body: {"email": "user@example.com", "password": "password123"}
    Returns: {"access": "jwt_token", "refresh": "refresh_token", "user": {...}}
    """
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = cast(User, cast(dict, serializer.validated_data)['user'])
        
        # Generate JWT tokens
        refresh: RefreshToken = RefreshToken.for_user(user)  # type: ignore[assignment]
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    User registration endpoint
    POST /api/auth/register/
    Body: {
        "username": "johndoe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "password": "securePassword123",
        "password_confirm": "securePassword123"
    }
    Returns: {"access": "jwt_token", "refresh": "refresh_token", "user": {...}}
    """
    serializer = RegisterSerializer(data=request.data)
    
    if serializer.is_valid():
        user = cast(User, serializer.save())
        
        # Generate JWT tokens
        refresh: RefreshToken = RefreshToken.for_user(user)  # type: ignore[assignment]
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    User logout endpoint - blacklists the refresh token
    POST /api/auth/logout/
    Body: {"refresh": "refresh_token"}
    Returns: {"message": "Successfully logged out"}
    """
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        token = RefreshToken(refresh_token)
        token.blacklist()
        
        return Response(
            {'message': 'Successfully logged out'},
            status=status.HTTP_200_OK
        )
    except TokenError:
        return Response(
            {'error': 'Invalid or expired token'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """
    Get or update user profile
    GET /api/auth/profile/ - Returns current user data
    PUT/PATCH /api/auth/profile/ - Updates current user data
    Body for update: {"first_name": "John", "last_name": "Doe", "username": "johndoe"}
    """
    user = request.user
    
    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method in ['PUT', 'PATCH']:
        # Prevent email changes: always keep the user's current email
        data = request.data.copy()
        data['email'] = user.email
        
        serializer = UserSerializer(
            user,
            data=data,
            partial=(request.method == 'PATCH')
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """
    Change user password
    POST /api/auth/change-password/
    Body: {
        "old_password": "currentPassword123",
        "new_password": "newPassword123",
        "new_password_confirm": "newPassword123"
    }
    Returns: {"message": "Password changed successfully"}
    """
    serializer = ChangePasswordSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)