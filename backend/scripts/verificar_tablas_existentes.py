#!/usr/bin/env python3
"""
Script para verificar qué tablas existen realmente en la base de datos
"""
import requests
import json
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://pagos-f2qf.onrender.com"

def verificar_tablas_existentes():
    """Verificar qué tablas existen realmente"""
    print("=== VERIFICACION DE TABLAS EXISTENTES ===")
    
    try:
        # Probar endpoints que requieren diferentes tablas
        endpoints_tablas = [
            ("/api/v1/clientes/count", "clientes"),
            ("/api/v1/usuarios/", "usuarios"),
            ("/api/v1/prestamos/", "prestamos"),
            ("/api/v1/pagos/", "pagos"),
            ("/api/v1/amortizacion/", "amortizacion"),
            ("/api/v1/analistas/", "analistas"),
            ("/api/v1/modelos-vehiculos/", "modelos_vehiculos"),
            ("/api/v1/concesionarios/", "concesionarios")
        ]
        
        for endpoint, tabla in endpoints_tablas:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                print(f"   {tabla}: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if 'total' in data:
                        print(f"      Total registros: {data['total']}")
                    elif 'items' in data:
                        print(f"      Total registros: {len(data['items'])}")
                    else:
                        print(f"      Respuesta: {data}")
                elif response.status_code == 403:
                    print(f"      Requiere autenticacion")
                elif response.status_code == 404:
                    print(f"      Tabla no existe")
                elif response.status_code == 503:
                    print(f"      Error de servidor")
                    
            except Exception as e:
                print(f"   {tabla}: ERROR - {e}")
        
        print("\n=== CONCLUSIONES ===")
        print("Si una tabla da 404, no existe en la base de datos.")
        print("Si da 403, existe pero requiere autenticacion.")
        print("Si da 503, hay error en el modelo.")
        
    except Exception as e:
        print(f"Error verificando tablas: {e}")

if __name__ == "__main__":
    verificar_tablas_existentes()
