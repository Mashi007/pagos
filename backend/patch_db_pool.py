"""Ajusta pool_recycle y pool_size en database.py para reducir 'SSL connection closed unexpectedly' en Render."""
import os
path = os.path.join(os.path.dirname(__file__), "app", "core", "database.py")
with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

# Reemplazos para hacer el pool más resiliente a SSL drops en Render
old = "pool_size=10,          # Conexiones mantenidas en pool\n    max_overflow=20,"
new = "pool_size=5,           # Menos conexiones persistentes (Render free tier; evita SSL closed)\n    max_overflow=10,"
if old in c:
    c = c.replace(old, new)
else:
    print("WARN: pool_size/max_overflow block not found exactly")

old2 = "pool_recycle=1800,     # Recicla conexiones cada 30 min (evita SSL stale)"
new2 = "pool_recycle=300,     # Recicla cada 5 min (Render cierra SSL antes; evita SSL connection closed unexpectedly)"
if old2 in c:
    c = c.replace(old2, new2)
else:
    print("WARN: pool_recycle block not found")

old3 = '"keepalives_idle": 60,        # Inicia keepalive tras 60s de inactividad'
new3 = '"keepalives_idle": 30,        # Inicia keepalive tras 30s de inactividad'
if old3 in c:
    c = c.replace(old3, new3)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: database.py pool settings updated (pool_recycle=300, pool_size=5, keepalives_idle=30)")
