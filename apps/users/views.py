from typing import cast

from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
    inline_serializer,
)
from rest_framework import serializers as drf_serializers
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

# ---------------------------------------------------------------------------
# Shared inline response schemas
# ---------------------------------------------------------------------------

_auth_token_response = inline_serializer(
    name='AuthTokenResponse',
    fields={
        'access': drf_serializers.CharField(
            help_text='JWT access token. Válido por 10 minutos. '
                      'Incluirlo en el header: Authorization: Bearer <token>'
        ),
        'refresh': drf_serializers.CharField(
            help_text='JWT refresh token. Válido por 7 días. '
                      'Usarlo en /api/auth/refresh/ para obtener un nuevo access token.'
        ),
        'user': UserSerializer(),
    }
)

_error_response = inline_serializer(
    name='ErrorResponse',
    fields={'error': drf_serializers.CharField(help_text='Descripción del error.')}
)

_message_response = inline_serializer(
    name='MessageResponse',
    fields={'message': drf_serializers.CharField(help_text='Mensaje de confirmación.')}
)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Autenticación'],
    summary='Iniciar sesión',
    description=(
        'Autentica a un usuario registrado con email y contraseña.\n\n'
        '**Retorna** un par de tokens JWT (`access` + `refresh`) junto con los datos '
        'básicos del usuario.\n\n'
        '- El token `access` debe incluirse en el header `Authorization: Bearer <token>` '
        'en todas las peticiones protegidas.\n'
        '- El token `access` expira en **60 minutos**.\n'
        '- El token `refresh` expira en **7 días** y sirve para renovar el `access` token '
        'sin necesidad de volver a iniciar sesión.\n\n'
        '**Errores comunes:**\n'
        '- `400` — Email o contraseña incorrectos.\n'
        '- `400` — El usuario está inactivo.'
    ),
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(
            response=_auth_token_response,
            description='Login exitoso. Retorna tokens JWT y datos del usuario.',
            examples=[
                OpenApiExample(
                    name='Login exitoso',
                    value={
                        'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                        'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                        'user': {
                            'id': 1,
                            'email': 'john@example.com',
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'full_name': 'John Doe',
                            'is_active': True,
                            'created_at': '2025-01-01T00:00:00Z',
                            'updated_at': '2025-01-01T00:00:00Z',
                        }
                    },
                    response_only=True,
                )
            ]
        ),
        400: OpenApiResponse(
            response=_error_response,
            description='Credenciales inválidas o usuario inactivo.',
            examples=[
                OpenApiExample(
                    name='Credenciales inválidas',
                    value={'non_field_errors': ['Invalid email or password.']},
                    response_only=True,
                )
            ]
        ),
    },
    examples=[
        OpenApiExample(
            name='Ejemplo de login',
            value={'email': 'john@example.com', 'password': 'securePassword123'},
            request_only=True,
        )
    ]
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


@extend_schema(
    tags=['Autenticación'],
    summary='Registrar nuevo usuario',
    description=(
        'Crea una nueva cuenta de usuario en el sistema.\n\n'
        '**Retorna** un par de tokens JWT (`access` + `refresh`) junto con los datos '
        'del usuario recién creado, permitiendo un inicio de sesión inmediato tras el registro.\n\n'
        '**Validaciones aplicadas:**\n'
        '- `email` debe ser único y tener formato válido.\n'
        '- `first_name` y `last_name` son obligatorios.\n'
        '- `password` debe cumplir las políticas de Django: mínimo 8 caracteres, '
        'no puede ser completamente numérica, no puede ser demasiado común.\n'
        '- `password` y `password_confirm` deben coincidir.\n\n'
        '**Errores comunes:**\n'
        '- `400` — El email ya está en uso.\n'
        '- `400` — Las contraseñas no coinciden.\n'
        '- `400` — La contraseña no cumple los requisitos de seguridad.'
    ),
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(
            response=_auth_token_response,
            description='Registro exitoso. Retorna tokens JWT y datos del usuario creado.',
            examples=[
                OpenApiExample(
                    name='Registro exitoso',
                    value={
                        'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                        'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                        'user': {
                            'id': 2,
                            'email': 'jane@example.com',
                            'first_name': 'Jane',
                            'last_name': 'Doe',
                            'full_name': 'Jane Doe',
                            'is_active': True,
                            'created_at': '2025-06-01T12:00:00Z',
                            'updated_at': '2025-06-01T12:00:00Z',
                        }
                    },
                    response_only=True,
                )
            ]
        ),
        400: OpenApiResponse(
            description='Datos de registro inválidos.',
            examples=[
                OpenApiExample(
                    name='Email duplicado',
                    value={'email': ['A user with this email already exists.']},
                    response_only=True,
                ),
                OpenApiExample(
                    name='Contraseñas no coinciden',
                    value={'password_confirm': ['Passwords do not match.']},
                    response_only=True,
                ),
            ]
        ),
    },
    examples=[
        OpenApiExample(
            name='Ejemplo de registro',
            value={
                'email': 'jane@example.com',
                'first_name': 'Jane',
                'last_name': 'Doe',
                'password': 'securePassword123',
                'password_confirm': 'securePassword123',
            },
            request_only=True,
        )
    ]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    User registration endpoint
    POST /api/auth/register/
    Body: {
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


@extend_schema(
    tags=['Autenticación'],
    summary='Cerrar sesión',
    description=(
        'Invalida el `refresh` token del usuario, cerrando efectivamente la sesión.\n\n'
        'El token es agregado a la **blacklist** de SimpleJWT, por lo que no podrá '
        'usarse nuevamente para obtener nuevos `access` tokens, incluso si aún no ha expirado.\n\n'
        '> ⚠️ **Importante:** El cliente también debe eliminar los tokens almacenados '
        'localmente (localStorage, cookies, etc.) al recibir la respuesta `200`.\n\n'
        '**Requiere autenticación:** Header `Authorization: Bearer <access_token>`\n\n'
        '**Errores comunes:**\n'
        '- `400` — No se proporcionó el refresh token.\n'
        '- `400` — El refresh token es inválido o ya expiró.\n'
        '- `401` — No se proporcionó el access token en el header.'
    ),
    request=inline_serializer(
        name='LogoutRequest',
        fields={
            'refresh': drf_serializers.CharField(
                help_text='El refresh token JWT que se desea invalidar.'
            )
        }
    ),
    responses={
        200: OpenApiResponse(
            response=_message_response,
            description='Sesión cerrada correctamente.',
            examples=[
                OpenApiExample(
                    name='Logout exitoso',
                    value={'message': 'Successfully logged out'},
                    response_only=True,
                )
            ]
        ),
        400: OpenApiResponse(
            description='Refresh token no proporcionado o inválido.',
            examples=[
                OpenApiExample(
                    name='Token faltante',
                    value={'error': 'Refresh token is required'},
                    response_only=True,
                ),
                OpenApiExample(
                    name='Token inválido',
                    value={'error': 'Invalid or expired token'},
                    response_only=True,
                ),
            ]
        ),
        401: OpenApiResponse(description='No autenticado. Access token no proporcionado.'),
    },
    examples=[
        OpenApiExample(
            name='Ejemplo de logout',
            value={'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'},
            request_only=True,
        )
    ]
)
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


@extend_schema(
    methods=['GET'],
    tags=['Perfil de usuario'],
    summary='Obtener perfil del usuario autenticado',
    description=(
        'Retorna los datos del perfil del usuario actualmente autenticado.\n\n'
        '**Requiere autenticación:** Header `Authorization: Bearer <access_token>`\n\n'
        'Los campos retornados incluyen información básica del perfil y metadatos '
        'de auditoría (`created_at`, `updated_at`).\n\n'
        '**Errores comunes:**\n'
        '- `401` — No autenticado o token expirado.'
    ),
    responses={
        200: OpenApiResponse(
            response=UserSerializer,
            description='Datos del perfil del usuario.',
            examples=[
                OpenApiExample(
                    name='Perfil del usuario',
                    value={
                        'id': 1,
                        'email': 'john@example.com',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'full_name': 'John Doe',
                        'is_active': True,
                        'created_at': '2025-01-01T00:00:00Z',
                        'updated_at': '2025-06-01T10:30:00Z',
                    },
                    response_only=True,
                )
            ]
        ),
        401: OpenApiResponse(description='No autenticado o token expirado.'),
    }
)
@extend_schema(
    methods=['PUT'],
    tags=['Perfil de usuario'],
    summary='Actualizar perfil completo',
    description=(
        'Actualiza completamente los datos del perfil del usuario autenticado.\n\n'
        '**Requiere autenticación:** Header `Authorization: Bearer <access_token>`\n\n'
        '> ℹ️ **Nota:** El campo `email` no puede modificarse a través de este endpoint. '
        'Aunque se envíe en el body, será ignorado y se conservará el email actual.\n\n'
        'Con `PUT` todos los campos son requeridos (excepto email). '
        'Para actualizaciones parciales usar `PATCH`.\n\n'
        '**Campos actualizables:** `first_name`, `last_name`\n\n'
        '**Errores comunes:**\n'
        '- `400` — Datos de validación inválidos.\n'
        '- `401` — No autenticado o token expirado.'
    ),
    request=inline_serializer(
        name='ProfileUpdateRequest',
        fields={
            'first_name': drf_serializers.CharField(help_text='Nombre del usuario.'),
            'last_name': drf_serializers.CharField(help_text='Apellido del usuario.'),
        }
    ),
    responses={
        200: OpenApiResponse(
            response=UserSerializer,
            description='Perfil actualizado correctamente.',
        ),
        400: OpenApiResponse(description='Datos de validación inválidos.'),
        401: OpenApiResponse(description='No autenticado o token expirado.'),
    },
    examples=[
        OpenApiExample(
            name='Actualización completa',
            value={'first_name': 'John', 'last_name': 'Smith'},
            request_only=True,
        )
    ]
)
@extend_schema(
    methods=['PATCH'],
    tags=['Perfil de usuario'],
    summary='Actualizar perfil parcialmente',
    description=(
        'Actualiza uno o más campos del perfil del usuario autenticado sin necesidad '
        'de enviar todos los campos.\n\n'
        '**Requiere autenticación:** Header `Authorization: Bearer <access_token>`\n\n'
        '> ℹ️ **Nota:** El campo `email` no puede modificarse a través de este endpoint.\n\n'
        '**Campos actualizables:** `first_name`, `last_name`\n\n'
        '**Errores comunes:**\n'
        '- `400` — Datos de validación inválidos.\n'
        '- `401` — No autenticado o token expirado.'
    ),
    request=inline_serializer(
        name='ProfilePatchRequest',
        fields={
            'first_name': drf_serializers.CharField(
                required=False, help_text='Nombre del usuario (opcional).'
            ),
            'last_name': drf_serializers.CharField(
                required=False, help_text='Apellido del usuario (opcional).'
            ),
        }
    ),
    responses={
        200: OpenApiResponse(
            response=UserSerializer,
            description='Perfil actualizado parcialmente.',
        ),
        400: OpenApiResponse(description='Datos de validación inválidos.'),
        401: OpenApiResponse(description='No autenticado o token expirado.'),
    },
    examples=[
        OpenApiExample(
            name='Actualización parcial',
            value={'first_name': 'Jonathan'},
            request_only=True,
        )
    ]
)
@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """
    Get or update user profile
    GET /api/auth/profile/ - Returns current user data
    PUT/PATCH /api/auth/profile/ - Updates current user data
    Body for update: {"first_name": "John", "last_name": "Doe"}
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


@extend_schema(
    tags=['Perfil de usuario'],
    summary='Cambiar contraseña',
    description=(
        'Permite al usuario autenticado cambiar su contraseña actual por una nueva.\n\n'
        '**Requiere autenticación:** Header `Authorization: Bearer <access_token>`\n\n'
        '**Proceso de validación:**\n'
        '1. Se verifica que `old_password` coincida con la contraseña actual del usuario.\n'
        '2. Se valida que `new_password` cumpla las políticas de seguridad de Django.\n'
        '3. Se verifica que `new_password` y `new_password_confirm` coincidan.\n\n'
        '**Políticas de contraseña:**\n'
        '- Mínimo 8 caracteres.\n'
        '- No puede ser completamente numérica.\n'
        '- No puede ser una contraseña demasiado común (ej: "password123").\n'
        '- No puede ser demasiado similar al nombre de usuario o email.\n\n'
        '> ⚠️ **Importante:** Tras cambiar la contraseña se recomienda cerrar sesión '
        '(`/api/auth/logout/`) e iniciar sesión nuevamente para obtener tokens frescos.\n\n'
        '**Errores comunes:**\n'
        '- `400` — La contraseña actual es incorrecta.\n'
        '- `400` — Las nuevas contraseñas no coinciden.\n'
        '- `400` — La nueva contraseña no cumple los requisitos de seguridad.\n'
        '- `401` — No autenticado o token expirado.'
    ),
    request=ChangePasswordSerializer,
    responses={
        200: OpenApiResponse(
            response=_message_response,
            description='Contraseña cambiada exitosamente.',
            examples=[
                OpenApiExample(
                    name='Cambio exitoso',
                    value={'message': 'Password changed successfully'},
                    response_only=True,
                )
            ]
        ),
        400: OpenApiResponse(
            description='Datos de validación inválidos.',
            examples=[
                OpenApiExample(
                    name='Contraseña actual incorrecta',
                    value={'old_password': ['Old password is incorrect.']},
                    response_only=True,
                ),
                OpenApiExample(
                    name='Contraseñas no coinciden',
                    value={'new_password_confirm': ['Passwords do not match.']},
                    response_only=True,
                ),
            ]
        ),
        401: OpenApiResponse(description='No autenticado o token expirado.'),
    },
    examples=[
        OpenApiExample(
            name='Cambio de contraseña',
            value={
                'old_password': 'currentPassword123',
                'new_password': 'newSecurePass456',
                'new_password_confirm': 'newSecurePass456',
            },
            request_only=True,
        )
    ]
)
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
