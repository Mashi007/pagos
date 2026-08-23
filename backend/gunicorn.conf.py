# -*- coding: utf-8 -*-
'''
Configuracion de Gunicorn del backend. Gunicorn la carga sola por llamarse
`gunicorn.conf.py` y estar en el directorio de trabajo (rootDir=backend en Render).

Existe para que los lotes de notificaciones no se corten. Un lote COBRANZAS_EXCEL
(~600 correos SMTP secuenciales, 30+ min) corre en un hilo dentro del worker, y hasta
ahora dos mecanismos de Gunicorn lo mataban a mitad:

1. WORKER TIMEOUT -> SIGABRT (exit 134). UvicornWorker solo refresca el latido del
   worker desde el event loop cada `timeout_notify` segundos; bajo carga alta eso fallo
   y corto el lote en 597/615 (31-jul-2026 12:59 UTC). Lo cubre `_keepalive_lotes`.
2. Reciclado por `--max-requests`, que descarta el worker con el hilo dentro
   (incidentes 45/618 y 258/618). Lo cubre `post_fork`.

Gunicorn aplica los flags del Start Command DESPUES de este archivo, asi que los valores
de modulo no alcanzan mientras el Dashboard conserve `--max-requests`; por eso los hooks
`when_ready` y `post_fork` corrigen en caliente lo que llega por CLI.

Escape hatch: GUNICORN_PERMITIR_MAX_REQUESTS=true respeta el valor del Start Command.
'''
import os
import sys
import threading
import time

GRACEFUL_TIMEOUT_MINIMO = 900
KEEPALIVE_INTERVALO_SEG = 30.0


def _flag_activa(nombre: str) -> bool:
    return str(os.environ.get(nombre, "")).strip().lower() in ("1", "true", "yes", "si")


PERMITIR_MAX_REQUESTS = _flag_activa("GUNICORN_PERMITIR_MAX_REQUESTS")

# Valores canonicos (aplican cuando el Start Command no trae el flag equivalente).
bind = "0.0.0.0:%s" % os.environ.get("PORT", "10000")
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 920
graceful_timeout = GRACEFUL_TIMEOUT_MINIMO
max_requests = 0
max_requests_jitter = 0


def when_ready(server):
    '''Eleva graceful_timeout si el Start Command trae un valor que corta lotes SMTP.'''
    try:
        actual = int(getattr(server.cfg, "graceful_timeout", 0) or 0)
        if actual < GRACEFUL_TIMEOUT_MINIMO:
            server.cfg.set("graceful_timeout", GRACEFUL_TIMEOUT_MINIMO)
            server.log.warning(
                "[gunicorn.conf] graceful_timeout=%ss del Start Command es insuficiente para "
                "drenar lotes de notificaciones; elevado a %ss.",
                actual,
                GRACEFUL_TIMEOUT_MINIMO,
            )
    except Exception as e:
        try:
            server.log.warning("[gunicorn.conf] no se pudo ajustar graceful_timeout: %s", e)
        except Exception:
            pass


def _keepalive_lotes(server, worker):
    '''
    Refresca el latido del worker ante el arbiter mientras hay un lote de
    notificaciones enviando o un «Guardar y cerrar» de revisión en segundo plano.

    Sin esto, el arbiter interpreta el silencio del event loop como worker colgado y
    manda SIGABRT, matando el hilo. Solo actua con trabajo BG activo: si el worker
    se cuelga de verdad y no hay job, el watchdog de Gunicorn sigue operando igual.
    '''
    while getattr(worker, "alive", True):
        time.sleep(KEEPALIVE_INTERVALO_SEG)
        try:
            # sys.modules en vez de import: no forzamos la carga de la app desde aqui.
            activo = False
            runner = sys.modules.get("app.services.notificaciones_envio_bg_runner")
            if runner is not None and getattr(runner, "hay_envios_activos", None):
                try:
                    if runner.hay_envios_activos():
                        activo = True
                except Exception:
                    pass
            if not activo:
                cerrar = sys.modules.get("app.services.revision_manual_cerrar_bg")
                if cerrar is not None and getattr(cerrar, "hay_cierres_activos", None):
                    try:
                        if cerrar.hay_cierres_activos():
                            activo = True
                    except Exception:
                        pass
            if not activo:
                continue
            worker.notify()
        except Exception:
            # Nunca romper el worker por el keepalive.
            pass


def post_fork(server, worker):
    '''Neutraliza el reciclado por peticiones y arranca el keepalive de lotes.'''
    try:
        hilo = threading.Thread(
            target=_keepalive_lotes,
            args=(server, worker),
            name="gunicorn-keepalive-notif",
            daemon=True,
        )
        hilo.start()
    except Exception as e:
        try:
            server.log.warning("[gunicorn.conf] no se pudo iniciar keepalive de lotes: %s", e)
        except Exception:
            pass

    if PERMITIR_MAX_REQUESTS:
        return
    try:
        limite = int(getattr(worker, "max_requests", 0) or 0)
    except (TypeError, ValueError):
        limite = 0
    venia_del_cli = 0 < limite < sys.maxsize
    try:
        worker.max_requests = sys.maxsize
        # UvicornWorker copia max_requests a su Config como limit_max_requests y lo
        # revisa en cada tick; sin esto el worker sale igual aunque gunicorn no lo mate.
        cfg_uvicorn = getattr(worker, "config", None)
        if cfg_uvicorn is not None and hasattr(cfg_uvicorn, "limit_max_requests"):
            cfg_uvicorn.limit_max_requests = None
        if venia_del_cli:
            server.log.warning(
                "[gunicorn.conf] --max-requests=%s ignorado: el reciclado del worker mata los "
                "hilos de envio de notificaciones a mitad de lote. Quitar el flag del Start "
                "Command en Render, o usar GUNICORN_PERMITIR_MAX_REQUESTS=true para respetarlo.",
                limite,
            )
    except Exception as e:
        try:
            server.log.warning("[gunicorn.conf] no se pudo desactivar max_requests: %s", e)
        except Exception:
            pass
