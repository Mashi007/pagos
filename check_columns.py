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
    
    # Obtener columnas de la tabla clientes
    cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='clientes'")
    columns = cursor.fetchall()
    
    print('Columnas de la tabla clientes:')
    print('-' * 50)
    for col in columns:
        print('  - ' + col[0] + ' (' + col[1] + ')')
    
    # Verificar si existen los IDs
    print('\nVerificando IDs de clientes a actualizar...')
    ids_to_check = [13131, 13970, 14855, 14972, 15073, 16064, 16750]
    placeholders = ','.join(['%s'] * len(ids_to_check))
    query = f"SELECT id, cedula, nombre, estado FROM clientes WHERE id IN ({placeholders}) ORDER BY id"
    cursor.execute(query, ids_to_check)
    results = cursor.fetchall()
    
    print('IDs encontrados: ' + str(len(results)) + ' de ' + str(len(ids_to_check)))
    print('-' * 50)
    for row in results:
        print('ID: ' + str(row[0]) + ', Estado: ' + str(row[3]))
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print('Error: ' + str(e))
