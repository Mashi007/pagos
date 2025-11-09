#!/usr/bin/env python
"""
Script principal para verificar y ajustar el dashboard de "Distribución de Financiamiento por Rangos"
Ejecuta todos los diagnósticos y ajustes necesarios
"""

import sys
import os
import subprocess
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def ejecutar_script(script_name: str, args: list = None):
    """Ejecuta un script de Python y muestra su salida"""
    script_path = Path(__file__).parent / script_name
    if not script_path.exists():
        print(f"❌ Script no encontrado: {script_path}")
        return False
    
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error ejecutando {script_name}: {e}")
        return False


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verificar y ajustar el dashboard de Financiamiento por Rangos"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Ejecutar ajustes (por defecto solo diagnostica)"
    )
    parser.add_argument(
        "--skip-diagnostico",
        action="store_true",
        help="Saltar el diagnóstico inicial"
    )
    parser.add_argument(
        "--skip-ajustes",
        action="store_true",
        help="Saltar los ajustes de fechas"
    )
    parser.add_argument(
        "--skip-test",
        action="store_true",
        help="Saltar la prueba del endpoint"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🔍 VERIFICACIÓN Y AJUSTE DEL DASHBOARD")
    print("=" * 80)
    print()
    
    # Paso 1: Diagnóstico
    if not args.skip_diagnostico:
        print("📋 PASO 1: Ejecutando diagnóstico...")
        print()
        ejecutar_script("diagnostico_dashboard_rangos.py")
        print()
        print("=" * 80)
        print()
    
    # Paso 2: Ajustes (si se solicita)
    if not args.skip_ajustes:
        if args.execute:
            print("🔧 PASO 2: Ejecutando ajustes de fechas...")
            print()
            ejecutar_script("ajustar_fechas_prestamos.py", ["--execute"])
        else:
            print("🔧 PASO 2: Revisando ajustes necesarios (modo dry-run)...")
            print()
            ejecutar_script("ajustar_fechas_prestamos.py")
            print()
            print("💡 Para ejecutar los ajustes, usa: --execute")
        print()
        print("=" * 80)
        print()
    
    # Paso 3: Prueba del endpoint
    if not args.skip_test:
        print("🧪 PASO 3: Probando endpoint...")
        print()
        print("⚠️  Nota: Asegúrate de que el backend esté corriendo")
        print()
        ejecutar_script("test_endpoint_rangos.py")
        print()
        print("=" * 80)
        print()
    
    print("✅ Verificación completada")
    print()
    print("📝 Próximos pasos:")
    print("   1. Revisar los resultados del diagnóstico")
    print("   2. Si hay problemas, ejecutar ajustes con --execute")
    print("   3. Verificar que el dashboard muestre los datos correctamente")
    print()


if __name__ == "__main__":
    main()

