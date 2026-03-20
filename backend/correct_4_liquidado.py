# -*- coding: utf-8 -*-
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print('='*100)
    print('PASO 2: ACTUALIZAR los 4 prestamos de LIQUIDADO a APROBADO')
    print('='*100)
    
    # Ejecutar el UPDATE
    result = db.execute(text('''
        UPDATE prestamos p
        SET estado = 'APROBADO'
        WHERE p.id IN (176, 331, 1672, 2735)
          AND p.estado = 'LIQUIDADO'
        RETURNING id, estado
    '''))
    
    updated_rows = result.fetchall()
    db.commit()
    
    print(f'\nActualizados: {len(updated_rows)} registros\n')
    
    for id_, estado in updated_rows:
        print(f'   ID {id_:>5} -> estado = {estado}')
    
    # Verificar resultado
    print('\n' + '='*100)
    print('PASO 3: VERIFICAR resultado post-UPDATE')
    print('='*100 + '\n')
    
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
        print(f'   {estado:<15} | Cantidad: {cantidad:>5} | Suma: {suma:>15}')
    
    print('\n' + '='*100)
    print('RESULTADO: 4 prestamos corregidos de LIQUIDADO -> APROBADO')
    print('='*100)
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
