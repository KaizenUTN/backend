#!/usr/bin/env python
"""
Script para probar rápidamente la API de autenticación
Uso: python test_auth_api.py
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

def print_response(title, response):
    """Imprime una respuesta formateada"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

def test_authentication_flow():
    """Prueba el flujo completo de autenticación"""
    
    # 1. Registro
    print("\n🔹 PASO 1: Registrar nuevo usuario")
    register_data = {
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register/", json=register_data)
    print_response("REGISTRO", response)
    
    if response.status_code != 201:
        print("\n❌ Error en registro. Intentando login con usuario existente...")
        # Si el usuario ya existe, intentar login
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
        print_response("LOGIN (usuario existente)", response)
    
    if response.status_code not in [200, 201]:
        print("\n❌ Error. No se pudo obtener tokens.")
        return
    
    tokens = response.json()
    access_token = tokens.get('access')
    refresh_token = tokens.get('refresh')
    
    print(f"\n✅ Access Token: {access_token[:50]}...")
    print(f"✅ Refresh Token: {refresh_token[:50]}...")
    
    # 2. Obtener perfil
    print("\n🔹 PASO 2: Obtener perfil de usuario")
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{BASE_URL}/auth/profile/", headers=headers)
    print_response("PERFIL", response)
    
    # 3. Actualizar perfil
    print("\n🔹 PASO 3: Actualizar perfil")
    update_data = {
        "first_name": "Updated",
        "last_name": "Name"
    }
    response = requests.patch(f"{BASE_URL}/auth/profile/", 
                            headers=headers, 
                            json=update_data)
    print_response("ACTUALIZAR PERFIL", response)
    
    # 4. Cambiar contraseña
    print("\n🔹 PASO 4: Cambiar contraseña")
    change_password_data = {
        "old_password": "TestPassword123!",
        "new_password": "NewTestPassword456!",
        "new_password_confirm": "NewTestPassword456!"
    }
    response = requests.post(f"{BASE_URL}/auth/change-password/", 
                           headers=headers, 
                           json=change_password_data)
    print_response("CAMBIAR CONTRASEÑA", response)
    
    # 5. Refresh token
    print("\n🔹 PASO 5: Refresh token")
    response = requests.post(f"{BASE_URL}/auth/refresh/", 
                           json={"refresh": refresh_token})
    print_response("REFRESH TOKEN", response)
    
    if response.status_code == 200:
        new_access_token = response.json().get('access')
        print(f"\n✅ Nuevo Access Token: {new_access_token[:50]}...")
        headers = {"Authorization": f"Bearer {new_access_token}"}
    
    # 6. Logout
    print("\n🔹 PASO 6: Logout")
    response = requests.post(f"{BASE_URL}/auth/logout/", 
                           headers=headers, 
                           json={"refresh": refresh_token})
    print_response("LOGOUT", response)
    
    # 7. Intentar acceder con token blacklisted
    print("\n🔹 PASO 7: Intentar usar token después de logout")
    response = requests.get(f"{BASE_URL}/auth/profile/", headers=headers)
    print_response("ACCESO DESPUÉS DE LOGOUT", response)
    
    print("\n" + "="*60)
    print("✅ PRUEBA COMPLETADA")
    print("="*60)

if __name__ == "__main__":
    try:
        test_authentication_flow()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: No se pudo conectar al servidor.")
        print("Asegúrate de que los contenedores estén corriendo:")
        print("   docker-compose -f docker-compose.dev.yaml up -d")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
