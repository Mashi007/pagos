"""
Adjunto PDF fijo para emails de cobranza.

Se anexa siempre el mismo archivo PDF sin modificaciones (documento estÃ¡tico).
La ruta y nombre se configuran en la tabla configuracion, clave 'adjunto_fijo_cobranza':
  JSON: { "nombre_archivo": "Documento.pdf", "ruta": "nombre.pdf" o "subcarpeta/nombre.pdf" }
Si ADJUNTO_FIJO_COBRANZA_BASE_DIR estÃ¡ definido, la ruta se resuelve dentro de ese directorio.
Si no, la ruta se interpreta como absoluta o relativa al cwd (comportamiento legacy).
"""
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CLAVE_ADJUNTO_FIJO_COBRANZA = "adjunto_fijo_cobranza"
CLAVE_ADJUNTOS_FIJOS_POR_CASO = "adjuntos_fijos_por_caso"

TIPOS_CASO_VALIDOS = frozenset(["dias_5", "dias_3", "dias_1", "hoy", "mora_90"])


def _resolve_path(ruta: str) -> Optional[str]:
    """
    Resuelve la ruta del PDF fijo. Si hay BASE_DIR configurado, la ruta se une a ese directorio
    (sin permitir '..'). Si no, se usa como absoluta o relativa al cwd.
    Retorna la ruta absoluta resuelta o None si es invÃ¡lida (path traversal).
    """
    ruta = (ruta or "").strip()
    if not ruta:
        return None
    try:
        from app.core.config import settings
        base_dir = getattr(settings, "ADJUNTO_FIJO_COBRANZA_BASE_DIR", None)
        if base_dir and (base_dir := (base_dir or "").strip()):
            base_dir = os.path.abspath(base_dir)
            if ".." in ruta or ruta.startswith("/") or (len(ruta) >= 2 and ruta[1] == ":"):
                logger.warning("Adjunto fijo cobranza: ruta no permitida cuando BASE_DIR estÃ¡ configurado: %s", ruta[:100])
                return None
            path = os.path.normpath(os.path.join(base_dir, ruta))
            if not path.startswith(base_dir):
                logger.warning("Adjunto fijo cobranza: path traversal detectado: %s", path[:100])
                return None
            return path
        path = os.path.normpath(ruta)
        if not os.path.isabs(path):
            path = os.path.normpath(os.path.join(os.getcwd(), ruta))
        return path
    except Exception as e:
        logger.warning("Adjunto fijo cobranza: error resolviendo ruta: %s", e)
        return None


def get_adjunto_fijo_cobranza_bytes(db) -> Optional[Tuple[str, bytes]]:
    """
    Carga el PDF fijo configurado para cobranza desde disco.

    Config en BD: clave 'adjunto_fijo_cobranza', valor JSON:
      { "nombre_archivo": "NombreVisible.pdf", "ruta": "ruta/al/archivo.pdf" }

    Returns:
        (nombre_archivo, bytes) si hay config, la ruta existe y se puede leer; None en caso contrario.
    """
    if db is None:
        return None
    try:
        from app.models.configuracion import Configuracion
        row = db.get(Configuracion, CLAVE_ADJUNTO_FIJO_COBRANZA)
        if not row or not row.valor:
            return None
        data = json.loads(row.valor)
        if not isinstance(data, dict):
            return None
        ruta = (data.get("ruta") or "").strip()
        nombre = (data.get("nombre_archivo") or "").strip() or "Adjunto_Cobranza.pdf"
        if not ruta:
            return None
        path = _resolve_path(ruta)
        if not path or not os.path.isfile(path):
            if path:
                logger.warning("Adjunto fijo cobranza: archivo no encontrado en %s", path)
            return None
        with open(path, "rb") as f:
            content = f.read()
        return (nombre, content)
    except json.JSONDecodeError as e:
        logger.warning("Adjunto fijo cobranza: valor en BD no es JSON vÃ¡lido: %s", e)
        return None
    except Exception as e:
        logger.exception("Adjunto fijo cobranza: %s", e)
        return None




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

def verificar_ruta_adjunto_fijo(db) -> Tuple[bool, Optional[str]]:
    """
    Comprueba si la ruta configurada del adjunto fijo existe y es legible.
    Returns:
        (existe, mensaje_opcional). Si no hay ruta configurada, (False, "No configurado").
    """
    if db is None:
        return False, "SesiÃ³n no disponible"
    try:
        from app.models.configuracion import Configuracion
        row = db.get(Configuracion, CLAVE_ADJUNTO_FIJO_COBRANZA)
        if not row or not row.valor:
            return False, "No configurado"
        data = json.loads(row.valor)
        if not isinstance(data, dict):
            return False, "ConfiguraciÃ³n invÃ¡lida"
        ruta = (data.get("ruta") or "").strip()
        if not ruta:
            return False, "Ruta vacÃ­a"
        path = _resolve_path(ruta)
        if not path:
            return False, "Ruta no permitida (use ruta relativa al directorio base)"
        if not os.path.isfile(path):
            return False, "Archivo no encontrado"
        return True, None
    except json.JSONDecodeError:
        return False, "ConfiguraciÃ³n invÃ¡lida"
    except Exception as e:
        logger.exception("verificar_ruta_adjunto_fijo: %s", e)
        return False, str(e)
