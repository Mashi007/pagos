#!/usr/bin/env python3
"""
Script para corregir automáticamente errores de formato según Black
"""
import subprocess
import sys
import os

# Cambiar al directorio backend
os.chdir('backend')

# Archivos que Black necesita reformatear
files_to_format = [
    'app/api/v1/endpoints/analistas.py',
    'app/api/v1/endpoints/auth.py',
    'app/models/analista.py',
    'app/models/concesionario.py',
    'app/api/v1/endpoints/validadores.py',
    'app/services/validators_service.py'
]

try:
    # Ejecutar Black en los archivos
    result = subprocess.run(
        ['black', '--line-length', '127'] + files_to_format,
        capture_output=True,
        text=True,
        check=False
    )
    
    if result.returncode == 0:
        print("✅ Black ejecutado exitosamente")
        print(result.stdout)
    else:
        print("⚠️ Black terminó con código:", result.returncode)
        print(result.stdout)
        print(result.stderr)
        
except FileNotFoundError:
    print("❌ Black no está instalado. Instalando...")
    subprocess.run(['pip', 'install', 'black'], check=True)
    
    # Ejecutar Black nuevamente
    result = subprocess.run(
        ['black', '--line-length', '127'] + files_to_format,
        capture_output=True,
        text=True,
        check=False
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

print("\n✅ Formateo completado")

