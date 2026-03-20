# -*- coding: utf-8 -*-
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print('='*120)
    print('ANALISIS: Logica de actualización automatica del estado a LIQUIDADO')
    print('='*120)
    
    # 1. Verificar triggers
    print('\n1. TRIGGERS en tabla prestamos')
    print('-'*120)
    result = db.execute(text('''
        SELECT 
            trigger_name,
            event_object_table,
            event_manipulation,
            action_statement
        FROM information_schema.triggers
        WHERE event_object_table = 'prestamos'
    ''')).fetchall()
    
    if result:
        for trigger_name, table, event, action in result:
            print(f'   Trigger: {trigger_name}')
            print(f'   Tabla: {table}')
            print(f'   Evento: {event}')
            print(f'   Accion: {action[:100]}...')
    else:
        print('   [NO EXISTEN TRIGGERS]')
    
    # 2. Verificar triggers en tabla cuota_pagos
    print('\n2. TRIGGERS en tabla cuota_pagos')
    print('-'*120)
    result = db.execute(text('''
        SELECT 
            trigger_name,
            event_object_table,
            event_manipulation
        FROM information_schema.triggers
        WHERE event_object_table = 'cuota_pagos'
    ''')).fetchall()
    
    if result:
        for trigger_name, table, event in result:
            print(f'   Trigger: {trigger_name}')
            print(f'   Evento: {event}')
    else:
        print('   [NO EXISTEN TRIGGERS]')
    
    # 3. Verificar funciones PL/pgSQL que mencionen LIQUIDADO
    print('\n3. FUNCIONES PL/pgSQL que mencionen LIQUIDADO')
    print('-'*120)
    result = db.execute(text('''
        SELECT 
            routine_schema,
            routine_name,
            routine_type
        FROM information_schema.routines
        WHERE routine_definition ILIKE '%LIQUIDADO%'
          AND routine_schema = 'public'
    ''')).fetchall()
    
    if result:
        for schema, name, type_ in result:
            print(f'   Esquema: {schema}')
            print(f'   Funcion: {name}')
            print(f'   Tipo: {type_}')
    else:
        print('   [NO EXISTEN FUNCIONES con LIQUIDADO]')
    
    # 4. Listar todas las funciones
    print('\n4. TODAS LAS FUNCIONES EN SCHEMA PUBLIC')
    print('-'*120)
    result = db.execute(text('''
        SELECT 
            routine_name,
            routine_type
        FROM information_schema.routines
        WHERE routine_schema = 'public'
        ORDER BY routine_name
    ''')).fetchall()
    
    if result:
        for name, type_ in result:
            print(f'   - {name} ({type_})')
    else:
        print('   [NO EXISTEN FUNCIONES]')
    
    print('\n' + '='*120)
    print('CONCLUSION:')
    print('='*120)
    print('''
Si NO hay triggers ni funciones automaticas para actualizar estado a LIQUIDADO:
- El backend/frontend DEBE IMPLEMENTAR logica explícita para:
  1. Detectar cuando prestamos.total_financiamiento = SUM(cuotas con estado=PAGADO)
  2. Actualizar prestamos.estado = LIQUIDADO automáticamente
  3. Registrar auditoria del cambio de estado
    ''')
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
