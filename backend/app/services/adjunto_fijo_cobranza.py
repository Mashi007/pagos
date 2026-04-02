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

# Casos de notificaciones: retrasadas (desde dia siguiente al venc.), prejudicial
TIPOS_CASO_VALIDOS = frozenset([
    "dias_1_retraso", "dias_3_retraso", "dias_5_retraso", "dias_30_retraso",
    "prejudicial",
    "masivos",
])

# Evitar repetir el mismo WARNING por cada ítem del batch (Render: disco efímero, archivos no existen)
_warned_adjuntos_caso_vacio: set = set()
_warned_adjunto_path: set = set()


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
            key = (tipo_caso, path)
            if key not in _warned_adjunto_path:
                _warned_adjunto_path.add(key)
                logger.warning("Adjunto por caso %s no encontrado (en Render usar disco persistente). base_dir=%s path=%s", tipo_caso, base_dir[:120], path[:200])
            continue
        try:
            with open(path, "rb") as f:
                result.append((nombre, f.read()))
        except Exception as e:
            logger.warning("Error leyendo adjunto %s: %s", path[:200], e)
    if lista and not result:
        if tipo_caso not in _warned_adjuntos_caso_vacio:
            _warned_adjuntos_caso_vacio.add(tipo_caso)
            logger.warning("Adjuntos fijos caso %s: config tiene entradas pero ningun archivo encontrado. base_dir=%s (Render: usar disco persistente)", tipo_caso, base_dir[:150])
    elif result:
        logger.info("Adjuntos fijos caso %s: %d archivo(s) anexados", tipo_caso, len(result))
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


def _bytes_es_pdf_valido(data: Optional[bytes]) -> bool:
    if not data or len(data) < 4:
        return False
    return data[:4] == b"%PDF"


def _diagnostico_archivo_en_disco(path: Optional[str]) -> dict:
    """Estado de un archivo: existe, tamano, cabecera PDF."""
    out: Dict[str, Any] = {
        "path_resuelto": path,
        "existe": False,
        "tamano_bytes": None,
        "cabecera_pdf": False,
    }
    if not path:
        out["motivo"] = "sin_ruta"
        return out
    try:
        if not os.path.isfile(path):
            out["motivo"] = "archivo_no_encontrado"
            return out
        out["existe"] = True
        out["tamano_bytes"] = int(os.path.getsize(path))
        with open(path, "rb") as f:
            head = f.read(16)
        out["cabecera_pdf"] = _bytes_es_pdf_valido(head)
        if not out["cabecera_pdf"]:
            out["motivo"] = "no_es_pdf_valido_o_vacio"
    except Exception as e:
        out["motivo"] = "error_lectura"
        out["error"] = str(e)
    return out


def diagnostico_adjuntos_notificaciones_cobranza(db) -> dict:
    """
    Diagnostico en una sola respuesta: adjunto global + PDFs fijos por caso (pestaña 3).
    Sirve para Render: rutas resueltas, existencia, tamano, cabecera %PDF.
    """
    from app.core.config import settings

    base_dir_por_caso = _get_base_dir_adjuntos()
    adj_base = getattr(settings, "ADJUNTO_FIJO_COBRANZA_BASE_DIR", None)
    cwd = os.getcwd()
    paquete_estricto = bool(getattr(settings, "NOTIFICACIONES_PAQUETE_ESTRICTO", True))

    global_diag: Dict[str, Any] = {
        "clave_configuracion": CLAVE_ADJUNTO_FIJO_COBRANZA,
        "configurado_en_bd": False,
        "ruta_relativa_config": None,
        "nombre_archivo_config": None,
        "archivo": {},
    }
    try:
        from app.models.configuracion import Configuracion

        row_g = db.get(Configuracion, CLAVE_ADJUNTO_FIJO_COBRANZA) if db is not None else None
        if row_g and row_g.valor:
            global_diag["configurado_en_bd"] = True
            data_g = json.loads(row_g.valor)
            if isinstance(data_g, dict):
                global_diag["ruta_relativa_config"] = (data_g.get("ruta") or "").strip() or None
                global_diag["nombre_archivo_config"] = (data_g.get("nombre_archivo") or "").strip() or None
                ruta = global_diag["ruta_relativa_config"] or ""
                path_g = _resolve_path(ruta) if ruta else None
                global_diag["archivo"] = _diagnostico_archivo_en_disco(path_g)
    except json.JSONDecodeError:
        global_diag["error"] = "json_invalido_adjunto_global"
    except Exception as e:
        global_diag["error"] = str(e)

    bytes_global = None
    try:
        tup = get_adjunto_fijo_cobranza_bytes(db)
        if tup:
            bytes_global = tup[1]
    except Exception:
        pass
    global_diag["carga_ok_servicio"] = bytes_global is not None and _bytes_es_pdf_valido(bytes_global)

    por_caso: Dict[str, Any] = {}
    raw_full: Dict[str, Any] = {}
    try:
        from app.models.configuracion import Configuracion

        row_c = db.get(Configuracion, CLAVE_ADJUNTOS_FIJOS_POR_CASO) if db is not None else None
        if row_c and row_c.valor:
            data_c = json.loads(row_c.valor)
            if isinstance(data_c, dict):
                raw_full = data_c
    except Exception:
        raw_full = {}

    for tipo_caso in sorted(TIPOS_CASO_VALIDOS):
        base_dir = base_dir_por_caso
        lista = raw_full.get(tipo_caso)
        if not isinstance(lista, list):
            lista = []
        entradas = []
        cargables = 0
        for item in lista:
            if not isinstance(item, dict):
                entradas.append({"error": "item_no_es_objeto"})
                continue
            ruta_rel = (item.get("ruta") or "").strip()
            nombre = (item.get("nombre_archivo") or "").strip() or "documento.pdf"
            _id = item.get("id")
            valido_cfg = bool(_id and item.get("nombre_archivo") and item.get("ruta"))
            path_abs = None
            motivo_path = None
            if not ruta_rel:
                motivo_path = "ruta_vacia"
            else:
                path_abs = os.path.normpath(os.path.join(base_dir, ruta_rel))
                if not path_abs.startswith(base_dir) or ".." in ruta_rel:
                    path_abs = None
                    motivo_path = "ruta_no_permitida_o_traversal"
            diag = _diagnostico_archivo_en_disco(path_abs)
            if motivo_path:
                diag["motivo_resolucion"] = motivo_path
            pdf_ok = False
            if diag.get("existe") and diag.get("tamano_bytes", 0) and diag.get("cabecera_pdf"):
                pdf_ok = True
                cargables += 1
            entradas.append(
                {
                    "id": _id,
                    "nombre_archivo": nombre,
                    "ruta_relativa": ruta_rel or None,
                    "valido_para_envio": valido_cfg,
                    "detalle": diag,
                    "pdf_valido": pdf_ok,
                }
            )
        loaded = get_adjuntos_fijos_por_caso(db, tipo_caso) if db is not None else []
        por_caso[tipo_caso] = {
            "base_dir_adjuntos": base_dir,
            "entradas_en_bd": len(lista),
            "entradas": entradas,
            "archivos_cargables_count": cargables,
            "archivos_cargados_por_servicio": len(loaded),
        }

    loaded_d1 = get_adjuntos_fijos_por_caso(db, "dias_1_retraso") if db is not None else []
    segundo_pdf_d1 = bool(global_diag.get("carga_ok_servicio")) or any(
        _bytes_es_pdf_valido(b) for _, b in loaded_d1
    )

    return {
        "notificaciones_paquete_estricto": paquete_estricto,
        "directorio_trabajo_cwd": cwd,
        "adjunto_fijo_cobranza_base_dir_env": (adj_base or "").strip() or None,
        "base_dir_adjuntos_por_caso": base_dir_por_caso,
        "adjunto_global_cobranza": global_diag,
        "adjuntos_fijos_por_caso": por_caso,
        "resumen": {
            "segundo_pdf_disponible_para_dias_1_retraso": segundo_pdf_d1,
            "texto": (
                "Con NOTIFICACIONES_PAQUETE_ESTRICTO=true hace falta Carta_Cobranza.pdf + al menos un PDF fijo valido. "
                "Ese segundo PDF puede venir del adjunto global o de la pestaña 3 para dias_1_retraso; deben existir en disco (Render: volumen persistente)."
            ),
        },
    }
