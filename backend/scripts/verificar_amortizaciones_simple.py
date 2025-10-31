"""
Script simplificado para verificar acceso a amortizaciones
Usa consultas SQL directas para evitar problemas de codificación
"""

import os
import sys
from pathlib import Path

# Configurar encoding UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("[ERROR] psycopg2 no está instalado. Instala con: pip install psycopg2-binary")
    sys.exit(1)

def verificar_amortizaciones():
    """Verifica acceso usando conexión directa con psycopg2"""
    
    # Obtener DATABASE_URL de forma segura
    database_url = None
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            from app.core.config import settings
            database_url = settings.DATABASE_URL
    except:
        pass
    
    if not database_url:
        database_url = "postgresql://user:password@localhost/pagos_db"
    
    # Manejar posibles problemas de encoding en la URL
    if isinstance(database_url, bytes):
        try:
            database_url = database_url.decode('utf-8', errors='replace')
        except:
            database_url = database_url.decode('latin1', errors='replace')
    
    print("=" * 80)
    print("VERIFICACION DE ACCESO A AMORTIZACIONES")
    print("=" * 80)
    
    try:
        # Parsear la URL y usar parámetros de conexión separados
        import urllib.parse
        
        # Intentar parsear la URL de forma segura
        try:
            # Si la URL es bytes, decodificar primero
            if isinstance(database_url, bytes):
                try:
                    database_url_str = database_url.decode('latin1', errors='replace')
                except:
                    database_url_str = str(database_url, errors='replace')
            else:
                database_url_str = str(database_url)
            
            parsed = urllib.parse.urlparse(database_url_str)
            
            # Extraer parámetros de conexión
            host = parsed.hostname or 'localhost'
            port = parsed.port or 5432
            database = parsed.path.lstrip('/') or 'pagos_db'
            
            # Decodificar usuario y contraseña de forma segura
            user = None
            password = None
            if parsed.username:
                try:
                    user = urllib.parse.unquote(parsed.username, encoding='utf-8', errors='replace')
                except:
                    user = parsed.username
            if parsed.password:
                try:
                    password = urllib.parse.unquote(parsed.password, encoding='utf-8', errors='replace')
                except:
                    password = parsed.password
            
            # Conectar con parámetros separados
            conn_params = {
                'host': host,
                'port': port,
                'database': database,
                'client_encoding': 'UTF8'
            }
            if user:
                conn_params['user'] = user
            if password:
                conn_params['password'] = password
            
            conn = psycopg2.connect(**conn_params)
            
        except Exception as parse_error:
            # Si falla el parsing, intentar conexión directa con manejo de errores
            print(f"[ADVERTENCIA] Error parseando URL, intentando conexion directa: {parse_error}")
            try:
                # Intentar como string primero
                conn = psycopg2.connect(database_url, client_encoding='UTF8')
            except:
                # Si falla, usar valores por defecto
                print("[ADVERTENCIA] Usando valores por defecto para conexion")
                conn = psycopg2.connect(
                    host='localhost',
                    port=5432,
                    database='pagos_db',
                    client_encoding='UTF8'
                )
        conn.set_client_encoding('UTF8')
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"\n[OK] Conexion a base de datos establecida")
        
        # 1. Contar préstamos
        cur.execute("SELECT COUNT(*) as total FROM prestamos")
        total_prestamos = cur.fetchone()['total']
        print(f"[OK] Total de prestamos: {total_prestamos}")
        
        # 2. Contar cuotas
        cur.execute("SELECT COUNT(*) as total FROM cuotas")
        total_cuotas = cur.fetchone()['total']
        print(f"[OK] Total de cuotas/amortizaciones: {total_cuotas}")
        
        # 3. Préstamos con cuotas
        cur.execute("""
            SELECT COUNT(DISTINCT p.id) as total
            FROM prestamos p
            INNER JOIN cuotas c ON p.id = c.prestamo_id
        """)
        prestamos_con_cuotas = cur.fetchone()['total']
        print(f"[OK] Prestamos con cuotas generadas: {prestamos_con_cuotas}")
        
        # 4. Estadísticas por estado de préstamo
        print("\n" + "-" * 80)
        print("ESTADISTICAS POR ESTADO DE PRESTAMO")
        print("-" * 80)
        cur.execute("""
            SELECT 
                p.estado,
                COUNT(DISTINCT p.id) as total_prestamos,
                COUNT(c.id) as total_cuotas
            FROM prestamos p
            LEFT JOIN cuotas c ON p.id = c.prestamo_id
            GROUP BY p.estado
            ORDER BY p.estado
        """)
        for row in cur.fetchall():
            estado = row['estado'] or 'NULL'
            print(f"  {estado:15s}: {row['total_prestamos']:4d} prestamos, {row['total_cuotas']:6d} cuotas")
        
        # 5. Estadísticas por estado de cuotas
        print("\n" + "-" * 80)
        print("ESTADISTICAS POR ESTADO DE CUOTAS")
        print("-" * 80)
        cur.execute("""
            SELECT 
                estado,
                COUNT(*) as total,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM cuotas), 2) as porcentaje
            FROM cuotas
            GROUP BY estado
            ORDER BY estado
        """)
        for row in cur.fetchall():
            estado = row['estado'] or 'NULL'
            print(f"  {estado:15s}: {row['total']:6d} cuotas ({row['porcentaje']:5.1f}%)")
        
        # 6. Resumen de montos (préstamos aprobados)
        print("\n" + "-" * 80)
        print("RESUMEN DE MONTOS (SOLO PRESTAMOS APROBADOS)")
        print("-" * 80)
        cur.execute("""
            SELECT 
                COALESCE(SUM(p.total_financiamiento), 0) as total_financiamiento,
                COALESCE(SUM(c.total_pagado), 0) as total_pagado,
                COALESCE(SUM(c.capital_pendiente), 0) as capital_pendiente,
                COALESCE(SUM(c.interes_pendiente), 0) as interes_pendiente,
                COALESCE(SUM(c.monto_mora), 0) as mora_acumulada
            FROM prestamos p
            LEFT JOIN cuotas c ON p.id = c.prestamo_id
            WHERE p.estado = 'APROBADO'
        """)
        resumen = cur.fetchone()
        
        print(f"  Total financiamiento: ${float(resumen['total_financiamiento']):,.2f}")
        print(f"  Total pagado: ${float(resumen['total_pagado']):,.2f}")
        print(f"  Capital pendiente: ${float(resumen['capital_pendiente']):,.2f}")
        print(f"  Interes pendiente: ${float(resumen['interes_pendiente']):,.2f}")
        print(f"  Mora acumulada: ${float(resumen['mora_acumulada']):,.2f}")
        total_pendiente = resumen['capital_pendiente'] + resumen['interes_pendiente'] + resumen['mora_acumulada']
        print(f"  Total pendiente: ${float(total_pendiente):,.2f}")
        
        # 7. Detalle de primeros 5 préstamos aprobados con cuotas
        print("\n" + "-" * 80)
        print("DETALLE DE PRESTAMOS APROBADOS CON CUOTAS (Primeros 5)")
        print("-" * 80)
        cur.execute("""
            SELECT 
                p.id,
                p.cedula,
                p.nombres,
                p.total_financiamiento,
                COUNT(c.id) as total_cuotas,
                COUNT(CASE WHEN c.estado = 'PAGADO' THEN 1 END) as cuotas_pagadas,
                COUNT(CASE WHEN c.estado = 'PENDIENTE' THEN 1 END) as cuotas_pendientes,
                COUNT(CASE WHEN c.fecha_vencimiento < CURRENT_DATE AND c.estado != 'PAGADO' THEN 1 END) as cuotas_vencidas,
                COALESCE(SUM(c.capital_pendiente + c.interes_pendiente + c.monto_mora), 0) as saldo_pendiente
            FROM prestamos p
            INNER JOIN cuotas c ON p.id = c.prestamo_id
            WHERE p.estado = 'APROBADO'
            GROUP BY p.id, p.cedula, p.nombres, p.total_financiamiento
            ORDER BY p.fecha_registro DESC
            LIMIT 5
        """)
        
        for row in cur.fetchall():
            print(f"\n  Prestamo ID: {row['id']}")
            nombres = row['nombres'] or 'N/A'
            cedula = row['cedula'] or 'N/A'
            print(f"     Cliente: {nombres[:50]} (Cedula: {cedula})")
            print(f"     Monto: ${float(row['total_financiamiento']):,.2f}")
            print(f"     Cuotas: {row['total_cuotas']} total | {row['cuotas_pagadas']} pagadas | {row['cuotas_pendientes']} pendientes | {row['cuotas_vencidas']} vencidas")
            print(f"     Saldo pendiente: ${float(row['saldo_pendiente']):,.2f}")
        
        # 8. Verificación final
        print("\n" + "=" * 80)
        print("VERIFICACION COMPLETA")
        print("=" * 80)
        print(f"[OK] Acceso a tabla 'prestamos': OK ({total_prestamos} registros)")
        print(f"[OK] Acceso a tabla 'cuotas': OK ({total_cuotas} registros)")
        print(f"[OK] Relacion prestamos-cuotas: OK ({prestamos_con_cuotas} prestamos con cuotas)")
        print(f"[OK] Consultas SQL directas: OK")
        print("\n[EXITO] ACCESO COMPLETO A AMORTIZACIONES CONFIRMADO")
        print("=" * 80)
        
        cur.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n[ERROR] Error de base de datos: {e}")
        print(f"   Codigo: {e.pgcode if hasattr(e, 'pgcode') else 'N/A'}")
        print(f"   Mensaje: {e.pgerror if hasattr(e, 'pgerror') else str(e)}")
    except Exception as e:
        print(f"\n[ERROR] Error inesperado: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    verificar_amortizaciones()

