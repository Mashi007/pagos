# -*- coding: utf-8 -*-
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print('='*120)
    print('VERIFICACION COMPLETA: Estados en prestamos')
    print('='*120)
    
    # 1. Resumen global
    print('\n1. RESUMEN GLOBAL')
    print('-'*120)
    result = db.execute(text('''
        SELECT
          COUNT(*) AS total_prestamos,
          COUNT(*) FILTER (WHERE estado = 'APROBADO') AS aprobados,
          COUNT(*) FILTER (WHERE estado = 'LIQUIDADO') AS liquidados,
          COUNT(*) FILTER (WHERE estado NOT IN ('APROBADO', 'LIQUIDADO')) AS otros_estados
        FROM prestamos
    ''')).fetchall()
    
    for total, aprobados, liquidados, otros in result:
        print(f'   Total prestamos:      {total}')
        print(f'   - APROBADO:           {aprobados}')
        print(f'   - LIQUIDADO:          {liquidados}')
        print(f'   - Otros estados:      {otros}')
    
    # 2. Distribucion por estado
    print('\n2. DISTRIBUCION POR ESTADO')
    print('-'*120)
    result = db.execute(text('''
        SELECT
          estado,
          COUNT(*) AS cantidad,
          ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM prestamos), 2) AS porcentaje,
          SUM(total_financiamiento)::numeric(14,2) AS suma_financiamiento
        FROM prestamos
        GROUP BY estado
        ORDER BY estado
    ''')).fetchall()
    
    print(f'   {"Estado":<20} | {"Cantidad":>8} | {"Porcentaje":>10} | {"Suma Financiamiento":>20}')
    print('   ' + '-'*80)
    for estado, cantidad, porcentaje, suma in result:
        print(f'   {estado:<20} | {cantidad:>8} | {porcentaje:>10}% | {suma:>20}')
    
    # 3. Prestamos APROBADO - estadisticas
    print('\n3. PRESTAMOS APROBADO - ESTADISTICAS')
    print('-'*120)
    result = db.execute(text('''
        SELECT
          COUNT(*) AS cantidad,
          SUM(total_financiamiento)::numeric(14,2) AS suma_capital,
          AVG(total_financiamiento)::numeric(14,2) AS promedio_capital,
          MIN(total_financiamiento)::numeric(14,2) AS minimo,
          MAX(total_financiamiento)::numeric(14,2) AS maximo,
          AVG(numero_cuotas)::numeric(10,2) AS promedio_cuotas
        FROM prestamos
        WHERE estado = 'APROBADO'
    ''')).fetchall()
    
    for cantidad, suma, promedio, minimo, maximo, prom_cuotas in result:
        print(f'   Cantidad:             {cantidad}')
        print(f'   Suma Capital:         {suma}')
        print(f'   Promedio Capital:     {promedio}')
        print(f'   Capital Minimo:       {minimo}')
        print(f'   Capital Maximo:       {maximo}')
        print(f'   Promedio Cuotas:      {prom_cuotas}')
    
    # 4. Prestamos LIQUIDADO - estadisticas
    print('\n4. PRESTAMOS LIQUIDADO - ESTADISTICAS')
    print('-'*120)
    result = db.execute(text('''
        SELECT
          COUNT(*) AS cantidad,
          SUM(total_financiamiento)::numeric(14,2) AS suma_capital,
          AVG(total_financiamiento)::numeric(14,2) AS promedio_capital,
          MIN(total_financiamiento)::numeric(14,2) AS minimo,
          MAX(total_financiamiento)::numeric(14,2) AS maximo,
          AVG(numero_cuotas)::numeric(10,2) AS promedio_cuotas
        FROM prestamos
        WHERE estado = 'LIQUIDADO'
    ''')).fetchall()
    
    for cantidad, suma, promedio, minimo, maximo, prom_cuotas in result:
        print(f'   Cantidad:             {cantidad}')
        print(f'   Suma Capital:         {suma}')
        print(f'   Promedio Capital:     {promedio}')
        print(f'   Capital Minimo:       {minimo}')
        print(f'   Capital Maximo:       {maximo}')
        print(f'   Promedio Cuotas:      {prom_cuotas}')
    
    # 5. Valores DISTINTOS de estado
    print('\n5. VALORES DISTINTOS EN prestamos.estado')
    print('-'*120)
    result = db.execute(text('''
        SELECT DISTINCT estado FROM prestamos ORDER BY estado
    ''')).fetchall()
    
    for (estado,) in result:
        print(f'   - {estado}')
    
    # 6. Verificar CHECK constraint
    print('\n6. CONSTRAINT: ck_prestamos_estado_valido')
    print('-'*120)
    result = db.execute(text('''
        SELECT pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conname = 'ck_prestamos_estado_valido'
    ''')).fetchall()
    
    if result:
        for (constraint_def,) in result:
            print(f'   {constraint_def}')
    else:
        print('   [NO EXISTE]')
    
    # 7. Los 4 IDs que fueron corregidos
    print('\n7. VERIFICACION: Los 4 IDs CORREGIDOS (176, 331, 1672, 2735)')
    print('-'*120)
    result = db.execute(text('''
        SELECT
          id,
          estado,
          total_financiamiento::numeric(14,2) AS capital,
          numero_cuotas,
          fecha_aprobacion
        FROM prestamos
        WHERE id IN (176, 331, 1672, 2735)
        ORDER BY id
    ''')).fetchall()
    
    print(f'   {"ID":>6} | {"Estado":<10} | {"Capital":>12} | {"Cuotas":>6} | {"Fecha Aprobacion"}')
    print('   ' + '-'*80)
    for id_, estado, capital, cuotas, fecha_aprob in result:
        status = '[OK]' if estado == 'APROBADO' else '[ERROR]'
        print(f'   {id_:>6} | {estado:<10} | {capital:>12} | {cuotas:>6} | {fecha_aprob} {status}')
    
    # 8. Integridad: APROBADO con cuotas
    print('\n8. INTEGRIDAD: APROBADO con cuotas generadas')
    print('-'*120)
    result = db.execute(text('''
        WITH aprobado_cuotas AS (
          SELECT
            p.id,
            p.estado,
            COUNT(c.id) AS num_cuotas_generadas,
            p.numero_cuotas AS cuotas_declaradas
          FROM prestamos p
          LEFT JOIN cuotas c ON c.prestamo_id = p.id
          WHERE p.estado = 'APROBADO'
          GROUP BY p.id, p.estado, p.numero_cuotas
        )
        SELECT
          COUNT(*) AS prestamos_aprobado,
          COUNT(*) FILTER (WHERE num_cuotas_generadas = cuotas_declaradas) AS con_cobertura_completa,
          COUNT(*) FILTER (WHERE num_cuotas_generadas < cuotas_declaradas) AS con_cobertura_parcial,
          COUNT(*) FILTER (WHERE num_cuotas_generadas = 0) AS sin_cuotas
        FROM aprobado_cuotas
    ''')).fetchall()
    
    for total, completa, parcial, sin_cuotas in result:
        print(f'   Total APROBADO:           {total}')
        print(f'   - Con cobertura completa: {completa}')
        print(f'   - Con cobertura parcial:  {parcial}')
        print(f'   - Sin cuotas:             {sin_cuotas}')
    
    # 9. Integridad: LIQUIDADO con cuotas 100% pagadas
    print('\n9. INTEGRIDAD: LIQUIDADO = 100% PAGADO')
    print('-'*120)
    result = db.execute(text('''
        WITH liquidado_check AS (
          SELECT
            p.id,
            p.total_financiamiento,
            COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) AS suma_pagado
          FROM prestamos p
          LEFT JOIN cuotas c ON c.prestamo_id = p.id
          WHERE p.estado = 'LIQUIDADO'
          GROUP BY p.id, p.total_financiamiento
        )
        SELECT
          COUNT(*) AS total_liquidado,
          COUNT(*) FILTER (WHERE ABS(total_financiamiento - suma_pagado) <= 0.01) AS cumple_definicion,
          COUNT(*) FILTER (WHERE ABS(total_financiamiento - suma_pagado) > 0.01) AS viola_definicion
        FROM liquidado_check
    ''')).fetchall()
    
    for total, cumple, viola in result:
        status = '[OK]' if viola == 0 else '[ALERTA]'
        print(f'   Total LIQUIDADO:          {total}')
        print(f'   - Cumplen definicion:     {cumple}')
        print(f'   - Violan definicion:      {viola} {status}')
    
    print('\n' + '='*120)
    print('VERIFICACION COMPLETADA')
    print('='*120)
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
