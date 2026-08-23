# -*- coding: utf-8 -*-
"""Cursor round-robin de ESTADO_CUENTA: tope proactivo 600/dia (America/Caracas)."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.configuracion import Configuracion
from app.services.cuota_estado import hoy_negocio

logger = logging.getLogger(__name__)

CLAVE_CURSOR = "estado_cuenta_envio_cursor"
MAX_ENVIOS_DIARIOS = 600
TIPO_CASO = "ESTADO_CUENTA"


def _leer(db: Session) -> Dict[str, Any]:
    row = db.get(Configuracion, CLAVE_CURSOR)
    if not row or not row.valor:
        return {}
    try:
        data = json.loads(row.valor)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _guardar(db: Session, data: Dict[str, Any]) -> None:
    valor = json.dumps(data, ensure_ascii=False)
    row = db.get(Configuracion, CLAVE_CURSOR)
    if row is None:
        for obj in list(db.new):
            if isinstance(obj, Configuracion) and obj.clave == CLAVE_CURSOR:
                row = obj
                break
    if row is None:
        row = (
            db.query(Configuracion)
            .filter(Configuracion.clave == CLAVE_CURSOR)
            .first()
        )
    if row is not None:
        row.valor = valor
    else:
        db.add(Configuracion(clave=CLAVE_CURSOR, valor=valor))


def obtener_cursor_estado_cuenta(db: Session) -> Dict[str, Any]:
    """
    Estado del ciclo: ultimo prestamo enviado y cupo del dia de negocio.
    Si cambia el dia (Caracas), reinicia enviados_hoy pero conserva el cursor.
    """
    hoy = hoy_negocio().isoformat()
    raw = _leer(db)
    fecha = str(raw.get("fecha_negocio") or "").strip()
    enviados = int(raw.get("enviados_hoy") or 0)
    last_id = raw.get("ultimo_prestamo_id")
    try:
        last_id_int = int(last_id) if last_id is not None else None
    except (TypeError, ValueError):
        last_id_int = None

    if fecha != hoy:
        enviados = 0
        fecha = hoy

    return {
        "fecha_negocio": fecha,
        "enviados_hoy": max(0, enviados),
        "ultimo_prestamo_id": last_id_int,
        "max_diarios": MAX_ENVIOS_DIARIOS,
        "cupo_restante": max(0, MAX_ENVIOS_DIARIOS - max(0, enviados)),
    }


def persistir_cursor_estado_cuenta(
    db: Session,
    *,
    ultimo_prestamo_id: Optional[int],
    enviados_hoy: int,
    fecha_negocio: Optional[str] = None,
) -> Dict[str, Any]:
    hoy = (fecha_negocio or hoy_negocio().isoformat()).strip()
    data = {
        "fecha_negocio": hoy,
        "enviados_hoy": max(0, int(enviados_hoy)),
        "ultimo_prestamo_id": (
            int(ultimo_prestamo_id) if ultimo_prestamo_id is not None else None
        ),
        "max_diarios": MAX_ENVIOS_DIARIOS,
    }
    _guardar(db, data)
    data["cupo_restante"] = max(0, MAX_ENVIOS_DIARIOS - data["enviados_hoy"])
    return data
