import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path('.env'))
import psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')
cur = conn.cursor()
cur.execute("SELECT nombre_variable, tabla, campo_bd, activa FROM variables_notificacion ORDER BY nombre_variable")
rows = cur.fetchall()
print('count=', len(rows))
for r in rows:
    print(r)
cur.execute("SELECT variables_disponibles FROM plantillas_notificacion WHERE id=27")
print('plantilla27 vars=', cur.fetchone())
cur.close(); conn.close()