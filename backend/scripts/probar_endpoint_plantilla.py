#!/usr/bin/env python3
"""
Script para probar el endpoint de plantilla Excel
"""

import requests
import json

def probar_endpoint_plantilla():
    """Probar el endpoint de descarga de plantilla"""
    base_url = "https://rapicredit-backend.onrender.com"  # URL del backend en Render
    endpoint = f"{base_url}/api/v1/plantilla/plantilla-clientes"
    
    print(f"🔍 Probando endpoint: {endpoint}")
    
    try:
        # Hacer petición sin autenticación primero
        response = requests.get(endpoint, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print(f"✅ Éxito! Tamaño del archivo: {len(response.content)} bytes")
            print(f"📄 Content-Type: {response.headers.get('Content-Type')}")
            print(f"📁 Content-Disposition: {response.headers.get('Content-Disposition')}")
            
            # Verificar si es un archivo Excel válido
            if response.content.startswith(b'PK'):
                print("✅ Archivo Excel válido (comienza con PK)")
            else:
                print("❌ Archivo no parece ser Excel válido")
                print(f"🔍 Primeros 100 bytes: {response.content[:100]}")
                
        elif response.status_code == 401:
            print("🔐 Requiere autenticación")
            print(f"📄 Respuesta: {response.text}")
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📄 Respuesta: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    probar_endpoint_plantilla()
