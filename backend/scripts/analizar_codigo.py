#!/usr/bin/env python3
"""
Script para ejecutar análisis de código con flake8
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    # Cambiar al directorio del backend
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    
    print("=" * 80)
    print("EJECUTANDO ANÁLISIS DE CÓDIGO CON FLAKE8")
    print("=" * 80)
    print()
    
    # Ejecutar flake8
    try:
        result = subprocess.run(
            ["python", "-m", "flake8", "app", "--config=setup.cfg"],
            capture_output=True,
            text=True,
            cwd=backend_dir
        )
        
        if result.returncode == 0:
            print("✅ No se encontraron errores de código con flake8")
            return 0
        else:
            print("⚠️ SE ENCONTRARON PROBLEMAS DE CÓDIGO:")
            print("-" * 80)
            print(result.stdout)
            print(result.stderr)
            print("-" * 80)
            return result.returncode
            
    except FileNotFoundError:
        print("❌ ERROR: Python no encontrado en el PATH")
        print("   Por favor, instala Python o activa tu entorno virtual")
        return 1
    except Exception as e:
        print(f"❌ ERROR al ejecutar flake8: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

