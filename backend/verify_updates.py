with open(r'C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
print('=== VERIFICACION: Cambios agregados ===\n')

# 1. Verificar import
print('1. IMPORT del scheduler:')
for i, line in enumerate(lines[:30]):
    if 'liquidado_scheduler' in line:
        print(f'   Linea {i+1}: {line.rstrip()}')

# 2. Verificar on_startup
print('\n2. Inicializacion en on_startup:')
for i, line in enumerate(lines[200:300]):
    if 'liquidado_scheduler.iniciar_scheduler' in line or 'Scheduler de actualizacion a LIQUIDADO' in line:
        print(f'   Linea {i+201}: {line.rstrip()}')

# 3. Verificar on_shutdown
print('\n3. Parada en on_shutdown:')
for i, line in enumerate(lines[270:330]):
    if 'liquidado_scheduler.detener_scheduler' in line or 'Scheduler de LIQUIDADO detenido' in line:
        print(f'   Linea {i+271}: {line.rstrip()}')

# 4. Verificar include_router
print('\n4. Include router del endpoint:')
for i, line in enumerate(lines[110:125]):
    if 'prestamos_liquidado_automatico' in line or 'app.include_router(prestamos_liquidado' in line:
        print(f'   Linea {i+111}: {line.rstrip()}')

print('\n✓ Verificacion completada')
