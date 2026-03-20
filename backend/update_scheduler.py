# Leer scheduler actual
with open(r'C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\services\liquidado_scheduler.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar import
if 'from app.services.liquidado_notificacion_service' not in content:
    content = content.replace(
        'import logging\nfrom datetime import datetime',
        'import logging\nfrom datetime import datetime\nfrom app.services.liquidado_notificacion_service import notificacion_service'
    )
    print('[OK] Agregado import de notificacion_service')

# Agregar llamada a notificacion en el metodo (buscar la linea donde se ejecuta la funcion SQL)
if 'notificacion_service.crear_notificacion' not in content:
    # Buscar la linea donde obtiene los cambios registrados
    marker = 'logger.info(f'
    # Insertar notificacion ANTES del log final
    notif_insert = '''
    
    # Crear notificaciones para cada cambio
    try:
        result_cambios = db.execute(text(\"\"\"
            SELECT p.id, p.total_financiamiento, COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0)
            FROM prestamos p
            LEFT JOIN cuotas c ON c.prestamo_id = p.id
            WHERE p.estado = 'LIQUIDADO' AND p.id IN (
              SELECT p2.id FROM prestamos p2
              LEFT JOIN cuotas c2 ON c2.prestamo_id = p2.id
              WHERE p2.estado = 'LIQUIDADO'
              GROUP BY p2.id, p2.total_financiamiento
              HAVING COALESCE(SUM(c2.monto_cuota) FILTER (WHERE c2.estado = 'PAGADO'), 0) >= p2.total_financiamiento - 0.01
            )
            GROUP BY p.id, p.total_financiamiento
        \"\"\")).fetchall()
        
        for prestamo_id, capital, suma_pagado in result_cambios:
            notificacion_service.crear_notificacion(
                prestamo_id=int(prestamo_id),
                capital=float(capital),
                suma_pagado=float(suma_pagado)
            )
    except Exception as e:
        logger.warning(f'[LIQUIDADO_NOTIF] Error al crear notificaciones: {e}')'''
    
    # Insertar antes del RAISE NOTICE
    content = content.replace(
        "RAISE NOTICE 'Prestamos actualizados a LIQUIDADO:",
        notif_insert + "\n    -- Log final\n    RAISE NOTICE 'Prestamos actualizados a LIQUIDADO:"
    )
    print('[OK] Agregada llamada a notificacion_service en scheduler')

# Guardar
with open(r'C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\services\liquidado_scheduler.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('[OK] Scheduler actualizado con integracion de notificaciones')
