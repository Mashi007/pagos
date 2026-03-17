"""One-off: add TTL cache to sync_from_db in email_config_holder to avoid 4s DB load on every request."""
path = "app/core/email_config_holder.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) Add cache vars after logger
old1 = """logger = logging.getLogger(__name__)

CLAVE_EMAIL_CONFIG = "email_config\""""
new1 = """logger = logging.getLogger(__name__)

# Cache: evitar sync_from_db() en cada get_smtp_config/get_modo_pruebas (tarda 0.4-4s por llamada)
_sync_ttl_seconds = 60
_last_sync_time = 0.0

CLAVE_EMAIL_CONFIG = "email_config\""""
if old1 not in content:
    print("Block 1 not found")
else:
    content = content.replace(old1, new1)
    print("Block 1 OK")

# 2) At start of sync_from_db(), skip if within TTL
old2 = """def sync_from_db() -> None:
    \"\"\"Carga la configuraci"""
# use a unique substring - the docstring may have encoding
import re
# Find sync_from_db and add at the beginning (after the docstring and t0 = time.time())
old2_full = """def sync_from_db() -> None:
    \"\"\"Carga la configuraci\u00f3n de email desde la tabla configuracion y actualiza el holder."""
# Try without special char
old2_alt = "def sync_from_db() -> None:\n    \"\"\"Carga la"
idx = content.find("def sync_from_db()")
if idx == -1:
    print("sync_from_db not found")
else:
    # Insert after "t0 = time.time()" and "try:"
    t0_line = content.find("t0 = time.time()", idx)
    if t0_line == -1:
        print("t0 = time.time() not found")
    else:
        try_line = content.find("try:", t0_line)
        if try_line == -1:
            print("try: not found")
        else:
            # Insert cache check right after t0 = time.time() and newline
            insert_after = content.find("\n", t0_line) + 1
            check = '''
    global _last_sync_time
    if (time.time() - _last_sync_time) < _sync_ttl_seconds:
        return
'''
            content = content[:insert_after] + check + content[insert_after:]
            print("Block 2 (cache check) OK")

# 3) After successful load, set _last_sync_time (after log_phase line in sync_from_db)
old3 = "log_phase(logger, FASE_CONFIG_CARGA, True, \"config cargada desde BD\", duration_ms=(time.time() - t0) * 1000)"
new3 = "log_phase(logger, FASE_CONFIG_CARGA, True, \"config cargada desde BD\", duration_ms=(time.time() - t0) * 1000)\n            _last_sync_time = time.time()"
if old3 in content:
    content = content.replace(old3, new3)
    print("Block 3 OK")
else:
    print("Block 3 not found:", repr(old3[:50]))

# 4) In update_from_api, invalidate cache so next sync_from_db refetches
old4 = "def update_from_api(data: dict[str, Any]) -> None:"
new4 = "def update_from_api(data: dict[str, Any]) -> None:\n    global _last_sync_time\n    _last_sync_time = 0.0  # invalidar cache para que sync_from_db vuelva a cargar si hace falta"
if new4 not in content and old4 in content:
    content = content.replace(old4, new4)
    print("Block 4 OK")
else:
    print("Block 4 skip or not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done.")
