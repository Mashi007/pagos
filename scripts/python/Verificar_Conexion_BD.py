"""
Script para verificar la conexión a la base de datos y diagnosticar problemas
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    import logging

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    def verificar_conexion():
        """Verifica la conexión a la base de datos"""
        print("=" * 60)
        print("VERIFICACIÓN DE CONEXIÓN A BASE DE DATOS")
        print("=" * 60)
        
        # 1. Verificar configuración de DATABASE_URL
        print("\n1. Verificando configuración de DATABASE_URL...")
        database_url = settings.DATABASE_URL
        
        # Ocultar contraseña en el log
        if database_url:
            # Reemplazar contraseña por asteriscos
            safe_url = database_url
            if '@' in safe_url and ':' in safe_url.split('@')[0]:
                parts = safe_url.split('@')
                user_pass = parts[0]
                if ':' in user_pass:
                    user = user_pass.split(':')[0]
                    safe_url = f"{user}:***@{parts[1]}" if len(parts) > 1 else user_pass
            print(f"   ✅ DATABASE_URL configurada: {safe_url}")
        else:
            print("   ❌ DATABASE_URL NO configurada")
            return False
        
        # 2. Intentar crear engine
        print("\n2. Creando engine de SQLAlchemy...")
        try:
            engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False,
                connect_args={"client_encoding": "UTF8"} if database_url.startswith("postgresql") else {}
            )
            print("   ✅ Engine creado exitosamente")
        except Exception as e:
            print(f"   ❌ Error creando engine: {type(e).__name__}: {str(e)}")
            return False
        
        # 3. Intentar conectar y ejecutar query simple
        print("\n3. Ejecutando prueba de conexión...")
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                if row and row[0] == 1:
                    print("   ✅ Conexión exitosa - Query de prueba OK")
                else:
                    print("   ⚠️  Conexión establecida pero query retornó resultado inesperado")
        except Exception as e:
            print(f"   ❌ Error ejecutando query de prueba: {type(e).__name__}: {str(e)}")
            return False
        
        # 4. Verificar tablas principales
        print("\n4. Verificando existencia de tablas principales...")
        tablas_requeridas = ['pagos', 'prestamos', 'cuotas', 'clientes']
        tablas_encontradas = []
        tablas_faltantes = []
        
        try:
            with engine.connect() as conn:
                # Obtener lista de tablas
                if database_url.startswith("postgresql"):
                    query_tablas = text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                    """)
                else:
                    query_tablas = text("SELECT name FROM sqlite_master WHERE type='table'")
                
                result = conn.execute(query_tablas)
                tablas_existentes = [row[0].lower() for row in result.fetchall()]
                
                for tabla in tablas_requeridas:
                    if tabla in tablas_existentes:
                        tablas_encontradas.append(tabla)
                        print(f"   ✅ Tabla '{tabla}' existe")
                    else:
                        tablas_faltantes.append(tabla)
                        print(f"   ❌ Tabla '{tabla}' NO existe")
        
        except Exception as e:
            print(f"   ⚠️  Error verificando tablas: {type(e).__name__}: {str(e)}")
        
        # 5. Verificar datos en tablas
        if not tablas_faltantes:
            print("\n5. Verificando datos en tablas...")
            try:
                with engine.connect() as conn:
                    # Contar registros en tablas principales
                    tablas_verificar = ['pagos', 'prestamos', 'cuotas']
                    for tabla in tablas_verificar:
                        try:
                            if tabla in tablas_encontradas:
                                query_count = text(f"SELECT COUNT(*) FROM {tabla}")
                                result = conn.execute(query_count)
                                count = result.scalar()
                                print(f"   ✅ Tabla '{tabla}': {count} registros")
                        except Exception as e:
                            print(f"   ⚠️  Error contando registros en '{tabla}': {str(e)}")
            except Exception as e:
                print(f"   ⚠️  Error verificando datos: {type(e).__name__}: {str(e)}")
        
        # 6. Crear sesión y verificar modelo Pago
        print("\n6. Verificando acceso a modelos ORM...")
        try:
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()
            
            try:
                from app.models.pago import Pago
                from sqlalchemy import func
                
                total_pagos = db.query(func.count(Pago.id)).scalar()
                print(f"   ✅ Modelo Pago accesible - Total pagos: {total_pagos}")
                
            except Exception as e:
                print(f"   ⚠️  Error accediendo modelo Pago: {type(e).__name__}: {str(e)}")
            finally:
                db.close()
        
        except Exception as e:
            print(f"   ⚠️  Error creando sesión: {type(e).__name__}: {str(e)}")
        
        print("\n" + "=" * 60)
        print("VERIFICACIÓN COMPLETADA")
        print("=" * 60)
        
        if tablas_faltantes:
            print(f"\n⚠️  ADVERTENCIA: Faltan {len(tablas_faltantes)} tablas requeridas")
            print("   Esto podría causar errores 500 en los endpoints")
        else:
            print("\n✅ Todas las verificaciones básicas pasaron correctamente")
        
        return len(tablas_faltantes) == 0

    if __name__ == "__main__":
        success = verificar_conexion()
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de ejecutar este script desde la raíz del proyecto")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

