# -*- coding: utf-8 -*-
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print('='*100)
    print('VERIFICACION ACTUAL: Estados de prestamos')
    print('='*100)
    
    # 1. Resumen por estado
    print('\n1. RESUMEN POR ESTADO')
    print('-'*100)
    result = db.execute(text('''
        SELECT
          estado,
          COUNT(*) AS cantidad,
          SUM(total_financiamiento)::numeric(14,2) AS suma_financiamiento
        FROM prestamos
        GROUP BY estado
        ORDER BY estado
    ''')).fetchall()
    
    for estado, cantidad, suma in result:
        print(f'   {estado:<15} | Cantidad: {cantidad:>5} | Suma Financiamiento: {suma:>15}')
    
    # 2. Totales
    print('\n2. TOTALES')
    print('-'*100)
    result = db.execute(text('''
        SELECT
          COUNT(*) AS total_prestamos,
          COUNT(*) FILTER (WHERE estado = 'APROBADO') AS aprobados,
          COUNT(*) FILTER (WHERE estado = 'LIQUIDADO') AS liquidados
        FROM prestamos
    ''')).fetchall()
    
    for total, aprobados, liquidados in result:
        print(f'   Total prestamos: {total}')
        print(f'   - APROBADO:      {aprobados}')
        print(f'   - LIQUIDADO:     {liquidados}')
    
    # 3. Los 5 ids que deberian estar en LIQUIDADO (para revisar si ya fueron corregidos)
    print('\n3. VERIFICACION: Los 5 IDs que deben estar en APROBADO (post-correccion)')
    print('-'*100)
    result = db.execute(text('''
        SELECT
          id,
          estado,
          total_financiamiento::numeric(14,2) AS capital,
          numero_cuotas
        FROM prestamos
        WHERE id IN (176, 331, 670, 1672, 2735)
        ORDER BY id
    ''')).fetchall()
    
    for id_, estado, capital, num_cuotas in result:
        status = '[OK]' if estado == 'APROBADO' else '[PENDIENTE]'
        print(f'   ID {id_:>5} | Estado: {estado:<10} | Capital: {capital:>10.2f} | Cuotas: {num_cuotas:>2} | {status}')
    
    # 4. Verificar si hay otros estados
    print('\n4. VALORES DISTINTOS EN prestamos.estado')
    print('-'*100)
    result = db.execute(text('''
        SELECT DISTINCT estado FROM prestamos ORDER BY estado
    ''')).fetchall()
    
    for (estado,) in result:
        print(f'   - {estado}')
    
    print('\n' + '='*100)
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
