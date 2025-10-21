#!/usr/bin/env python3
"""
Test para verificar el formato exacto de errores HTTPException en FastAPI
"""

import requests
import json

def test_error_format():
    """Test para verificar el formato de error 503"""
    
    # URL del endpoint
    url = "https://pagos-f2qf.onrender.com/api/v1/clientes"
    
    # Datos de cliente con cédula duplicada
    data = {
        "cedula": "V31566283",  # Cédula que sabemos que existe
        "nombres": "TEST",
        "apellidos": "TEST",
        "telefono": "+581111111111",
        "email": "test@test.com",
        "direccion": "test",
        "fecha_nacimiento": "2025-10-01",
        "ocupacion": "TEST",
        "modelo_vehiculo": "ASIAWING NC250",
        "concesionario": "BARRETOMOTORCYCLE, C.A.",
        "analista": "BELIANA YSABEL GONZÁLEZ CARVAJAL",
        "estado": "ACTIVO",
        "notas": ""
    }
    
    # Headers con token de autenticación (necesitarás obtener un token válido)
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzIxMTI5NjIsInN1YiI6IjEiLCJ0eXBlIjoiYWNjZXNzIiwiaXNfYWRtaW4iOnRydWUsImVtYWlsIjoiaXRtYXN0ZXJAcmFwaWNyZWRpdGNhLmNvbSJ9.8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q"  # Token de prueba
    }
    
    try:
        print("🔍 Enviando request para crear cliente duplicado...")
        response = requests.post(url, json=data, headers=headers)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📊 Headers: {dict(response.headers)}")
        print(f"📊 Response Text: {response.text}")
        
        if response.status_code == 503:
            try:
                error_data = response.json()
                print(f"📊 Error JSON: {json.dumps(error_data, indent=2)}")
                print(f"📊 Error Keys: {list(error_data.keys())}")
                
                if 'detail' in error_data:
                    print(f"📊 Detail field: '{error_data['detail']}'")
                    print(f"📊 Contains 'duplicate key': {'duplicate key' in error_data['detail']}")
                    print(f"📊 Contains 'already exists': {'already exists' in error_data['detail']}")
                else:
                    print("❌ No 'detail' field found")
                    
            except json.JSONDecodeError:
                print("❌ Response is not valid JSON")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_error_format()
