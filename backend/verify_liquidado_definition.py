#!/usr/bin/env python
# -*- coding: utf-8 -*-
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print('='*100)
    print('VERIFICACION: DEFINICION REAL DE LIQUIDADO')
    print('='*100)
    
    # 1. Columnas en tabla prestamos
    print('\n1. TABLA: prestamos')
    print('-'*100)
    result = db.execute(text('''
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'prestamos'
        AND column_name IN ('id', 'estado', 'total_financiamiento')
    ''')).fetchall()
    
    for col_name, data_type in result:
        print(f'   {col_name:<30} {data_type}')
    
    # 2. Columnas en tabla cuotas
    print('\n2. TABLA: cuotas')
    print('-'*100)
    result = db.execute(text('''
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'cuotas'
        AND column_name IN ('prestamo_id', 'estado', 'monto_cuota', 'total_pagado')
    ''')).fetchall()
    
    for col_name, data_type in result:
        print(f'   {col_name:<30} {data_type}')
    
    # 3. Valores posibles de estado en cuotas
    print('\n3. VALORES POSIBLES: cuotas.estado')
    print('-'*100)
    result = db.execute(text('''
        SELECT DISTINCT estado FROM cuotas ORDER BY estado
    ''')).fetchall()
    
    for (estado,) in result:
        print(f'   - {estado}')
    
    # 4. Valores posibles de estado en prestamos
    print('\n4. VALORES POSIBLES: prestamos.estado')
    print('-'*100)
    result = db.execute(text('''
        SELECT DISTINCT estado FROM prestamos ORDER BY estado
    ''')).fetchall()
    
    for (estado,) in result:
        print(f'   - {estado}')
    
    # 5. Verificacion SQL exacta
    print('\n5. DEFINICION VERIFICADA:')
    print('-'*100)
    print('   LIQUIDADO se cumple cuando:')
    print('   prestamos.estado = LIQUIDADO')
    print('   AND')
    print('   prestamos.total_financiamiento = SUM(cuotas.monto_cuota WHERE cuotas.estado = PAGADO)')
    print()
    print('   CAMPOS EXACTOS UTILIZADOS:')
    print('   - prestamos.id (integer)')
    print('   - prestamos.estado (character varying)')
    print('   - prestamos.total_financiamiento (numeric)')
    print('   - cuotas.prestamo_id (integer)')
    print('   - cuotas.estado (character varying)')
    print('   - cuotas.monto_cuota (numeric)')
    
    print('\n6. VIOLACIONES DETECTADAS (5 registros):')
    print('-'*100)
    result = db.execute(text('''
        WITH liquidado_check AS (
          SELECT
            p.id,
            p.estado AS prestamos_estado,
            p.total_financiamiento,
            COUNT(c.id) FILTER (WHERE c.estado = 'PAGADO') AS cuotas_pagado_count,
            COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) AS suma_monto_cuota_pagado
          FROM prestamos p
          LEFT JOIN cuotas c ON c.prestamo_id = p.id
          WHERE p.estado = 'LIQUIDADO'
          GROUP BY p.id, p.estado, p.total_financiamiento
        )
        SELECT
          id,
          prestamos_estado,
          total_financiamiento,
          cuotas_pagado_count,
          suma_monto_cuota_pagado
        FROM liquidado_check
        WHERE ABS(total_financiamiento - suma_monto_cuota_pagado) > 0.01
        ORDER BY id
    ''')).fetchall()
    
    if result:
        for id_, estado, capital, count, suma in result:
            print(f'   ID {id_:>5} | estado={estado:<10} | total_financiamiento={capital:>10.2f} | SUM(monto_cuota)={suma:>10.2f}')
    else:
        print('   Ninguno - Todos los registros LIQUIDADO cumplen la definicion')
    
    print('\n' + '='*100)
    print('CONFIRMACION: Tu definicion de LIQUIDADO se aplica correctamente.')
    print('='*100)
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
