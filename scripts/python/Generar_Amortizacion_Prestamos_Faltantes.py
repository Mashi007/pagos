"""
Script para generar tablas de amortización para préstamos aprobados
que no tienen cuotas generadas pero tienen todos los datos necesarios.

Uso:
    python scripts/python/Generar_Amortizacion_Prestamos_Faltantes.py
"""

import os
import sys
from datetime import date
from decimal import Decimal

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.prestamo import Prestamo
from app.services.prestamo_amortizacion_service import generar_tabla_amortizacion


def create_safe_session():
    """Crea una sesión de base de datos manejando encoding issues"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError("DATABASE_URL no está definido en las variables de entorno")
    
    # Manejar encoding issues
    try:
        database_url = database_url.encode('utf-8').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        try:
            database_url = database_url.encode('latin1').decode('utf-8')
        except:
            pass
    
    # Crear engine con encoding explícito
    engine = create_engine(
        database_url,
        connect_args={
            "options": "-c client_encoding=UTF8"
        },
        echo=False
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def identificar_prestamos_sin_amortizacion(db):
    """Identifica préstamos aprobados sin tabla de amortización"""
    query = text("""
        SELECT p.id
        FROM prestamos p
        WHERE p.estado = 'APROBADO'
          AND p.fecha_base_calculo IS NOT NULL
          AND p.numero_cuotas > 0
          AND p.total_financiamiento > 0
          AND p.modalidad_pago IN ('MENSUAL', 'QUINCENAL', 'SEMANAL')
          AND NOT EXISTS (SELECT 1 FROM cuotas WHERE prestamo_id = p.id)
        ORDER BY p.id
    """)
    
    result = db.execute(query)
    prestamo_ids = [row[0] for row in result]
    return prestamo_ids


def generar_amortizacion_prestamo(prestamo_id: int, db) -> tuple[bool, str]:
    """
    Genera tabla de amortización para un préstamo específico
    
    Returns:
        (exito: bool, mensaje: str)
    """
    try:
        # Obtener préstamo
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        
        if not prestamo:
            return False, f"Préstamo {prestamo_id} no encontrado"
        
        if prestamo.estado != 'APROBADO':
            return False, f"Préstamo {prestamo_id} no está aprobado (estado: {prestamo.estado})"
        
        if not prestamo.fecha_base_calculo:
            return False, f"Préstamo {prestamo_id} no tiene fecha_base_calculo"
        
        if prestamo.numero_cuotas <= 0:
            return False, f"Préstamo {prestamo_id} tiene número de cuotas inválido: {prestamo.numero_cuotas}"
        
        if prestamo.total_financiamiento <= 0:
            return False, f"Préstamo {prestamo_id} tiene monto inválido: {prestamo.total_financiamiento}"
        
        if prestamo.modalidad_pago not in ['MENSUAL', 'QUINCENAL', 'SEMANAL']:
            return False, f"Préstamo {prestamo_id} tiene modalidad inválida: {prestamo.modalidad_pago}"
        
        # Verificar si ya tiene cuotas
        from app.models.amortizacion import Cuota
        cuotas_existentes = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id).count()
        
        if cuotas_existentes > 0:
            return False, f"Préstamo {prestamo_id} ya tiene {cuotas_existentes} cuotas generadas"
        
        # Generar tabla de amortización
        fecha_base = prestamo.fecha_base_calculo
        cuotas_generadas = generar_tabla_amortizacion(prestamo, fecha_base, db)
        
        return True, f"Préstamo {prestamo_id}: {len(cuotas_generadas)} cuotas generadas correctamente"
        
    except Exception as e:
        return False, f"Error en préstamo {prestamo_id}: {str(e)}"


def main():
    """Función principal"""
    print("=" * 70)
    print("GENERAR AMORTIZACIÓN PARA PRÉSTAMOS FALTANTES")
    print("=" * 70)
    print()
    
    # Crear sesión
    try:
        SessionLocal = create_safe_session()
        db = SessionLocal()
        print("✅ Conexión a base de datos establecida")
    except Exception as e:
        print(f"❌ Error conectando a base de datos: {str(e)}")
        return
    
    try:
        # Identificar préstamos sin amortización
        print("\n🔍 Identificando préstamos aprobados sin tabla de amortización...")
        prestamo_ids = identificar_prestamos_sin_amortizacion(db)
        
        if not prestamo_ids:
            print("\n✅ No hay préstamos aprobados sin tabla de amortización")
            return
        
        print(f"\n📊 Encontrados {len(prestamo_ids)} préstamos sin tabla de amortización")
        print(f"   IDs: {', '.join(map(str, prestamo_ids))}")
        
        # Confirmar antes de generar
        respuesta = input(f"\n¿Generar amortización para estos {len(prestamo_ids)} préstamos? (s/n): ")
        if respuesta.lower() != 's':
            print("\n❌ Operación cancelada")
            return
        
        # Generar amortización para cada préstamo
        print("\n🔄 Generando tablas de amortización...\n")
        
        exitosos = 0
        fallidos = 0
        
        for prestamo_id in prestamo_ids:
            exito, mensaje = generar_amortizacion_prestamo(prestamo_id, db)
            
            if exito:
                print(f"✅ {mensaje}")
                exitosos += 1
            else:
                print(f"❌ {mensaje}")
                fallidos += 1
        
        # Resumen final
        print("\n" + "=" * 70)
        print("RESUMEN DE GENERACIÓN")
        print("=" * 70)
        print(f"✅ Exitosos: {exitosos}")
        print(f"❌ Fallidos: {fallidos}")
        print(f"📊 Total procesados: {len(prestamo_ids)}")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print("\n✅ Sesión cerrada")


if __name__ == "__main__":
    main()

