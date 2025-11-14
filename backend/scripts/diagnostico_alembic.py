#!/usr/bin/env python3
"""
Script de diagnóstico para problemas con Alembic
Verifica configuración, variables de entorno y conexión a la base de datos
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

def verificar_variables_entorno():
    """Verificar que las variables de entorno estén configuradas"""
    print("=" * 80)
    print("1. VERIFICANDO VARIABLES DE ENTORNO")
    print("=" * 80)
    
    # Verificar archivo .env
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        print(f"✅ Archivo .env encontrado: {env_file}")
        
        # Intentar cargar con python-dotenv
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print("✅ Variables de entorno cargadas desde .env")
        except ImportError:
            print("⚠️ python-dotenv no está instalado, leyendo manualmente...")
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
    else:
        print(f"⚠️ Archivo .env NO encontrado en: {env_file}")
    
    # Verificar DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Mostrar solo los primeros caracteres por seguridad
        masked_url = database_url[:30] + "..." if len(database_url) > 30 else database_url
        print(f"✅ DATABASE_URL configurada: {masked_url}")
        return True
    else:
        print("❌ DATABASE_URL NO está configurada")
        print("   Configura DATABASE_URL en el archivo .env o como variable de entorno")
        return False

def verificar_importaciones():
    """Verificar que las importaciones funcionen correctamente"""
    print("\n" + "=" * 80)
    print("2. VERIFICANDO IMPORTACIONES")
    print("=" * 80)
    
    try:
        print("📦 Importando app.core.config...")
        from app.core.config import settings
        print("✅ app.core.config importado correctamente")
        
        print("📦 Verificando DATABASE_URL en settings...")
        if hasattr(settings, 'DATABASE_URL'):
            db_url = settings.DATABASE_URL
            masked = db_url[:30] + "..." if len(db_url) > 30 else db_url
            print(f"✅ DATABASE_URL en settings: {masked}")
        else:
            print("❌ DATABASE_URL no está en settings")
            return False
            
    except Exception as e:
        print(f"❌ Error al importar app.core.config: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        print("📦 Importando app.db.base...")
        from app.db.base import Base
        print("✅ app.db.base importado correctamente")
    except Exception as e:
        print(f"❌ Error al importar app.db.base: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        print("📦 Importando app.models...")
        import app.models  # noqa: F401
        print("✅ app.models importado correctamente")
    except Exception as e:
        print(f"❌ Error al importar app.models: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def verificar_conexion_bd():
    """Verificar conexión a la base de datos"""
    print("\n" + "=" * 80)
    print("3. VERIFICANDO CONEXIÓN A BASE DE DATOS")
    print("=" * 80)
    
    try:
        from app.core.config import settings
        from sqlalchemy import create_engine, text
        
        database_url = settings.DATABASE_URL
        if not database_url:
            print("❌ DATABASE_URL no está configurada")
            return False
        
        print("🔌 Intentando conectar a la base de datos...")
        engine = create_engine(database_url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            print("✅ Conexión a la base de datos exitosa")
            return True
            
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        import traceback
        traceback.print_exc()
        return False

def verificar_alembic():
    """Verificar configuración de Alembic"""
    print("\n" + "=" * 80)
    print("4. VERIFICANDO CONFIGURACIÓN DE ALEMBIC")
    print("=" * 80)
    
    alembic_ini = Path(__file__).parent.parent / "alembic.ini"
    if alembic_ini.exists():
        print(f"✅ alembic.ini encontrado: {alembic_ini}")
    else:
        print(f"❌ alembic.ini NO encontrado en: {alembic_ini}")
        return False
    
    alembic_dir = Path(__file__).parent.parent / "alembic"
    if alembic_dir.exists():
        print(f"✅ Directorio alembic encontrado: {alembic_dir}")
    else:
        print(f"❌ Directorio alembic NO encontrado en: {alembic_dir}")
        return False
    
    versions_dir = alembic_dir / "versions"
    if versions_dir.exists():
        migrations = list(versions_dir.glob("*.py"))
        print(f"✅ Directorio versions encontrado con {len(migrations)} migraciones")
    else:
        print(f"❌ Directorio versions NO encontrado en: {versions_dir}")
        return False
    
    env_py = alembic_dir / "env.py"
    if env_py.exists():
        print(f"✅ env.py encontrado: {env_py}")
    else:
        print(f"❌ env.py NO encontrado en: {env_py}")
        return False
    
    return True

def main():
    """Ejecutar todas las verificaciones"""
    # Configurar encoding para Windows
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("\n" + "=" * 80)
    print("DIAGNOSTICO DE ALEMBIC")
    print("=" * 80)
    print(f"📁 Directorio de trabajo: {os.getcwd()}")
    print(f"📁 Directorio del script: {Path(__file__).parent.parent}")
    print()
    
    resultados = []
    
    # Ejecutar verificaciones
    resultados.append(("Variables de entorno", verificar_variables_entorno()))
    resultados.append(("Importaciones", verificar_importaciones()))
    resultados.append(("Conexión BD", verificar_conexion_bd()))
    resultados.append(("Configuración Alembic", verificar_alembic()))
    
    # Resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN")
    print("=" * 80)
    
    for nombre, resultado in resultados:
        estado = "✅ OK" if resultado else "❌ FALLO"
        print(f"  {estado} - {nombre}")
    
    todos_ok = all(resultado for _, resultado in resultados)
    
    if todos_ok:
        print("\n✅ Todas las verificaciones pasaron. Puedes ejecutar Alembic.")
        return 0
    else:
        print("\n❌ Algunas verificaciones fallaron. Revisa los errores arriba.")
        print("\n💡 Soluciones sugeridas:")
        print("   1. Crea un archivo .env en el directorio backend/")
        print("   2. Agrega DATABASE_URL=postgresql://usuario:contraseña@host:puerto/nombre_bd")
        print("   3. Instala python-dotenv: pip install python-dotenv")
        return 1

if __name__ == "__main__":
    sys.exit(main())

