import psycopg2

db_config = {
    'host': 'dpg-d3l8tkur433s738ooph0-a.oregon-postgres.render.com',
    'port': 5432,
    'database': 'pagos_db_zjer',
    'user': 'pagos_admin',
    'password': 'F3iOLGHBnP8NBhojFwpA6vCwCngGUrGt',
    'sslmode': 'require'
}

try:
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password'],
        sslmode=db_config['sslmode']
    )
    
    cursor = conn.cursor()
    
    print('=' * 80)
    print('EJECUTANDO CONSULTAS SQL')
    print('=' * 80)
    
    ids_clientes = [13131, 13970, 14855, 14972, 15073, 16064, 16750]
    
    print('\n1. ACTUALIZANDO ESTADO DE 7 CLIENTES DE INACTIVO A ACTIVO...')
    placeholders = ','.join(['%s'] * len(ids_clientes))
    update_query = f"UPDATE clientes SET estado = 'ACTIVO' WHERE estado = 'INACTIVO' AND id IN ({placeholders})"
    
    cursor.execute(update_query, ids_clientes)
    rows_updated = cursor.rowcount
    conn.commit()
    print('âœ“ Filas actualizadas: ' + str(rows_updated))
    
    print('\n2. VERIFICANDO TOTAL DE CLIENTES INACTIVOS RESTANTES...')
    cursor.execute("SELECT COUNT(*) FROM clientes WHERE estado = 'INACTIVO'")
    inactive_count = cursor.fetchone()[0]
    print('âœ“ Total INACTIVOS: ' + str(inactive_count))
    
    print('\n3. LISTA DE LOS 7 CLIENTES ACTUALIZADOS:')
    query = f"SELECT id, cedula, nombres, estado FROM clientes WHERE id IN ({placeholders}) ORDER BY id"
    cursor.execute(query, ids_clientes)
    updated_clients = cursor.fetchall()
    
    print('-' * 80)
    print('ID       | CEDULA          | NOMBRE                          | ESTADO    ')
    print('-' * 80)
    for row in updated_clients:
        nombre = str(row[2]) if row[2] else 'N/A'
        print(str(row[0]).ljust(8) + '| ' + str(row[1]).ljust(15) + '| ' + nombre.ljust(31) + '| ' + str(row[3]).ljust(10))
    print('-' * 80)
    
    print('\n4. VERIFICANDO TOTAL DE CLIENTES ACTIVOS...')
    cursor.execute("SELECT COUNT(*) FROM clientes WHERE estado = 'ACTIVO'")
    active_count = cursor.fetchone()[0]
    print('âœ“ Total ACTIVOS: ' + str(active_count))
    
    print('\n' + '=' * 80)
    print('RESUMEN DE CAMBIOS')
    print('=' * 80)
    print('âœ“ Clientes actualizados: ' + str(rows_updated))
    print('âœ“ Clientes INACTIVOS restantes: ' + str(inactive_count))
    print('âœ“ Total de clientes ACTIVOS: ' + str(active_count))
    print('=' * 80)
    
    cursor.close()
    conn.close()
    
except psycopg2.Error as e:
    print('Error BD: ' + str(e))
except Exception as e:
    print('Error: ' + str(e))
