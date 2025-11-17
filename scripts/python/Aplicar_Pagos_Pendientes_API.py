"""
Script para aplicar pagos pendientes usando el endpoint API HTTP
Alternativa cuando hay problemas de encoding con conexión directa a BD
"""

import sys
import requests
import os
from typing import Optional

# Configurar encoding para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def obtener_pagos_pendientes(base_url: str, token: str) -> list:
    """Obtiene lista de pagos pendientes desde la API"""
    print("🔍 Obteniendo lista de pagos pendientes desde la API...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        # Obtener todos los pagos con prestamo_id
        response = requests.get(
            f"{base_url}/api/v1/pagos/",
            headers=headers,
            params={"per_page": 1000}  # Ajustar según necesidad
        )
        response.raise_for_status()

        data = response.json()
        pagos = data.get("items", [])

        # Filtrar solo los que tienen prestamo_id
        pagos_con_prestamo = [p for p in pagos if p.get("prestamo_id")]

        print(f"📊 Encontrados {len(pagos_con_prestamo)} pagos con prestamo_id")
        return pagos_con_prestamo

    except Exception as e:
        print(f"❌ Error obteniendo pagos: {str(e)}")
        return []


def aplicar_pago_via_api(base_url: str, token: str, pago_id: int) -> bool:
    """Aplica un pago usando el endpoint API"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{base_url}/api/v1/pagos/{pago_id}/aplicar-cuotas",
            headers=headers
        )
        response.raise_for_status()

        result = response.json()
        cuotas_completadas = result.get("cuotas_completadas", 0)

        print(f"✅ Pago ID {pago_id} aplicado. Cuotas completadas: {cuotas_completadas}")
        return True

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"⚠️ Pago ID {pago_id} no encontrado")
        elif e.response.status_code == 400:
            print(f"⚠️ Pago ID {pago_id} no tiene prestamo_id válido")
        else:
            print(f"❌ Error HTTP aplicando pago ID {pago_id}: {e.response.status_code}")
        return False
    except Exception as e:
        print(f"❌ Error aplicando pago ID {pago_id}: {str(e)}")
        return False


def main():
    """Función principal"""
    print("=" * 60)
    print("APLICAR PAGOS PENDIENTES A CUOTAS (VIA API)")
    print("=" * 60)

    # Configuración
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    token = os.getenv("API_TOKEN", "")

    if not token:
        print("❌ ERROR: Debes configurar API_TOKEN en variables de entorno")
        print("   Ejemplo: export API_TOKEN='tu_token_jwt'")
        return

    try:
        # Obtener pagos pendientes
        pagos = obtener_pagos_pendientes(base_url, token)

        if not pagos:
            print("✅ No hay pagos con prestamo_id para aplicar")
            return

        print(f"\n📋 Aplicando {len(pagos)} pagos...")
        print("-" * 60)

        aplicados = 0
        errores = 0

        for i, pago in enumerate(pagos, 1):
            if i % 100 == 0:
                print(f"🔄 Progreso: {i}/{len(pagos)} pagos procesados...")

            pago_id = pago.get("id")
            if not pago_id:
                continue

            if aplicar_pago_via_api(base_url, token, pago_id):
                aplicados += 1
            else:
                errores += 1

        print("-" * 60)
        print(f"✅ Resumen Final:")
        print(f"   - Aplicados exitosamente: {aplicados}")
        print(f"   - Errores: {errores}")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

