"""
Script alternativo para generar amortizaciones usando la API del backend
Útil cuando hay problemas de encoding con DATABASE_URL directo

Uso:
    python scripts/python/Generar_Amortizacion_Por_API.py
"""

import requests
import os
import sys

# IDs de préstamos identificados sin amortización
PRESTAMOS_IDS = [1, 4, 5, 6, 8, 9, 10, 11, 15, 16, 3705, 3706, 3707, 3708]

# URL base del backend (ajustar según entorno)
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
# Para producción usar: BASE_URL = "https://rapicredit.onrender.com"

def generar_amortizacion_via_api(prestamo_id: int, token: str = None) -> tuple[bool, str]:
    """
    Genera amortización para un préstamo usando la API
    
    Args:
        prestamo_id: ID del préstamo
        token: Token de autenticación (opcional si no hay auth)
    
    Returns:
        (exito: bool, mensaje: str)
    """
    try:
        url = f"{BASE_URL}/api/v1/prestamos/{prestamo_id}/generar-amortizacion"
        
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        response = requests.post(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return True, f"Préstamo {prestamo_id}: Amortización generada"
        elif response.status_code == 404:
            return False, f"Préstamo {prestamo_id}: No encontrado"
        elif response.status_code == 401:
            return False, f"Préstamo {prestamo_id}: No autorizado (necesita token)"
        else:
            error_msg = response.json().get("detail", "Error desconocido") if response.content else "Error sin detalle"
            return False, f"Préstamo {prestamo_id}: {error_msg}"
            
    except requests.exceptions.ConnectionError:
        return False, f"Préstamo {prestamo_id}: Error de conexión al servidor"
    except Exception as e:
        return False, f"Préstamo {prestamo_id}: {str(e)}"


def main():
    """Función principal"""
    print("=" * 70)
    print("GENERAR AMORTIZACION POR API")
    print("=" * 70)
    print()
    print(f"Backend URL: {BASE_URL}")
    print(f"Préstamos a procesar: {len(PRESTAMOS_IDS)}")
    print(f"IDs: {', '.join(map(str, PRESTAMOS_IDS))}")
    print()
    
    # Solicitar token si es necesario
    token = None
    print("NOTA: Si el endpoint requiere autenticación, proporciona un token.")
    token_input = input("Token de autenticación (Enter para omitir): ").strip()
    if token_input:
        token = token_input
    
    # Confirmar
    respuesta = input(f"\n¿Generar amortización para estos {len(PRESTAMOS_IDS)} préstamos? (s/n): ")
    if respuesta.lower() != 's':
        print("\n[CANCELADO] Operación cancelada")
        return
    
    # Generar amortizaciones
    print("\n[INFO] Generando tablas de amortización...\n")
    
    exitosos = 0
    fallidos = 0
    
    for prestamo_id in PRESTAMOS_IDS:
        exito, mensaje = generar_amortizacion_via_api(prestamo_id, token)
        
        if exito:
            print(f"[OK] {mensaje}")
            exitosos += 1
        else:
            print(f"[ERROR] {mensaje}")
            fallidos += 1
    
    # Resumen final
    print("\n" + "=" * 70)
    print("RESUMEN DE GENERACIÓN")
    print("=" * 70)
    print(f"[OK] Exitosos: {exitosos}")
    print(f"[ERROR] Fallidos: {fallidos}")
    print(f"[INFO] Total procesados: {len(PRESTAMOS_IDS)}")
    print("=" * 70)


if __name__ == "__main__":
    main()

