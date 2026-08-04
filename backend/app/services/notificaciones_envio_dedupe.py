# -*- coding: utf-8 -*-
"""Deduplicación same-day de envíos de notificaciones (sin deps de FastAPI/SMTP)."""
from __future__ import annotations


def debe_omitir_ya_enviado(
    *,
    prestamo_id,
    cedula: str,
    tipo_tab: str,
    ya_pid: dict[str, set[int]],
    ya_ced: dict[str, set[str]],
) -> bool:
    """True si este ítem ya tuvo envío exitoso hoy para ``tipo_tab``.

    Con ``prestamo_id``: solo deduplica por préstamo. Un cliente con dos préstamos
    activos en el mismo listado (p. ej. 1 día de retraso / prejudicial) debe recibir
    ambos correos; omitir por cédula silenciaría el segundo préstamo y también
    rompería el reintento tras caída del worker a mitad de lote.

    Sin ``prestamo_id`` (MASIVOS / comunicación general): deduplica por cédula.
    """
    tt = (tipo_tab or "").strip()
    if not tt:
        return False
    pid_int = None
    if prestamo_id is not None:
        try:
            pid_int = int(prestamo_id)
        except (TypeError, ValueError):
            pid_int = None
    if pid_int is not None:
        return pid_int in ya_pid.get(tt, set())
    ced = (cedula or "").strip()
    return bool(ced) and ced in ya_ced.get(tt, set())


def registrar_envio_exito_en_sets(
    *,
    prestamo_id,
    cedula: str,
    tipo_tab: str,
    ya_pid: dict[str, set[int]],
    ya_ced: dict[str, set[str]],
) -> None:
    """Actualiza sets in-batch tras un SMTP exitoso (misma regla que la omisión)."""
    tt = (tipo_tab or "").strip()
    if not tt:
        return
    pid_int = None
    if prestamo_id is not None:
        try:
            pid_int = int(prestamo_id)
        except (TypeError, ValueError):
            pid_int = None
    if pid_int is not None:
        ya_pid.setdefault(tt, set()).add(pid_int)
        return
    ced = (cedula or "").strip()
    if ced:
        ya_ced.setdefault(tt, set()).add(ced)
