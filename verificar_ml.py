#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple para verificar si los modelos ML están conectados a la BD
Ejecutar: python verificar_ml.py
"""

import sys
import os
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    try:
        os.system('chcp 65001 >nul 2>&1')
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

try:
    # Importar directamente desde session para usar la misma configuración
    from app.db.session import engine

    print("=" * 70)
    print("VERIFICANDO CONEXION DE MODELOS ML A BASE DE DATOS")
    print("=" * 70)

    # Conectar a BD
    print("\n[1] Conectando a base de datos...")
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        # Test de conexión
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("    OK - Conexion exitosa")
    except Exception as e:
        print(f"    ERROR - No se pudo conectar: {str(e)[:100]}")
        print("    Verifica que DATABASE_URL este configurado en .env")
        sys.exit(1)

    # Verificar tablas
    print("\n[2] Verificando tablas...")
    tablas_existentes = inspector.get_table_names()

    tablas_requeridas = {
        'modelos_riesgo': 'Modelos de Riesgo ML',
        'modelos_impago_cuotas': 'Modelos de Impago de Cuotas ML'
    }

    todas_existen = True
    for tabla, nombre in tablas_requeridas.items():
        existe = tabla in tablas_existentes
        estado = "EXISTE" if existe else "NO EXISTE"
        simbolo = "[OK]" if existe else "[ERROR]"
        print(f"    {simbolo} {tabla:<35} - {estado}")
        if not existe:
            todas_existen = False

    # Si existen, mostrar detalles
    if todas_existen:
        print("\n[3] Detalles de las tablas:")
        for tabla, nombre in tablas_requeridas.items():
            try:
                columnas = inspector.get_columns(tabla)
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
                    total = result.scalar() or 0
                print(f"    {tabla}: {len(columnas)} columnas, {total} registros")
            except Exception as e:
                print(f"    {tabla}: Error - {e}")

    # Verificar scikit-learn
    print("\n[4] Verificando scikit-learn...")
    try:
        import sklearn
        print(f"    OK - scikit-learn {sklearn.__version__} instalado")
    except ImportError:
        print("    ERROR - scikit-learn NO instalado")
        print("    Instalar con: pip install scikit-learn==1.6.1")

    # Resumen
    print("\n" + "=" * 70)
    if todas_existen:
        print("RESULTADO: MODELOS ML CONECTADOS A BD")
    else:
        print("RESULTADO: FALTAN TABLAS - Ejecutar: cd backend && alembic upgrade head")
    print("=" * 70)

except ImportError as e:
    print(f"ERROR: No se pudo importar modulos: {e}")
    print("Asegurate de estar en la raiz del proyecto")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

