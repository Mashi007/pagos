"""
Script para verificar acceso a amortizaciones de todos los préstamos
"""

import os
import sys
from pathlib import Path
from datetime import date
from decimal import Decimal

# Configurar encoding UTF-8 para evitar errores de codificación
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.models.prestamo import Prestamo
from app.models.amortizacion import Cuota
from sqlalchemy import func, desc, text, create_engine  # type: ignore
from sqlalchemy.orm import sessionmaker  # type: ignore

def safe_str(value):
    """Convierte un valor a string de forma segura manejando errores de codificación"""
    if value is None:
        return "N/A"
    try:
        if isinstance(value, (bytes, bytearray)):
            # Intentar decodificar como UTF-8, luego latin1 como fallback
            try:
                return value.decode('utf-8', errors='replace')
            except:
                return value.decode('latin1', errors='replace')
        if isinstance(value, str):
            # Si ya es string, verificar que es UTF-8 válido
            value.encode('utf-8')
            return value
        return str(value)
    except (UnicodeDecodeError, UnicodeEncodeError):
        try:
            return str(value).encode('latin1', errors='replace').decode('latin1')
        except:
            return str(value).encode('ascii', errors='replace').decode('ascii')

def create_safe_engine():
    """Crea un engine con manejo robusto de codificación"""
    import os
    import urllib.parse
    
    # Obtener DATABASE_URL de forma segura
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            database_url = getattr(settings, 'DATABASE_URL', None)
        if not database_url:
            database_url = "postgresql://user:password@localhost/pagos_db"
    except:
        database_url = "postgresql://user:password@localhost/pagos_db"
    
    # Intentar reparar la URL si tiene problemas de encoding
    try:
        # Si la URL tiene bytes inválidos, intentar decodificar como latin1
        if isinstance(database_url, bytes):
            database_url = database_url.decode('latin1', errors='replace')
        
        # Parsear y reconstruir la URL de forma segura
        parsed = urllib.parse.urlparse(database_url)
        
        # Reconstruir la URL asegurando encoding correcto
        if parsed.password:
            # Codificar componentes de forma segura
            safe_password = urllib.parse.quote(parsed.password, safe='')
            safe_user = urllib.parse.quote(parsed.username or '', safe='')
            safe_netloc = f"{safe_user}:{safe_password}@{parsed.hostname}"
            if parsed.port:
                safe_netloc += f":{parsed.port}"
            
            database_url = urllib.parse.urlunparse((
                parsed.scheme,
                safe_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
    except Exception as e:
        print(f"[ADVERTENCIA] Error procesando DATABASE_URL: {e}")
        # Usar URL por defecto si hay problemas
        database_url = "postgresql://user:password@localhost/pagos_db"
    
    # Configurar psycopg2 para manejar encoding
    connect_args = {}
    if database_url.startswith('postgresql'):
        connect_args = {
            'client_encoding': 'UTF8',
        }
    
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False,
        connect_args=connect_args,
    )


def verificar_amortizaciones():
    """Verifica acceso a todas las amortizaciones"""
    # Crear engine y session de forma segura
    try:
        safe_engine = create_safe_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=safe_engine)
        db = SessionLocal()
    except Exception as e:
        print(f"[ERROR] No se pudo conectar a la base de datos: {e}")
        print(f"Verifica que DATABASE_URL este correctamente configurada")
        return
    
    try:
        print("=" * 80)
        print("VERIFICACION DE ACCESO A AMORTIZACIONES")
        print("=" * 80)
        
        # Configurar encoding en la conexión
        try:
            db.execute(text("SET client_encoding TO 'UTF8'"))
            db.commit()
        except Exception as e:
            print(f"[ADVERTENCIA] No se pudo configurar UTF-8 en conexion: {e}")
        
        # Obtener nombre de BD de forma segura
        try:
            db_name = settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL
            db_name_safe = safe_str(db_name) if db_name else "N/A"
        except:
            db_name_safe = "localhost/pagos_db"
        
        print(f"\nBase de datos: {db_name_safe}")
        print()
        
        # 1. Contar total de préstamos
        total_prestamos = db.query(Prestamo).count()
        print(f"[OK] Total de prestamos en BD: {total_prestamos}")
        
        # 2. Contar total de cuotas/amortizaciones
        total_cuotas = db.query(Cuota).count()
        print(f"[OK] Total de cuotas/amortizaciones en BD: {total_cuotas}")
        
        # 3. Préstamos con cuotas
        prestamos_con_cuotas = (
            db.query(Prestamo.id)
            .join(Cuota, Prestamo.id == Cuota.prestamo_id)
            .distinct()
            .count()
        )
        print(f"[OK] Prestamos con cuotas generadas: {prestamos_con_cuotas}")
        
        # 4. Préstamos sin cuotas
        prestamos_sin_cuotas = total_prestamos - prestamos_con_cuotas
        print(f"[ADVERTENCIA] Prestamos sin cuotas: {prestamos_sin_cuotas}")
        
        # 5. Estadísticas por estado de préstamo
        print("\n" + "-" * 80)
        print("ESTADÍSTICAS POR ESTADO DE PRÉSTAMO")
        print("-" * 80)
        
        prestamos_por_estado = (
            db.query(Prestamo.estado, func.count(Prestamo.id))
            .group_by(Prestamo.estado)
            .all()
        )
        
        for estado, count in prestamos_por_estado:
            cuotas_estado = (
                db.query(func.count(Cuota.id))
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .filter(Prestamo.estado == estado)
                .scalar() or 0
            )
            estado_str = safe_str(estado) if estado else "N/A"
            print(f"  {estado_str:15s}: {count:4d} prestamos, {cuotas_estado:6d} cuotas")
        
        # 6. Estadísticas por estado de cuotas
        print("\n" + "-" * 80)
        print("ESTADÍSTICAS POR ESTADO DE CUOTAS")
        print("-" * 80)
        
        cuotas_por_estado = (
            db.query(Cuota.estado, func.count(Cuota.id))
            .group_by(Cuota.estado)
            .all()
        )
        
        for estado, count in cuotas_por_estado:
            porcentaje = (count / total_cuotas * 100) if total_cuotas > 0 else 0
            estado_str = safe_str(estado) if estado else "N/A"
            print(f"  {estado_str:15s}: {count:6d} cuotas ({porcentaje:5.1f}%)")
        
        # 7. Detalle de préstamos aprobados con sus cuotas
        print("\n" + "-" * 80)
        print("DETALLE DE PRÉSTAMOS APROBADOS CON CUOTAS (Primeros 10)")
        print("-" * 80)
        
        prestamos_aprobados = (
            db.query(Prestamo)
            .filter(Prestamo.estado == "APROBADO")
            .join(Cuota, Prestamo.id == Cuota.prestamo_id)
            .distinct()
            .order_by(desc(Prestamo.fecha_registro))
            .limit(10)
            .all()
        )
        
        for prestamo in prestamos_aprobados:
            cuotas_prestamo = db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).all()
            
            total_cuotas_p = len(cuotas_prestamo)
            cuotas_pagadas = len([c for c in cuotas_prestamo if c.estado == "PAGADO"])
            cuotas_pendientes = len([c for c in cuotas_prestamo if c.estado == "PENDIENTE"])
            cuotas_vencidas = len([c for c in cuotas_prestamo if c.esta_vencida])
            
            saldo_total = sum(
                c.capital_pendiente + c.interes_pendiente + c.monto_mora
                for c in cuotas_prestamo
            )
            
            print(f"\n  Prestamo ID: {prestamo.id}")
            nombres_safe = safe_str(prestamo.nombres) if prestamo.nombres else "N/A"
            cedula_safe = safe_str(prestamo.cedula) if prestamo.cedula else "N/A"
            print(f"     Cliente: {nombres_safe} (Cedula: {cedula_safe})")
            print(f"     Monto: ${float(prestamo.total_financiamiento):,.2f}")
            print(f"     Cuotas: {total_cuotas_p} total | {cuotas_pagadas} pagadas | {cuotas_pendientes} pendientes | {cuotas_vencidas} vencidas")
            print(f"     Saldo pendiente: ${float(saldo_total):,.2f}")
        
        # 8. Resumen de montos
        print("\n" + "-" * 80)
        print("RESUMEN DE MONTOS")
        print("-" * 80)
        
        total_financiamiento = (
            db.query(func.sum(Prestamo.total_financiamiento))
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or Decimal("0")
        )
        
        total_capital_pendiente = (
            db.query(func.sum(Cuota.capital_pendiente))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or Decimal("0")
        )
        
        total_interes_pendiente = (
            db.query(func.sum(Cuota.interes_pendiente))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or Decimal("0")
        )
        
        total_mora = (
            db.query(func.sum(Cuota.monto_mora))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or Decimal("0")
        )
        
        total_pagado = (
            db.query(func.sum(Cuota.total_pagado))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or Decimal("0")
        )
        
        print(f"  Total financiamiento (APROBADOS): ${float(total_financiamiento):,.2f}")
        print(f"  Total pagado: ${float(total_pagado):,.2f}")
        print(f"  Capital pendiente: ${float(total_capital_pendiente):,.2f}")
        print(f"  Interés pendiente: ${float(total_interes_pendiente):,.2f}")
        print(f"  Mora acumulada: ${float(total_mora):,.2f}")
        print(f"  Total pendiente: ${float(total_capital_pendiente + total_interes_pendiente + total_mora):,.2f}")
        
        # 9. Verificación de acceso completo
        print("\n" + "=" * 80)
        print("VERIFICACION COMPLETA")
        print("=" * 80)
        print(f"[OK] Acceso a tabla 'prestamos': OK ({total_prestamos} registros)")
        print(f"[OK] Acceso a tabla 'cuotas': OK ({total_cuotas} registros)")
        print(f"[OK] Relacion prestamos-cuotas: OK ({prestamos_con_cuotas} prestamos con cuotas)")
        print(f"[OK] Calculos y agregaciones: OK")
        print("\n[EXITO] ACCESO COMPLETO A AMORTIZACIONES CONFIRMADO")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] ERROR al acceder a las amortizaciones:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    verificar_amortizaciones()

