import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from app.core.config import settings
from app.core.database import SessionLocal
from sqlalchemy import text

print('=' * 70)
print('VERIFICACIÃ“N DE VALORES EN LA TABLA CLIENTES')
print('=' * 70)
print()

db = SessionLocal()
try:
    # Consultar los valores distintos de estado
    query = text('SELECT DISTINCT estado FROM clientes ORDER BY estado')
    results = db.execute(query).fetchall()
    
    print('Valores Ãºnicos en la columna estado (clientes):')
    for row in results:
        print(f'  - {repr(row[0])}')
    
    print()
    print('Conteo por estado:')
    query2 = text('SELECT estado, COUNT(*) as cantidad FROM clientes GROUP BY estado ORDER BY estado')
    results2 = db.execute(query2).fetchall()
    for row in results2:
        print(f'  - {repr(row[0])}: {row[1]}')
        
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
