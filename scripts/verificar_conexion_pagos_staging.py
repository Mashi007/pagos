#!/usr/bin/env python3
"""
Script de verificación de conexión a pagos_staging
Verifica que la tabla existe, la conexión funciona y hay datos
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.models.pago_staging import PagoStaging

def verificar_conexion():
    """Verifica la conexión a la base de datos y la tabla pagos_staging"""
    
    # Obtener DATABASE_URL del entorno
    database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/pagos_db")
    
    print("=" * 70)
    print("VERIFICACIÓN DE CONEXIÓN A pagos_staging")
    print("=" * 70)
    print(f"\n📊 DATABASE_URL: {database_url.split('@')[1] if '@' in database_url else database_url}")
    
    try:
        # Crear engine
        engine = create_engine(database_url, pool_pre_ping=True)
        
        # Crear sesión
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        print("\n✅ Conexión a la base de datos: OK")
        
        # Verificar que la tabla existe
        inspector = inspect(engine)
        tablas = inspector.get_table_names()
        
        if "pagos_staging" in tablas:
            print("✅ Tabla 'pagos_staging' existe en la base de datos")
        else:
            print("❌ Tabla 'pagos_staging' NO existe en la base de datos")
            print(f"   Tablas disponibles: {', '.join(tablas[:10])}...")
            db.close()
            return False
        
        # Verificar estructura de la tabla
        columnas = inspector.get_columns("pagos_staging")
        print(f"\n📋 Estructura de la tabla 'pagos_staging':")
        print(f"   Total de columnas: {len(columnas)}")
        columnas_importantes = ['id', 'cedula_cliente', 'cedula', 'prestamo_id', 
                                'fecha_pago', 'monto_pagado', 'estado', 'conciliado']
        for col in columnas_importantes:
            if any(c['name'] == col for c in columnas):
                print(f"   ✅ {col}")
            else:
                print(f"   ⚠️  {col} (no encontrada)")
        
        # Verificar que el modelo puede hacer consultas
        try:
            total_registros = db.query(PagoStaging).count()
            print(f"\n📊 Total de registros en pagos_staging: {total_registros}")
            
            if total_registros > 0:
                # Obtener un registro de ejemplo
                ejemplo = db.query(PagoStaging).first()
                print(f"\n📝 Ejemplo de registro:")
                print(f"   ID: {ejemplo.id}")
                print(f"   Cédula: {ejemplo.cedula_cliente or ejemplo.cedula or 'N/A'}")
                print(f"   Monto: {ejemplo.monto_pagado or 'N/A'}")
                print(f"   Fecha pago: {ejemplo.fecha_pago or 'N/A'}")
                print(f"   Estado: {ejemplo.estado or 'N/A'}")
                print(f"   Conciliado: {ejemplo.conciliado}")
            else:
                print("\n⚠️  La tabla está vacía (esto puede ser normal si no hay datos)")
            
        except Exception as e:
            print(f"\n❌ Error al consultar pagos_staging: {e}")
            db.close()
            return False
        
        # Verificar consultas con SQL directo
        try:
            resultado = db.execute(text("SELECT COUNT(*) FROM pagos_staging"))
            count_sql = resultado.scalar()
            print(f"\n✅ Consulta SQL directa: OK ({count_sql} registros)")
        except Exception as e:
            print(f"\n❌ Error en consulta SQL directa: {e}")
            db.close()
            return False
        
        # Verificar esquema
        try:
            resultado = db.execute(text("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_name = 'pagos_staging'
            """))
            esquemas = resultado.fetchall()
            if esquemas:
                print(f"\n📁 Esquema de la tabla:")
                for schema, table in esquemas:
                    print(f"   {schema}.{table}")
            else:
                print("\n⚠️  No se pudo determinar el esquema")
        except Exception as e:
            print(f"\n⚠️  Error al verificar esquema: {e}")
        
        db.close()
        
        print("\n" + "=" * 70)
        print("✅ VERIFICACIÓN COMPLETA: Todo está correcto")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR DE CONEXIÓN: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        import traceback
        print(f"\n   Traceback completo:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verificar_conexion()
    sys.exit(0 if success else 1)

