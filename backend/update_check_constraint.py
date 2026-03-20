# -*- coding: utf-8 -*-
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print('='*100)
    print('PASO 4: ACTUALIZAR CHECK constraint')
    print('='*100)
    
    # Paso 1: Verificar constraint actual
    print('\n1. Obtener definicion del CHECK constraint actual')
    print('-'*100)
    result = db.execute(text('''
        SELECT pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conname = 'ck_prestamos_estado_valido'
    ''')).fetchall()
    
    if result:
        for (constraint_def,) in result:
            print(f'   {constraint_def}')
    else:
        print('   No existe constraint con ese nombre')
    
    # Paso 2: Eliminar constraint antiguo
    print('\n2. Eliminando constraint antiguo...')
    print('-'*100)
    db.execute(text('''
        ALTER TABLE prestamos
        DROP CONSTRAINT IF EXISTS ck_prestamos_estado_valido
    '''))
    db.commit()
    print('   [OK] Constraint eliminado')
    
    # Paso 3: Crear constraint nuevo
    print('\n3. Creando constraint nuevo con SOLO APROBADO y LIQUIDADO...')
    print('-'*100)
    db.execute(text('''
        ALTER TABLE prestamos
        ADD CONSTRAINT ck_prestamos_estado_valido 
        CHECK (estado IN ('APROBADO', 'LIQUIDADO'))
    '''))
    db.commit()
    print('   [OK] Constraint creado')
    
    # Paso 4: Verificar constraint nuevo
    print('\n4. Verificar constraint nuevo')
    print('-'*100)
    result = db.execute(text('''
        SELECT pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conname = 'ck_prestamos_estado_valido'
    ''')).fetchall()
    
    for (constraint_def,) in result:
        print(f'   {constraint_def}')
    
    # Paso 5: Verificar estados en tabla
    print('\n5. Estados disponibles en prestamos')
    print('-'*100)
    result = db.execute(text('''
        SELECT DISTINCT estado FROM prestamos ORDER BY estado
    ''')).fetchall()
    
    for (estado,) in result:
        print(f'   - {estado}')
    
    print('\n' + '='*100)
    print('RESULTADO: CHECK constraint actualizado exitosamente')
    print('Ahora solo se permiten: APROBADO, LIQUIDADO')
    print('='*100)
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
