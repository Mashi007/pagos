# -*- coding: utf-8 -*-
"""
Script para verificar columnas en tabla prestamos
"""
import os
import sys

# Cambiar a directorio del backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from app.core.database import engine
    from sqlalchemy import inspect, text
    
    inspector = inspect(engine)
    
    # Obtener columnas de la tabla prestamos
    columnas = inspector.get_columns('prestamos')
    
    print("=" * 80)
    print("COLUMNAS DE LA TABLA: prestamos")
    print("=" * 80)
    print()
    
    for idx, col in enumerate(columnas, 1):
        print(f"{idx:2d}. {col['name']:30s} | {col['type']}")
    
    print()
    print("=" * 80)
    
    # Buscar columna que contenga "referencia"
    print("\nBuscando columnas con 'referencia'...")
    referencia_cols = [col['name'] for col in columnas if 'referencia' in col['name'].lower()]
    
    if referencia_cols:
        print(f"Encontradas: {referencia_cols}")
    else:
        print("No encontradas columnas con 'referencia'")
    
    # Buscar columna que contenga "interno"
    print("\nBuscando columnas con 'interno'...")
    interno_cols = [col['name'] for col in columnas if 'interno' in col['name'].lower()]
    
    if interno_cols:
        print(f"Encontradas: {interno_cols}")
    else:
        print("No encontradas columnas con 'interno'")
    
    print()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
