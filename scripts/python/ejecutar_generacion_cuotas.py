"""
Script wrapper para ejecutar la generación de cuotas con informes periódicos
Ejecutar desde la raíz del proyecto: python scripts/python/ejecutar_generacion_cuotas.py
"""

import sys
import os

# Agregar el directorio backend al path para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from generar_cuotas_prestamos_pendientes import main

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generar cuotas para préstamos pendientes')
    parser.add_argument('--execute', action='store_true', help='Ejecutar cambios reales (sin dry-run)')
    parser.add_argument('--limit', type=int, help='Límite de préstamos a procesar')
    
    args = parser.parse_args()
    
    dry_run = not args.execute
    limit = args.limit
    
    print("\n" + "=" * 80)
    print("🚀 INICIANDO GENERACIÓN DE CUOTAS PARA PRÉSTAMOS PENDIENTES")
    print("=" * 80)
    print(f"Modo: {'DRY RUN (sin cambios)' if dry_run else 'EJECUCIÓN REAL'}")
    if limit:
        print(f"Límite: {limit} préstamos")
    print("=" * 80 + "\n")
    
    main(dry_run=dry_run, limit=limit)
