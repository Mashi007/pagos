# -*- coding: utf-8 -*-
"""Cola de lotes incompletos para continuar al dia siguiente (cupo Gmail / caidas)."""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.configuracion import Configuracion
from app.services.cuota_estado import hoy_negocio

logger = logging.getLogger(__name__)

CLAVE_LOTES_CONTINUAR = "notificaciones_lotes_continuar"


def _leer(db: Session) -> Dict[str, Any]:
    row = db.get(Configuracion, CLAVE_LOTES_CONTINUAR)
    if not row or not row.valor:
        return {"lotes": []}
    try:
        data = json.loads(row.valor)
    except (TypeError, ValueError):
        return {"lotes": []}
    if not isinstance(data, dict):
        return {"lotes": []}
    lotes = data.get("lotes")
    if not isinstance(lotes, list):
        data["lotes"] = []
    return data


def _guardar(db: Session, data: Dict[str, Any]) -> None:
    valor = json.dumps(data, ensure_ascii=False)
    row = db.get(Configuracion, CLAVE_LOTES_CONTINUAR)
    if row is None:
        for obj in list(db.new):
            if isinstance(obj, Configuracion) and obj.clave == CLAVE_LOTES_CONTINUAR:
                row = obj
                break
    if row is None:
        row = (
            db.query(Configuracion)
            .filter(Configuracion.clave == CLAVE_LOTES_CONTINUAR)
            .first()
        )
    if row is not None:
        row.valor = valor
    else:
        db.add(Configuracion(clave=CLAVE_LOTES_CONTINUAR, valor=valor))


def listar_lotes_continuar(db: Session) -> List[Dict[str, Any]]:
    data = _leer(db)
    out = []
    for item in data.get("lotes") or []:
        if isinstance(item, dict) and str(item.get("tipo_caso") or "").strip():
            out.append(item)
    return out


def upsert_lote_continuar(
    db: Session,
    *,
    tipo_caso: str,
    total_en_lista: int,
    procesados: int,
    enviados: int = 0,
    fallidos: int = 0,
    estado: str = "pausado_limite_gmail",
    fecha_negocio_inicio: Optional[str] = None,
    fecha_negocio_pausa: Optional[str] = None,
    inicio_utc: Optional[str] = None,
    motivo: Optional[str] = None,
) -> Dict[str, Any]:
    """Registra o actualiza el punto de corte de un lote incompleto."""
    tipo = str(tipo_caso or "").strip()
    if not tipo:
        raise ValueError("tipo_caso requerido")
    hoy = hoy_negocio().isoformat()
    data = _leer(db)
    lotes: List[Dict[str, Any]] = [
        x for x in (data.get("lotes") or []) if isinstance(x, dict)
    ]
    existente = None
    for i, item in enumerate(lotes):
        if str(item.get("tipo_caso") or "").strip() == tipo:
            existente = i
            break
    base = dict(lotes[existente]) if existente is not None else {}
    snap = {
        **base,
        "tipo_caso": tipo,
        "total_en_lista": int(total_en_lista or 0),
        "procesados": int(procesados or 0),
        "enviados": int(enviados or 0),
        "fallidos": int(fallidos or 0),
        "estado": str(estado or "pausado_limite_gmail").strip(),
        "fecha_negocio_inicio": str(
            fecha_negocio_inicio or base.get("fecha_negocio_inicio") or hoy
        ).strip(),
        "fecha_negocio_pausa": str(
            fecha_negocio_pausa or hoy
        ).strip(),
        "inicio_utc": inicio_utc or base.get("inicio_utc"),
        "motivo": (motivo or base.get("motivo") or "")[:2000] or None,
        "actualizado_utc": datetime.now(timezone.utc).isoformat(),
    }
    if existente is not None:
        lotes[existente] = snap
    else:
        lotes.append(snap)
    data["lotes"] = lotes
    data["actualizado_utc"] = datetime.now(timezone.utc).isoformat()
    _guardar(db, data)
    logger.info(
        "[notif_continuar] upsert tipo=%s estado=%s procesados=%s/%s inicio=%s pausa=%s",
        tipo,
        snap["estado"],
        snap["procesados"],
        snap["total_en_lista"],
        snap["fecha_negocio_inicio"],
        snap["fecha_negocio_pausa"],
    )
    return snap


def quitar_lote_continuar(db: Session, tipo_caso: str) -> bool:
    tipo = str(tipo_caso or "").strip()
    if not tipo:
        return False
    data = _leer(db)
    before = list(data.get("lotes") or [])
    after = [
        x
        for x in before
        if isinstance(x, dict) and str(x.get("tipo_caso") or "").strip() != tipo
    ]
    if len(after) == len(before):
        return False
    data["lotes"] = after
    data["actualizado_utc"] = datetime.now(timezone.utc).isoformat()
    _guardar(db, data)
    logger.info("[notif_continuar] quitado tipo=%s (lote completo)", tipo)
    return True


def obtener_lote_continuar(db: Session, tipo_caso: str) -> Optional[Dict[str, Any]]:
    tipo = str(tipo_caso or "").strip()
    for item in listar_lotes_continuar(db):
        if str(item.get("tipo_caso") or "").strip() == tipo:
            return item
    return None


def proximo_lote_reanudable_continuar(
    db: Session,
) -> Optional[Dict[str, Any]]:
    """
    Primer lote pendiente cuyo dia de pausa ya paso (America/Caracas).
    Prioriza pausado_limite_gmail; luego incompletos.
    """
    hoy = hoy_negocio()
    candidatos: List[Dict[str, Any]] = []
    for item in listar_lotes_continuar(db):
        try:
            total = int(item.get("total_en_lista") or 0)
            procesados = int(item.get("procesados") or 0)
        except (TypeError, ValueError):
            continue
        if total <= 0 or procesados >= total:
            continue
        raw_pausa = str(item.get("fecha_negocio_pausa") or "").strip()
        try:
            dia_pausa = date.fromisoformat(raw_pausa) if raw_pausa else None
        except ValueError:
            dia_pausa = None
        if dia_pausa is None:
            continue
        if hoy <= dia_pausa:
            continue
        candidatos.append(item)

    def _prio(it: Dict[str, Any]) -> tuple:
        est = str(it.get("estado") or "")
        # 0 = cupo gmail (prioridad), 1 = otros
        return (0 if "limite" in est or "pausado" in est else 1, str(it.get("fecha_negocio_pausa") or ""))

    if not candidatos:
        return None
    candidatos.sort(key=_prio)
    return candidatos[0]
