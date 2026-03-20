import re

# Leer archivo
with open(r'C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar import del scheduler (despues de otros imports)
import_addition = 'from app.services.liquidado_scheduler import liquidado_scheduler\n'
if 'from app.services.liquidado_scheduler' not in content:
    # Buscar la linea que dice 'from app.middleware.audit_middleware import AuditMiddleware'
    content = content.replace(
        'from app.middleware.audit_middleware import AuditMiddleware',
        'from app.middleware.audit_middleware import AuditMiddleware\nfrom app.services.liquidado_scheduler import liquidado_scheduler'
    )
    print('[OK] Agregado import del scheduler')

# 2. Agregar inicializacion en on_startup (antes de la ultima exception handler)
startup_code = '''
    # Scheduler automatico de LIQUIDADO: ejecutar a las 21:00 (9 PM) diariamente
    try:
        liquidado_scheduler.iniciar_scheduler()
        logger.info('Scheduler de actualizacion a LIQUIDADO iniciado (9 PM diariamente)')
    except Exception as e:
        logger.warning('No se pudo iniciar el scheduler de LIQUIDADO: %s', e)
'''

# Buscar el bloque 'try/except' del limpiar syncs de Gmail y agregar antes
if 'liquidado_scheduler.iniciar_scheduler()' not in content:
    # Buscar donde agregar (antes de ''# Limpiar syncs de Gmail'')
    content = content.replace(
        '    # Limpiar syncs de Gmail que quedaron en estado "running"',
        startup_code.strip() + '\n\n    # Limpiar syncs de Gmail que quedaron en estado "running"'
    )
    print('[OK] Agregado inicializacion del scheduler en on_startup')

# 3. Agregar parada en on_shutdown (despues de start_scheduler_leader_heartbeat)
if 'liquidado_scheduler.detener_scheduler()' not in content:
    # Buscar donde agregar (antes del 'from app.core.scheduler import stop_scheduler')
    content = content.replace(
        '    try:\n        if getattr(app.state, "_scheduler_leader", False):',
        '    # Detener scheduler de LIQUIDADO\n    try:\n        liquidado_scheduler.detener_scheduler()\n        logger.info(\'Scheduler de LIQUIDADO detenido\')\n    except Exception as e:\n        logger.warning(\'Error al detener scheduler de LIQUIDADO: %s\', e)\n    \n    try:\n        if getattr(app.state, "_scheduler_leader", False):'
    )
    print('[OK] Agregado parada del scheduler en on_shutdown')

# 4. Agregar include_router del endpoint (despues de app.include_router(api_router...))
if 'prestamos_liquidado_automatico' not in content:
    content = content.replace(
        'app.include_router(api_router, prefix=settings.API_V1_STR)',
        'app.include_router(api_router, prefix=settings.API_V1_STR)\n\n# Incluir endpoint del scheduler de LIQUIDADO\nfrom app.api.v1.endpoints import prestamos_liquidado_automatico\napp.include_router(prestamos_liquidado_automatico.router)'
    )
    print('[OK] Agregado include_router del endpoint')

# Guardar archivo
with open(r'C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('[OK] Archivo main.py actualizado exitosamente')
