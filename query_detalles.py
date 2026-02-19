import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from app.core.config import settings
from app.core.database import SessionLocal
from sqlalchemy import text

print()
print('=' * 70)
print('DETALLES DE CLIENTES INACTIVOS CON PRÃ‰STAMOS APROBADOS')
print('=' * 70)
print()

db = SessionLocal()
try:
    # Detalles de clientes inactivos
    query = text("""
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
    
    results = db.execute(query).fetchall()
    
    print(f'{"ID":<5} {"CÃ©dula":<15} {"Nombre":<30} {"PrÃ©stamos":<12} {"Total Financiamiento":<20}')
    print('-' * 82)
    
    for row in results:
        client_id, cedula, nombres, cant_prestamos, total_fin = row
        total_fin_str = f'{total_fin:.2f}' if total_fin else '0.00'
        print(f'{client_id:<5} {cedula:<15} {nombres[:28]:<30} {cant_prestamos:<12} {total_fin_str:<20}')
    
    print()
    print('=' * 70)
    print()
    
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
