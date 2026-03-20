from app.core.database import SessionLocal
from sqlalchemy import text, inspect

db = SessionLocal()
try:
    print('[BUSCAR] Tablas relacionadas a notificaciones...\n')
    
    inspector = inspect(db.get_bind())
    all_tables = inspector.get_table_names()
    
    # Buscar tablas con 'notif', 'notification', 'envio'
    matching = [t for t in all_tables if any(x in t.lower() for x in ['notif', 'envio', 'notificacion'])]
    
    print('Tablas encontradas:')
    for table in sorted(matching):
        cols = inspector.get_columns(table)
        print(f'  TABLE: {table}')
        for col in cols[:8]:
            print(f'    - {col[\"name\"]:<30} ({col[\"type\"]})')
        if len(cols) > 8:
            print(f'    ... (+{len(cols)-8} mas)')
        print()
    
    if not matching:
        print('  No se encontraron tablas de notificaciones')
        print('\n  Todas las tablas:')
        for t in sorted(all_tables)[:20]:
            print(f'    - {t}')
    
finally:
    db.close()
