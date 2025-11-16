#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script SIMPLE para verificar si los modelos ML están conectados a la BD
Ejecutar: python verificar_ml_simple.py
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

print("=" * 70)
print("VERIFICANDO CONEXION DE MODELOS ML A BASE DE DATOS")
print("=" * 70)

try:
    # Importar módulos necesarios
    from sqlalchemy import create_engine, inspect, text
    from urllib.parse import quote_plus, urlparse, urlunparse
    
    # Cargar .env si existe
    env_file = Path(__file__).parent / "backend" / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            # Si dotenv no está, leer manualmente
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
    
    # Leer DATABASE_URL directamente del entorno
    database_url_raw = os.getenv("DATABASE_URL")
    
    if not database_url_raw:
        print("\n[ERROR] DATABASE_URL no configurado")
        print("Configura DATABASE_URL en backend/.env o como variable de entorno")
        sys.exit(1)
    
    # Manejar encoding igual que session.py
    if isinstance(database_url_raw, bytes):
        try:
            database_url_raw = database_url_raw.decode("utf-8")
        except UnicodeDecodeError:
            database_url_raw = database_url_raw.decode("latin-1", errors="ignore")
    
    # Parsear y reconstruir URL
    if "@" in database_url_raw and "://" in database_url_raw:
        try:
            parsed = urlparse(database_url_raw)
            if parsed.password:
                netloc = f"{parsed.username}:{quote_plus(parsed.password, safe='')}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                parsed = parsed._replace(netloc=netloc)
                database_url = urlunparse(parsed)
            else:
                database_url = database_url_raw
        except Exception:
            database_url = database_url_raw
    else:
        database_url = database_url_raw
    
    # Conectar a BD
    print("\n[1] Conectando a base de datos...")
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        inspector = inspect(engine)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("    OK - Conexion exitosa")
    except Exception as e:
        print(f"    ERROR - No se pudo conectar: {str(e)[:100]}")
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
                print(f"    {tabla}: Error - {str(e)[:80]}")
    
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
        print("RESULTADO: FALTAN TABLAS")
        print("Ejecutar: cd backend && alembic upgrade head")
    print("=" * 70)
    
except ImportError as e:
    print(f"\nERROR: No se pudo importar modulos: {e}")
    print("Asegurate de estar en la raiz del proyecto")
    sys.exit(1)
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

