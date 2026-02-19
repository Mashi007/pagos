import os
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

from app.core.config import settings
from app.core.database import SessionLocal
from sqlalchemy import text

print('=' * 70)
print('CONSULTAS: CLIENTES INACTIVOS Y PRÃ‰STAMOS APROBADOS')
print('=' * 70)
print(f'ConexiÃ³n a BD: {settings.DATABASE_URL[:50]}...')
print()

db = SessionLocal()
try:
    # Query 1: Total clientes inactivos
    query1 = text('SELECT COUNT(*) as total_clientes_inactivos FROM clientes WHERE estado = ''INACTIVO''')
    result1 = db.execute(query1).fetchone()
    print('1. TOTAL CLIENTES INACTIVOS')
    print('-' * 70)
    print(f'   Total: {result1[0]}')
    print()
    
    # Query 2: Clientes inactivos CON prÃ©stamos aprobados
    query2 = text('SELECT COUNT(DISTINCT c.id) as clientes_inactivos_con_prestamos_aprobados FROM clientes c JOIN prestamos p ON c.id = p.cliente_id WHERE c.estado = ''INACTIVO'' AND p.estado = ''APROBADO''')
    result2 = db.execute(query2).fetchone()
    print('2. CLIENTES INACTIVOS CON PRÃ‰STAMOS APROBADOS')
    print('-' * 70)
    print(f'   Total: {result2[0]}')
    print()
    
    # Query 3: Clientes inactivos SIN prÃ©stamos aprobados
    query3 = text('SELECT COUNT(DISTINCT c.id) as clientes_inactivos_sin_prestamos_aprobados FROM clientes c WHERE c.estado = ''INACTIVO'' AND NOT EXISTS (SELECT 1 FROM prestamos p WHERE p.cliente_id = c.id AND p.estado = ''APROBADO'')')
    result3 = db.execute(query3).fetchone()
    print('3. CLIENTES INACTIVOS SIN PRÃ‰STAMOS APROBADOS')
    print('-' * 70)
    print(f'   Total: {result3[0]}')
    print()
    
    # Resumen
    print('RESUMEN COMBINADO')
    print('-' * 70)
    total_inactivos = result1[0]
    con_aprobados = result2[0]
    sin_aprobados = result3[0]
    
    print(f'   Total clientes inactivos:                  {total_inactivos}')
    print(f'   Con prÃ©stamos aprobados:                   {con_aprobados}')
    print(f'   Sin prÃ©stamos aprobados:                   {sin_aprobados}')
    print(f'   VerificaciÃ³n (con + sin = total):          {con_aprobados + sin_aprobados} = {total_inactivos}')
    
    if con_aprobados + sin_aprobados == total_inactivos:
        print('   âœ“ ValidaciÃ³n: OK')
    else:
        print('   âœ— ValidaciÃ³n: ERROR - Las sumas no coinciden')
    
    print()
    print('=' * 70)

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
