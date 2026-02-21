from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
from typing import cast

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model - read-only representation"""
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name',
                  'full_name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']


class LoginSerializer(serializers.Serializer):
    """Serializer for user login with email/password"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError(
                'Email and password are required.'
            )
        
        # Authenticate using email
        try:
            user = User.objects.get(email=email)
            if not user.check_password(password):
                raise serializers.ValidationError(
                    'Invalid email or password.'
                )
        except User.DoesNotExist:
            raise serializers.ValidationError(
                'Invalid email or password.'
            )
        
        if not user.is_active:
            raise serializers.ValidationError(
                'User account is not active.'
            )
        
        attrs['user'] = user
        return attrs


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name',
                  'password', 'password_confirm']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_password(self, value):
        # Construye un usuario temporal para que UserAttributeSimilarityValidator
        # pueda comparar la contraseña con email/first_name/last_name.
        partial_user = User(
            email=self.initial_data.get('email', ''),
            first_name=self.initial_data.get('first_name', ''),
            last_name=self.initial_data.get('last_name', ''),
        )
        try:
            validate_password(value, user=partial_user)
        except Exception as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        return attrs
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'A user with this email already exists.'
            )
        return value
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        # Genera un username único a partir del email (no expuesto en la API)
        base = validated_data.get('email', '').split('@')[0]
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        validated_data['username'] = username

        user = User.objects.create(**validated_data)
        user.set_password(password)

        # Asigna el rol por defecto "Operador" si está definido en el sistema.
        # Importación diferida para evitar acoplamiento circular users → authorization.
        # Si el rol no existe (entorno limpio sin seed), se deja sin rol.
        try:
            from apps.authorization.models import Role  # noqa: PLC0415
            user.role_id = Role.objects.get(name='Operador').pk
        except (ImportError, ObjectDoesNotExist):
            pass

        user.save()

        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password"""
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Passwords do not match.'
            })
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value

    def validate_new_password(self, value):
        # Pasa el usuario real para que UserAttributeSimilarityValidator
        # compare la nueva contraseña con email/nombre/apellido del usuario.
        user = self.context['request'].user
        try:
            validate_password(value, user=user)
        except Exception as exc:
            raise serializers.ValidationError(exc.messages)
        return value
    
    def save(self, **kwargs):
        if not self.validated_data:
            raise serializers.ValidationError('Serializer must be validated before saving.')
        
        user = self.context['request'].user
        # validated_data can be the DRF 'empty' sentinel at type-check time;
        # cast to dict so static analyzers (Pylance) know it supports .get()
        validated = cast(dict, self.validated_data)
        user.set_password(validated.get('new_password'))
        user.save()
        return user


# ===========================================================================
# Serializers de administración de usuarios
# ===========================================================================

class AdminUserSerializer(serializers.ModelSerializer):
    """
    Representación completa de un usuario para endpoints administrativos.
    Incluye role_name como campo de solo lectura para evitar un join adicional en el frontend.
    No expone password ni token_version.
    """
    full_name = serializers.CharField(read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_name', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class AdminCreateUserSerializer(serializers.Serializer):
    """
    Valida datos para el alta administrativa de un usuario.
    Role es opcional; si no se provee, el usuario queda sin rol asignado.
    """
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
    )
    role_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    is_active = serializers.BooleanField(default=True)

    def validate_email(self, value: str) -> str:
        from .models import User as _User
        if _User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Ya existe un usuario con este email.')
        return value


class AdminUpdateUserSerializer(serializers.Serializer):
    """
    Valida datos para la edición administrativa de un usuario.
    Todos los campos son opcionales (semántica PATCH).
    Para cambiar is_active usar el endpoint dedicado /deactivate/.
    Para cambiar password usar el endpoint dedicado /reset-password/.
    """
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    role_id = serializers.IntegerField(required=False, allow_null=True)
