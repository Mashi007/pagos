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
    
    # Obtener lista de tablas
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = cursor.fetchall()
    
    print('Tablas disponibles en la base de datos:')
    print('-' * 50)
    for table in tables:
        print('  - ' + table[0])
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print('Error: ' + str(e))
