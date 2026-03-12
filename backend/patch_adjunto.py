# Script to add adjuntos-por-caso to adjunto_fijo_cobranza.py
import re

path = "app/services/adjunto_fijo_cobranza.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

if "CLAVE_ADJUNTOS_FIJOS_POR_CASO" in c:
    print("Constants already present")
    exit(0)

# Add constants after CLAVE_ADJUNTO_FIJO_COBRANZA
old = "CLAVE_ADJUNTO_FIJO_COBRANZA = \"adjunto_fijo_cobranza\""
new = """CLAVE_ADJUNTO_FIJO_COBRANZA = "adjunto_fijo_cobranza"
CLAVE_ADJUNTOS_FIJOS_POR_CASO = "adjuntos_fijos_por_caso"

TIPOS_CASO_VALIDOS = frozenset(["dias_5", "dias_3", "dias_1", "hoy", "mora_90"])"""
c = c.replace(old, new, 1)

# Append new functions before the last line (or at end)
new_funcs = '''

def _get_base_dir_adjuntos():
    """Directorio base para guardar adjuntos subidos por caso."""
    try:
        from app.core.config import settings
        base = getattr(settings, "ADJUNTO_FIJO_COBRANZA_BASE_DIR", None)
        if base and (base := (base or "").strip()):
            base = os.path.abspath(base)
        else:
            base = os.path.abspath(os.path.join(os.getcwd(), "uploads", "adjuntos_fijos"))
    except Exception:
        base = os.path.abspath(os.path.join(os.getcwd(), "uploads", "adjuntos_fijos"))
    os.makedirs(base, exist_ok=True)
    return base


def _get_adjuntos_por_caso_raw(db):
    """Lee la config adjuntos_fijos_por_caso de la BD."""
    if db is None:
        return {}
    try:
        from app.models.configuracion import Configuracion
        row = db.get(Configuracion, CLAVE_ADJUNTOS_FIJOS_POR_CASO)
        if not row or not row.valor:
            return {}
        data = json.loads(row.valor)
        if not isinstance(data, dict):
            return {}
        out = {}
        for k, v in data.items():
            if k in TIPOS_CASO_VALIDOS and isinstance(v, list):
                out[k] = [x for x in v if isinstance(x, dict) and x.get("id") and x.get("nombre_archivo") and x.get("ruta")]
            else:
                out[k] = []
        return out
    except json.JSONDecodeError:
        return {}
    except Exception as e:
        logger.exception("_get_adjuntos_por_caso_raw: %s", e)
        return {}


def get_adjuntos_fijos_por_caso(db, tipo_caso: str):
    """Lista de (nombre_archivo, contenido_bytes) de PDFs fijos para ese caso."""
    if tipo_caso not in TIPOS_CASO_VALIDOS:
        return []
    raw = _get_adjuntos_por_caso_raw(db)
    lista = raw.get(tipo_caso, [])
    base_dir = _get_base_dir_adjuntos()
    result = []
    for item in lista:
        ruta_rel = (item.get("ruta") or "").strip()
        nombre = (item.get("nombre_archivo") or "").strip() or "documento.pdf"
        if not ruta_rel:
            continue
        path = os.path.normpath(os.path.join(base_dir, ruta_rel))
        if not path.startswith(base_dir) or ".." in ruta_rel:
            continue
        if not os.path.isfile(path):
            logger.warning("Adjunto por caso %s no encontrado: %s", tipo_caso, path[:200])
            continue
        try:
            with open(path, "rb") as f:
                result.append((nombre, f.read()))
        except Exception as e:
            logger.warning("Error leyendo adjunto %s: %s", path[:200], e)
    return result
'''

# Insert before "def verificar_ruta_adjunto_fijo"
insert_before = "def verificar_ruta_adjunto_fijo(db)"
if insert_before in c and "def _get_base_dir_adjuntos" not in c:
    c = c.replace(insert_before, new_funcs.rstrip() + "\n\n" + insert_before)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Added new functions")
else:
    print("Skip or already patched:", "get_base_dir" in c)
