# -*- coding: utf-8 -*-
'''
Watchdog que reanuda lotes de notificaciones interrumpidos.

Un lote (COBRANZAS_EXCEL: ~600 correos SMTP secuenciales) vive en un hilo del worker.
Si el worker muere a mitad -- reciclado por --max-requests, deploy, OOM -- el resumen
queda en_proceso y el resto de la lista nunca sale. Este watchdog detecta ese estado
y relanza el mismo caso. El pipeline omite a quien ya recibio correo con exito hoy
(_sets_ya_enviados_exito_hoy), por lo que reanudar no duplica envios.

No es un cron de negocio: solo continua un lote que un humano ya inicio por API
(origen api_*), dentro de la misma fecha de negocio (America/Caracas) y con tope de
reintentos diarios.
'''
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import date, datetime, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

from app.services.cuota_estado import TZ_NEGOCIO, hoy_negocio

logger = logging.getLogger(__name__)

# El lote refresca heartbeat ~cada 1.5 s mientras envia. 150 s sin latido significa
# worker muerto: un correo SMTP lento tarda segundos, no minutos.
UMBRAL_HEARTBEAT_MUERTO_SEG = 150.0
INTERVALO_CHEQUEO_SEG = 30.0
MAX_REANUDACIONES_POR_DIA = 12
CLAVE_REANUDACIONES = "notificaciones_lote_reanudaciones"

_MARCAS_INTERRUPCION = (
    "interrump",
    "worker_recycle",
    "worker_interrupted",
    "stale",
    "shutdown",
)

_stop = threading.Event()
_thread: Optional[threading.Thread] = None
_lock = threading.Lock()


def _a_utc(iso_txt) -> Optional[datetime]:
    txt = str(iso_txt or "").strip()
    if not txt:
        return None
    try:
        dt = datetime.fromisoformat(txt.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _edad_segundos(iso_txt) -> Optional[float]:
    dt = _a_utc(iso_txt)
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds()


def _fecha_negocio(iso_txt) -> Optional[date]:
    dt = _a_utc(iso_txt)
    if dt is None:
        return None
    return dt.astimezone(ZoneInfo(TZ_NEGOCIO)).date()


def _tipos_caso_validos() -> frozenset:
    from app.api.v1.endpoints.notificaciones_tabs.routes import TIPOS_CASO_MANUAL

    return frozenset(TIPOS_CASO_MANUAL)


def lote_reanudable(ultimo) -> Optional[Tuple[str, str, int, int]]:
    '''
    (tipo_caso, motivo, procesados, total) si el lote quedo a medias y se puede
    continuar; None si no hay nada que reanudar.
    '''
    if not isinstance(ultimo, dict) or ultimo.get("omitido"):
        return None
    if not str(ultimo.get("origen") or "").strip().startswith("api_"):
        return None
    det = ultimo.get("detalles") if isinstance(ultimo.get("detalles"), dict) else {}
    tipo = str(ultimo.get("tipo_caso") or det.get("tipo_caso") or "").strip()
    if not tipo:
        return None
    try:
        total = int(ultimo.get("total_en_lista") or det.get("total_en_lista") or 0)
        procesados = int(det.get("procesados") or 0)
    except (TypeError, ValueError):
        return None
    if total <= 0 or procesados >= total:
        return None
    if _fecha_negocio(ultimo.get("inicio_utc")) != hoy_negocio():
        return None

    estado = str(ultimo.get("estado") or "").strip().lower()
    if estado == "en_proceso" or bool(det.get("en_proceso")):
        edad = _edad_segundos(ultimo.get("heartbeat_utc") or ultimo.get("inicio_utc"))
        if edad is not None and edad >= UMBRAL_HEARTBEAT_MUERTO_SEG:
            return (tipo, "sin latido hace %.0fs" % edad, procesados, total)
        return None

    error = str(ultimo.get("error") or "").strip().lower()
    if error and any(marca in error for marca in _MARCAS_INTERRUPCION):
        return (tipo, "lote cerrado por interrupcion del worker", procesados, total)
    return None


def _leer_intentos(db, hoy: date) -> int:
    from app.models.configuracion import Configuracion

    row = db.get(Configuracion, CLAVE_REANUDACIONES)
    if not row or not row.valor:
        return 0
    try:
        data = json.loads(row.valor)
    except (TypeError, ValueError):
        return 0
    if not isinstance(data, dict):
        return 0
    if str(data.get("fecha_negocio") or "") != hoy.isoformat():
        return 0
    try:
        return int(data.get("intentos") or 0)
    except (TypeError, ValueError):
        return 0


def _registrar_intento(db, hoy: date, tipo: str, intentos: int) -> None:
    from app.models.configuracion import Configuracion

    valor = json.dumps(
        {
            "fecha_negocio": hoy.isoformat(),
            "tipo_caso": tipo,
            "intentos": intentos,
            "ultimo_intento_utc": datetime.now(timezone.utc).isoformat(),
        },
        ensure_ascii=False,
    )
    row = db.get(Configuracion, CLAVE_REANUDACIONES)
    if row:
        row.valor = valor
    else:
        db.add(Configuracion(clave=CLAVE_REANUDACIONES, valor=valor))


def revisar_y_reanudar_una_vez() -> Optional[str]:
    '''Un ciclo de revision. Devuelve el tipo_caso relanzado, o None.'''
    from app.core.database import SessionLocal
    from app.services.notificaciones_envio_batch_resumen import (
        get_ultimo_envio_batch_dict,
    )
    from app.services.notificaciones_envio_bg_runner import (
        claves_activas,
        spawn_envio_bg,
    )

    db = SessionLocal()
    try:
        candidato = lote_reanudable(get_ultimo_envio_batch_dict(db))
        if candidato is None:
            return None
        tipo, motivo, procesados, total = candidato
        if tipo not in _tipos_caso_validos():
            logger.warning(
                "[notif_watchdog] tipo_caso=%s no es un caso manual valido; sin reanudar",
                tipo,
            )
            return None

        clave = "caso:%s" % tipo
        if clave in claves_activas():
            # Este worker ya lo esta enviando: el latido viejo es de un envio lento.
            return None

        hoy = hoy_negocio()
        intentos = _leer_intentos(db, hoy)
        if intentos >= MAX_REANUDACIONES_POR_DIA:
            logger.error(
                "[notif_watchdog] tope de %s reanudaciones alcanzado hoy para %s; "
                "revisar por que el worker sigue muriendo (quedan %s de %s)",
                MAX_REANUDACIONES_POR_DIA,
                tipo,
                total - procesados,
                total,
            )
            return None

        _registrar_intento(db, hoy, tipo, intentos + 1)
        db.commit()

        from app.api.v1.endpoints.notificaciones.routes import (
            _tarea_enviar_caso_manual,
        )

        inicio = datetime.now(timezone.utc).isoformat()
        token = str(uuid.uuid4())
        if not spawn_envio_bg(
            clave, _tarea_enviar_caso_manual, tipo, None, inicio, token
        ):
            return None
        logger.warning(
            "[notif_watchdog] Lote %s reanudado (%s). Faltaban %s de %s; los ya "
            "enviados hoy se omiten. intento_del_dia=%s token=%s",
            tipo,
            motivo,
            total - procesados,
            total,
            intentos + 1,
            token[:12],
        )
        return tipo
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        logger.exception("[notif_watchdog] fallo al evaluar reanudacion de lote")
        return None
    finally:
        db.close()


def _loop() -> None:
    logger.info(
        "[notif_watchdog] activo: revisa cada %.0fs y reanuda lotes sin latido > %.0fs",
        INTERVALO_CHEQUEO_SEG,
        UMBRAL_HEARTBEAT_MUERTO_SEG,
    )
    while not _stop.wait(INTERVALO_CHEQUEO_SEG):
        revisar_y_reanudar_una_vez()
    logger.info("[notif_watchdog] detenido")


def iniciar_watchdog_lotes_notificacion() -> bool:
    '''Arranca el watchdog. True si quedo corriendo por esta llamada.'''
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return False
        _stop.clear()
        _thread = threading.Thread(
            target=_loop, name="notif-lote-watchdog", daemon=True
        )
        _thread.start()
        return True


def detener_watchdog_lotes_notificacion() -> None:
    '''Detiene el watchdog (usar antes de drenar lotes en shutdown).'''
    _stop.set()
    with _lock:
        hilo = _thread
    if hilo is not None and hilo.is_alive():
        hilo.join(timeout=5.0)
