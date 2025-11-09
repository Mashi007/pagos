"""
Script para probar el endpoint de financiamiento-por-rangos
Simula las llamadas del frontend para verificar que funciona correctamente
"""

import sys
import os
import requests
import json
from pathlib import Path
from datetime import date

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_endpoint(base_url: str = "http://localhost:8000", token: str = None):
    """
    Prueba el endpoint de financiamiento-por-rangos con diferentes parámetros
    """
    print("=" * 80)
    print("🧪 PRUEBA DEL ENDPOINT: /api/v1/dashboard/financiamiento-por-rangos")
    print("=" * 80)
    print()

    if not token:
        print("⚠️  No se proporcionó token de autenticación")
        print("   El endpoint puede requerir autenticación")
        print()

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Casos de prueba
    casos_prueba = [
        {
            "nombre": "Sin filtros (todos los préstamos)",
            "params": {}
        },
        {
            "nombre": "Año actual completo",
            "params": {
                "fecha_inicio": f"{date.today().year}-01-01",
                "fecha_fin": f"{date.today().year}-12-31"
            }
        },
        {
            "nombre": "Mes actual",
            "params": {
                "fecha_inicio": f"{date.today().year}-{date.today().month:02d}-01",
                "fecha_fin": f"{date.today().year}-{date.today().month:02d}-{date.today().day:02d}"
            }
        },
    ]

    for caso in casos_prueba:
        print(f"📋 Prueba: {caso['nombre']}")
        print("-" * 80)

        url = f"{base_url}/api/v1/dashboard/financiamiento-por-rangos"

        try:
            response = requests.get(url, params=caso["params"], headers=headers, timeout=30)

            print(f"  Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                total_prestamos = data.get("total_prestamos", 0)
                total_monto = data.get("total_monto", 0)
                rangos = data.get("rangos", [])

                print(f"  ✅ Total préstamos: {total_prestamos:,}")
                print(f"  ✅ Total monto: ${total_monto:,.2f}")
                print(f"  ✅ Rangos con datos: {len([r for r in rangos if r.get('cantidad_prestamos', 0) > 0])}")

                # Mostrar primeros 5 rangos con datos
                rangos_con_datos = [r for r in rangos if r.get("cantidad_prestamos", 0) > 0][:5]
                if rangos_con_datos:
                    print(f"  📊 Primeros rangos con datos:")
                    for rango in rangos_con_datos:
                        print(f"     • {rango.get('categoria', 'N/A')}: {rango.get('cantidad_prestamos', 0):,} préstamos, ${rango.get('monto_total', 0):,.2f}")
                else:
                    print(f"  ⚠️  No hay rangos con datos")

                if total_prestamos == 0:
                    print(f"  ⚠️  ADVERTENCIA: El endpoint retorna 0 préstamos")
                    print(f"     Esto puede indicar un problema con los filtros de fecha")
            else:
                print(f"  ❌ Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"     Detalle: {error_data.get('detail', 'Sin detalle')}")
                except:
                    print(f"     Respuesta: {response.text[:200]}")

        except requests.exceptions.ConnectionError:
            print(f"  ❌ Error: No se pudo conectar al servidor en {base_url}")
            print(f"     Verifica que el backend esté corriendo")
        except requests.exceptions.Timeout:
            print(f"  ❌ Error: Timeout esperando respuesta del servidor")
        except Exception as e:
            print(f"  ❌ Error inesperado: {e}")

        print()

    print("=" * 80)


def main():
    """Función principal"""
    import argparse

    parser = argparse.ArgumentParser(description="Probar endpoint de financiamiento-por-rangos")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="URL base del backend (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--token",
        help="Token de autenticación (Bearer token)"
    )

    args = parser.parse_args()

    test_endpoint(base_url=args.url, token=args.token)


if __name__ == "__main__":
    main()
