#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar si las tablas de modelos ML están conectadas a la base de datos
Ejecutar: python backend/scripts/verificar_modelos_ml_bd.py
"""

import sys
import os
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Agregar el directorio backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect, text
from app.core.config import settings

def print_success(text):
    """Imprimir texto en verde"""
    try:
        print(f"\033[92m{text}\033[0m")
    except UnicodeEncodeError:
        print(f"[OK] {text}")

def print_error(text):
    """Imprimir texto en rojo"""
    try:
        print(f"\033[91m{text}\033[0m")
    except UnicodeEncodeError:
        print(f"[ERROR] {text}")

def print_warning(text):
    """Imprimir texto en amarillo"""
    try:
        print(f"\033[93m{text}\033[0m")
    except UnicodeEncodeError:
        print(f"[WARNING] {text}")

def print_info(text):
    """Imprimir texto en azul"""
    try:
        print(f"\033[94m{text}\033[0m")
    except UnicodeEncodeError:
        print(f"[INFO] {text}")

def verificar_tablas_modelos_ml():
    """Verificar si las tablas de modelos ML existen en la base de datos"""
    try:
        print_info("🔍 Verificando conexión a base de datos y tablas de modelos ML...")
        db_url_display = settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'BD local'
        print_info(f"📊 Conectando a: {db_url_display}")

        engine = create_engine(settings.DATABASE_URL)
        inspector = inspect(engine)

        tablas_requeridas = [
            ('modelos_riesgo', 'Modelos de Riesgo ML'),
            ('modelos_impago_cuotas', 'Modelos de Impago de Cuotas ML'),
        ]

        tablas_existentes = inspector.get_table_names()

        print("\n" + "=" * 70)
        print_info("📋 Estado de las tablas de modelos ML:")
        print("=" * 70)

        todas_existen = True
        for tabla, nombre in tablas_requeridas:
            existe = tabla in tablas_existentes
            if existe:
                print_success(f"  ✅ {tabla:<35} {nombre:<30} EXISTE")
            else:
                print_error(f"  ❌ {tabla:<35} {nombre:<30} NO EXISTE")
                todas_existen = False

        print("=" * 70)

        # Si las tablas existen, verificar estructura
        if todas_existen:
            print("\n" + "-" * 70)
            print_info("🔍 Verificando estructura de las tablas...")
            print("-" * 70)

            for tabla, nombre in tablas_requeridas:
                try:
                    columnas = inspector.get_columns(tabla)
                    indices = inspector.get_indexes(tabla)
                    print(f"\n  📊 {tabla} ({nombre}):")
                    print(f"     - Columnas: {len(columnas)}")
                    print(f"     - Índices: {len(indices)}")

                    # Verificar columnas críticas
                    nombres_columnas = [col['name'] for col in columnas]
                    columnas_criticas = ['id', 'nombre', 'algoritmo', 'activo', 'ruta_archivo']
                    faltantes = [col for col in columnas_criticas if col not in nombres_columnas]

                    if faltantes:
                        print_warning(f"     ⚠️  Columnas críticas faltantes: {', '.join(faltantes)}")
                    else:
                        print_success(f"     ✅ Todas las columnas críticas existen")

                    # Contar registros
                    try:
                        with engine.connect() as conn:
                            result = conn.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
                            total = result.scalar() or 0
                            print(f"     - Registros: {total}")
                    except Exception as e:
                        print_warning(f"     ⚠️  No se pudo contar registros: {e}")

                except Exception as e:
                    print_error(f"     ❌ Error verificando estructura: {e}")

        # Verificar servicios ML
        print("\n" + "-" * 70)
        print_info("🔍 Verificando servicios ML disponibles...")
        print("-" * 70)

        try:
            import sklearn
            print_success(f"  ✅ scikit-learn instalado: {sklearn.__version__}")
        except ImportError:
            print_error("  ❌ scikit-learn NO está instalado")
            print_warning("     Instala con: pip install scikit-learn==1.6.1")

        try:
            from app.services.ml_service import MLService
            print_success("  ✅ MLService disponible")
        except ImportError as e:
            print_warning(f"  ⚠️  MLService no disponible: {e}")

        try:
            from app.services.ml_impago_cuotas_service import MLImpagoCuotasService
            print_success("  ✅ MLImpagoCuotasService disponible")
        except ImportError as e:
            print_warning(f"  ⚠️  MLImpagoCuotasService no disponible: {e}")

        # Verificar estado de Alembic
        print("\n" + "-" * 70)
        print_info("🔄 Verificando estado de migraciones Alembic...")
        print("-" * 70)
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                version_actual = result.scalar()
                print(f"  Versión actual de Alembic: {version_actual}")

                # Verificar migraciones específicas
                migraciones_ml = [
                    '20251114_04_modelos_riesgo',
                    '20251114_05_modelos_impago_cuotas',
                ]

                print("\n  Migraciones de modelos ML requeridas:")
                for migracion in migraciones_ml:
                    print(f"    - {migracion}")

        except Exception as e:
            print_warning(f"  ⚠️  No se pudo verificar estado de Alembic: {e}")

        # Resumen final
        print("\n" + "=" * 70)
        if todas_existen:
            print_success("✅ RESULTADO: Todas las tablas de modelos ML están conectadas a la BD")
            print("\n💡 Próximos pasos:")
            print("   1. Verificar que scikit-learn esté instalado (ver arriba)")
            print("   2. Probar entrenar un modelo desde la interfaz")
            print("   3. Verificar que los endpoints funcionen correctamente")
        else:
            print_error("❌ RESULTADO: Algunas tablas de modelos ML NO están conectadas a la BD")
            print("\n💡 Solución:")
            print("   Ejecuta las migraciones:")
            print("   cd backend")
            print("   alembic upgrade head")
            print("\n   O verifica manualmente:")
            print("   python backend/scripts/verificar_modelos_ml_bd.py")
        print("=" * 70)

        return todas_existen

    except Exception as e:
        print_error(f"\n❌ ERROR: No se pudo conectar a la base de datos: {e}")
        print("\n💡 Verifica:")
        print("   1. Que DATABASE_URL esté configurado correctamente")
        print("   2. Que la base de datos esté accesible")
        print("   3. Que las credenciales sean correctas")
        print("   4. Que el archivo .env tenga la configuración correcta")
        import traceback
        print("\n📋 Detalles del error:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verificar_tablas_modelos_ml()

