# -*- coding: utf-8 -*-
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print('='*120)
    print('PASO 1: Crear tabla de auditoria y funcion para actualizar a LIQUIDADO')
    print('='*120)
    
    # 1. Tabla de auditoria
    print('\n1. Creando tabla auditoria_cambios_estado_prestamo...')
    print('-'*120)
    db.execute(text('''
        CREATE TABLE IF NOT EXISTS auditoria_cambios_estado_prestamo (
            id SERIAL PRIMARY KEY,
            prestamo_id INTEGER NOT NULL REFERENCES prestamos(id),
            estado_anterior VARCHAR(50),
            estado_nuevo VARCHAR(50),
            motivo VARCHAR(255),
            fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ejecutado_por VARCHAR(100) DEFAULT 'sistema_automatico',
            total_financiamiento NUMERIC(14,2),
            suma_pagado NUMERIC(14,2)
        )
    '''))
    db.commit()
    print('   [OK] Tabla creada')
    
    # 2. Indices
    db.execute(text('''
        CREATE INDEX IF NOT EXISTS idx_auditoria_prestamo_id 
            ON auditoria_cambios_estado_prestamo(prestamo_id)
    '''))
    db.execute(text('''
        CREATE INDEX IF NOT EXISTS idx_auditoria_fecha_cambio 
            ON auditoria_cambios_estado_prestamo(fecha_cambio DESC)
    '''))
    db.commit()
    print('   [OK] Indices creados')
    
    # 3. Crear funcion manualmente SIN problemas de escape
    print('\n2. Creando funcion actualizar_prestamos_a_liquidado_automatico()...')
    print('-'*120)
    
    # Primero eliminar si existe
    db.execute(text('DROP FUNCTION IF EXISTS actualizar_prestamos_a_liquidado_automatico() CASCADE'))
    db.commit()
    
    # Crear funcion paso a paso
    db.execute(text('''
        CREATE FUNCTION actualizar_prestamos_a_liquidado_automatico()
        RETURNS void AS
        'UPDATE prestamos SET estado = ''LIQUIDADO'' WHERE estado = ''APROBADO'' AND id IN (
          SELECT p.id FROM prestamos p LEFT JOIN cuotas c ON c.prestamo_id = p.id
          WHERE p.estado = ''APROBADO'' GROUP BY p.id, p.total_financiamiento
          HAVING COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = ''PAGADO''), 0) >= p.total_financiamiento - 0.01
        );
        INSERT INTO auditoria_cambios_estado_prestamo
          (prestamo_id, estado_anterior, estado_nuevo, motivo, total_financiamiento, suma_pagado)
        SELECT p.id, ''APROBADO'', ''LIQUIDADO'', ''Actualizacion automatica: 100% pagado'',
          p.total_financiamiento::numeric(14,2),
          COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = ''PAGADO''), 0)::numeric(14,2)
        FROM prestamos p LEFT JOIN cuotas c ON c.prestamo_id = p.id
        WHERE p.estado = ''LIQUIDADO'' GROUP BY p.id, p.total_financiamiento;'
        LANGUAGE SQL
    '''))
    db.commit()
    print('   [OK] Función creada')
    
    print('\n[OK] PASO 1 COMPLETADO')
    print('='*120)
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
