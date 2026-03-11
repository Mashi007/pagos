"""
Adjunto PDF fijo para emails de cobranza.

Se anexa siempre el mismo archivo PDF sin modificaciones (documento estático).
La ruta y nombre se configuran en la tabla configuracion, clave 'adjunto_fijo_cobranza':
  JSON: { "nombre_archivo": "Documento.pdf", "ruta": "nombre.pdf" o "subcarpeta/nombre.pdf" }
Si ADJUNTO_FIJO_COBRANZA_BASE_DIR está definido, la ruta se resuelve dentro de ese directorio.
Si no, la ruta se interpreta como absoluta o relativa al cwd (comportamiento legacy).
"""
import json
import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

CLAVE_ADJUNTO_FIJO_COBRANZA = "adjunto_fijo_cobranza"


def _resolve_path(ruta: str) -> Optional[str]:
    """
    Resuelve la ruta del PDF fijo. Si hay BASE_DIR configurado, la ruta se une a ese directorio
    (sin permitir '..'). Si no, se usa como absoluta o relativa al cwd.
    Retorna la ruta absoluta resuelta o None si es inválida (path traversal).
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
                logger.warning("Adjunto fijo cobranza: ruta no permitida cuando BASE_DIR está configurado: %s", ruta[:100])
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
        logger.warning("Adjunto fijo cobranza: valor en BD no es JSON válido: %s", e)
        return None
    except Exception as e:
        logger.exception("Adjunto fijo cobranza: %s", e)
        return None


def verificar_ruta_adjunto_fijo(db) -> Tuple[bool, Optional[str]]:
    """
    Comprueba si la ruta configurada del adjunto fijo existe y es legible.
    Returns:
        (existe, mensaje_opcional). Si no hay ruta configurada, (False, "No configurado").
    """
    if db is None:
        return False, "Sesión no disponible"
    try:
        from app.models.configuracion import Configuracion
        row = db.get(Configuracion, CLAVE_ADJUNTO_FIJO_COBRANZA)
        if not row or not row.valor:
            return False, "No configurado"
        data = json.loads(row.valor)
        if not isinstance(data, dict):
            return False, "Configuración inválida"
        ruta = (data.get("ruta") or "").strip()
        if not ruta:
            return False, "Ruta vacía"
        path = _resolve_path(ruta)
        if not path:
            return False, "Ruta no permitida (use ruta relativa al directorio base)"
        if not os.path.isfile(path):
            return False, "Archivo no encontrado"
        return True, None
    except json.JSONDecodeError:
        return False, "Configuración inválida"
    except Exception as e:
        logger.exception("verificar_ruta_adjunto_fijo: %s", e)
        return False, str(e)
