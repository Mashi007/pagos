# -*- coding: utf-8 -*-
\"\"\"
Script de prueba para verificar la automatizacion de LIQUIDADO
\"\"\"
from app.core.database import SessionLocal
from sqlalchemy import text
from datetime import datetime
import time

db = SessionLocal()
try:
    print('='*120)
    print('PRUEBA: Actualizacion de prestamos a LIQUIDADO')
    print('='*120)
    
    # 1. Contar prestamos APROBADO antes
    print('\n1. ANTES')
    print('-'*120)
    result_antes = db.execute(text('''
        SELECT
          COUNT(*) FILTER (WHERE estado = 'APROBADO') as aprobados,
          COUNT(*) FILTER (WHERE estado = 'LIQUIDADO') as liquidados
        FROM prestamos
    ''')).fetchone()
    print(f'   APROBADO: {result_antes[0]}')
    print(f'   LIQUIDADO: {result_antes[1]}')
    
    # 2. Ejecutar la funcion
    print('\n2. EJECUTAR: actualizar_prestamos_a_liquidado_automatico()')
    print('-'*120)
    db.execute(text('''SELECT actualizar_prestamos_a_liquidado_automatico()'''))
    db.commit()
    print('   [OK] Funcion ejecutada')
    time.sleep(1)
    
    # 3. Contar prestamos APROBADO despues
    print('\n3. DESPUES')
    print('-'*120)
    result_despues = db.execute(text('''
        SELECT
          COUNT(*) FILTER (WHERE estado = 'APROBADO') as aprobados,
          COUNT(*) FILTER (WHERE estado = 'LIQUIDADO') as liquidados
        FROM prestamos
    ''')).fetchone()
    print(f'   APROBADO: {result_despues[0]}')
    print(f'   LIQUIDADO: {result_despues[1]}')
    
    # 4. Mostrar cambios
    cambios = result_antes[0] - result_despues[0]
    print('\n4. CAMBIOS')
    print('-'*120)
    print(f'   APROBADO cambiados a LIQUIDADO: {cambios}')
    
    # 5. Mostrar auditoria reciente
    print('\n5. AUDITORIA RECIENTE')
    print('-'*120)
    registros = db.execute(text('''
        SELECT 
          prestamo_id,
          estado_anterior,
          estado_nuevo,
          motivo,
          fecha_cambio,
          total_financiamiento,
          suma_pagado
        FROM auditoria_cambios_estado_prestamo
        WHERE fecha_cambio >= NOW() - INTERVAL '5 minutes'
        ORDER BY fecha_cambio DESC
        LIMIT 5
    ''')).fetchall()
    
    print(f'   Registros encontrados: {len(registros)}')
    for i, reg in enumerate(registros, 1):
        print(f'\n   Registro {i}:')
        print(f'     Prestamo ID: {reg[0]}')
        print(f'     {reg[1]} -> {reg[2]}')
        print(f'     Motivo: {reg[3]}')
        print(f'     Capital: {reg[5]}')
        print(f'     Pagado: {reg[6]}')
    
    print('\n' + '='*120)
    print('PRUEBA COMPLETADA')
    print('='*120)
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
