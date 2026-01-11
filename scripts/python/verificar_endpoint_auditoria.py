"""
Script para verificar el endpoint de auditoría
Diagnostica por qué no aparecen datos en /api/v1/auditoria
"""

import os
import sys
import requests
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configuración
BASE_URL = os.getenv("API_URL", "https://rapicredit.onrender.com")
ENDPOINT = f"{BASE_URL}/api/v1/auditoria"

def verificar_endpoint():
    """Verifica el endpoint de auditoría"""
    print("=" * 80)
    print("🔍 VERIFICACIÓN DEL ENDPOINT DE AUDITORÍA")
    print("=" * 80)
    print(f"\n📍 URL: {ENDPOINT}")
    print(f"🌐 Base URL: {BASE_URL}\n")
    
    # 1. Verificar que el endpoint responde
    print("1️⃣ Verificando que el endpoint responde...")
    try:
        response = requests.get(
            ENDPOINT,
            params={
                "skip": 0,
                "limit": 10
            },
            timeout=30
        )
        
        print(f"   ✅ Status Code: {response.status_code}")
        print(f"   📋 Headers: {dict(response.headers)}\n")
        
        if response.status_code == 401:
            print("   ⚠️  Error 401: No autorizado")
            print("   💡 El endpoint requiere autenticación")
            print("   💡 Necesitas un token de autenticación válido\n")
            return
        
        if response.status_code != 200:
            print(f"   ❌ Error {response.status_code}")
            try:
                error_data = response.json()
                print(f"   📄 Respuesta: {error_data}")
            except:
                print(f"   📄 Respuesta (texto): {response.text[:500]}")
            return
        
        # 2. Analizar la respuesta
        print("2️⃣ Analizando respuesta...")
        try:
            data = response.json()
            print(f"   ✅ Respuesta JSON válida")
            print(f"   📊 Estructura recibida:")
            print(f"      - items: {type(data.get('items', []))} con {len(data.get('items', []))} elementos")
            print(f"      - total: {data.get('total', 'N/A')}")
            print(f"      - page: {data.get('page', 'N/A')}")
            print(f"      - page_size: {data.get('page_size', 'N/A')}")
            print(f"      - total_pages: {data.get('total_pages', 'N/A')}\n")
            
            # 3. Verificar contenido
            print("3️⃣ Verificando contenido...")
            items = data.get('items', [])
            total = data.get('total', 0)
            
            if total == 0:
                print("   ⚠️  No hay registros de auditoría (total = 0)")
                print("   💡 Posibles causas:")
                print("      - Las tablas de auditoría no existen en la BD")
                print("      - No hay registros de auditoría guardados")
                print("      - Hay un problema con las consultas a la BD")
            elif len(items) == 0 and total > 0:
                print(f"   ⚠️  Hay {total} registros pero no se retornaron items")
                print("   💡 Posible problema con la paginación o filtros")
            else:
                print(f"   ✅ Se encontraron {len(items)} registros de {total} totales")
                if len(items) > 0:
                    print(f"   📝 Primer registro:")
                    first_item = items[0]
                    for key, value in first_item.items():
                        print(f"      - {key}: {value}")
            
        except Exception as e:
            print(f"   ❌ Error parseando JSON: {e}")
            print(f"   📄 Respuesta (texto): {response.text[:500]}")
        
    except requests.exceptions.Timeout:
        print("   ❌ Timeout: El servidor no respondió a tiempo")
    except requests.exceptions.ConnectionError:
        print("   ❌ Error de conexión: No se pudo conectar al servidor")
        print(f"   💡 Verifica que {BASE_URL} esté disponible")
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ Verificación completada")
    print("=" * 80)

if __name__ == "__main__":
    verificar_endpoint()
