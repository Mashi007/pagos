#!/usr/bin/env python3
"""
Script simple para verificar conexión de modelos ML a la base de datos
Ejecutar desde la raíz del proyecto: python verificar_modelos_ml.py
"""

import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Ejecutar el script de verificación
if __name__ == "__main__":
    from scripts.verificar_modelos_ml_bd import verificar_tablas_modelos_ml
    verificar_tablas_modelos_ml()

