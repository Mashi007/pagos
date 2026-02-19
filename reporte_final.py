import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from app.core.config import settings
from app.core.database import SessionLocal
from sqlalchemy import text
from datetime import datetime

print()
print('=' * 80)
print(' REPORTE FINAL: CLIENTES INACTIVOS Y PRESTAMOS APROBADOS '.center(80))
print('=' * 80)
print()
print(f'Fecha del reporte: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print(f'Base de datos: PostgreSQL')
print()

db = SessionLocal()
try:
    # Query 1: Total clientes inactivos
    query1 = text("SELECT COUNT(*) as total_clientes_inactivos FROM clientes WHERE estado = 'INACTIVO'")
    result1 = db.execute(query1).fetchone()
    
    # Query 2: Clientes inactivos CON prestamos aprobados
    query2 = text("SELECT COUNT(DISTINCT c.id) as clientes_inactivos_con_prestamos_aprobados FROM clientes c JOIN prestamos p ON c.id = p.cliente_id WHERE c.estado = 'INACTIVO' AND p.estado = 'APROBADO'")
    result2 = db.execute(query2).fetchone()
    
    # Query 3: Clientes inactivos SIN prestamos aprobados
    query3 = text("SELECT COUNT(DISTINCT c.id) as clientes_inactivos_sin_prestamos_aprobados FROM clientes c WHERE c.estado = 'INACTIVO' AND NOT EXISTS (SELECT 1 FROM prestamos p WHERE p.cliente_id = c.id AND p.estado = 'APROBADO')")
    result3 = db.execute(query3).fetchone()
    
    total_inactivos = result1[0]
    con_aprobados = result2[0]
    sin_aprobados = result3[0]
    
    print('RESULTADOS DE CONSULTAS SQL')
    print('-' * 80)
    print(f'1. Total clientes con estado = INACTIVO: {total_inactivos}')
    print(f'2. Clientes INACTIVOS con prestamos APROBADOS: {con_aprobados}')
    print(f'3. Clientes INACTIVOS SIN prestamos APROBADOS: {sin_aprobados}')
    print()
    
    print('VALIDACION')
    print('-' * 80)
    print(f'Total (con + sin) = {con_aprobados} + {sin_aprobados} = {con_aprobados + sin_aprobados} (Esperado: {total_inactivos})')
    
    if con_aprobados + sin_aprobados == total_inactivos:
        print('VALIDACION: OK - Las sumas coinciden perfectamente')
    else:
        print('VALIDACION: ERROR - Las sumas no coinciden')
    
    print()
    print('LISTADO DE CLIENTES INACTIVOS')
    print('-' * 80)
    print('%-5s %-15s %-30s %-12s %s' % ('ID', 'Cedula', 'Nombre', 'Prestamos', 'Total Financiamiento'))
    print('-' * 80)
    
    query_detail = text("""
        SELECT 
            c.id,
            c.cedula,
            c.nombres,
            COUNT(DISTINCT p.id) as cantidad_prestamos_aprobados,
            SUM(p.total_financiamiento) as total_financiamiento
        FROM clientes c
        LEFT JOIN prestamos p ON c.id = p.cliente_id AND p.estado = 'APROBADO'
        WHERE c.estado = 'INACTIVO'
        GROUP BY c.id, c.cedula, c.nombres
        ORDER BY c.id
    """)
    
    details = db.execute(query_detail).fetchall()
    
    for row in details:
        client_id, cedula, nombres, cant_prestamos, total_fin = row
        total_fin_str = f'{total_fin:.2f}' if total_fin else '0.00'
        print('%-5d %-15s %-30s %-12d %s' % (client_id, cedula, nombres[:28], cant_prestamos, total_fin_str))
    
    print('-' * 80)
    print()
    
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
