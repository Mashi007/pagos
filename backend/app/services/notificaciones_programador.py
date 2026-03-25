# -*- coding: utf-8 -*-
"""
Envio automatico de notificaciones por hora configurada (campo programador en notificaciones_envios).

- Zona: America/Caracas (igual que el scheduler).
- Por cada criterio (PAGO_* , PREJUDICIAL) la hora HH:MM del cuadro dispara una vez por dia
  ese lote filtrado (deduplicacion en configuracion).
- Si programador falta o es invalido, se usa 01:00 (compatibilidad con el antiguo job unico).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Tuple

from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from app.models.configuracion import Configuracion

logger = logging.getLogger(__name__)

CLAVE_DEDUP = "notificaciones_programador_ultimo"
TZ = ZoneInfo("America/Caracas")
# Antes el envio masivo era a las 01:00 fijas; configs sin programador siguen ese horario.
DEFAULT_HM: Tuple[int, int] = (1, 0)

GLOBAL_KEYS = frozenset({"modo_pruebas", "email_pruebas", "emails_pruebas"})


def _slot_key(fecha: str, hm: Tuple[int, int]) -> str:
    return f"{fecha}|{hm[0]:02d}:{hm[1]:02d}"


def parse_programador_hm(raw: Any) -> Tuple[int, int]:
    if raw is None:
        return DEFAULT_HM
    s = str(raw).strip()
    if not s:
        return DEFAULT_HM
    s = s.replace(".", ":")
    parts = s.split(":")
    try:
        h = int(parts[0]) % 24
        m = int(parts[1]) % 60 if len(parts) > 1 else 0
        return (h, m)
    except (ValueError, TypeError, IndexError):
        return DEFAULT_HM


def _load_dedup(db: Session) -> Dict[str, str]:
    try:
        row = db.get(Configuracion, CLAVE_DEDUP)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                m = data.get("por_tipo")
                if isinstance(m, dict):
                    return {str(k): str(v) for k, v in m.items()}
    except json.JSONDecodeError as e:
        logger.warning("notificaciones_programador_ultimo: JSON invalido: %s", e)
    except Exception as e:
        logger.exception("_load_dedup: %s", e)
    return {}


def _save_dedup(db: Session, m: Dict[str, str]) -> None:
    body = {"v": 1, "por_tipo": m}
    valor = json.dumps(body, ensure_ascii=False)
    row = db.get(Configuracion, CLAVE_DEDUP)
    if row:
        row.valor = valor
    else:
        db.add(Configuracion(clave=CLAVE_DEDUP, valor=valor))


def _config_tiene_coincidencia_hora(config: dict, hm: Tuple[int, int]) -> bool:
    for k, v in config.items():
        if k in GLOBAL_KEYS or not isinstance(v, dict):
            continue
        if v.get("habilitado", True) is False:
            continue
        if parse_programador_hm(v.get("programador")) == hm:
            return True
    return False


def _item_entra(
    item: dict,
    get_tipo: Callable[[dict], str],
    config: dict,
    hm_now: Tuple[int, int],
    fecha_str: str,
    dedup: Dict[str, str],
) -> bool:
    tipo = get_tipo(item)
    cfg = config.get(tipo) or {}
    if cfg.get("habilitado", True) is False:
        return False
    phm = parse_programador_hm(cfg.get("programador"))
    if phm != hm_now:
        return False
    sk = _slot_key(fecha_str, phm)
    if dedup.get(tipo) == sk:
        return False
    return True


def ejecutar_envios_por_programador(db: Session) -> Dict[str, Any]:
    """
    Ejecuta envios para items cuya hora programador coincide con la hora actual en Caracas,
    una vez por dia por tipo (dedup).
    """
    from app.api.v1.endpoints.notificaciones import get_notificaciones_tabs_data
    from app.services.notificaciones_envios_store import get_notificaciones_envios_dict
    from app.api.v1.endpoints.notificaciones_tabs import (
        _enviar_correos_items,
        _tipo_dia_pago,
        _tipo_prejudicial,
        _tipo_previas,
        _tipo_retrasadas,
    )

    config = get_notificaciones_envios_dict(db)
    now = datetime.now(TZ)
    hm = (now.hour, now.minute)
    fecha_str = now.date().isoformat()

    if not _config_tiene_coincidencia_hora(config, hm):
        return {"skipped": True, "motivo": "ninguna_hora_coincide", "hm_caracas": f"{hm[0]:02d}:{hm[1]:02d}"}

    dedup = _load_dedup(db)
    data = get_notificaciones_tabs_data(db)

    asunto_p = "Recordatorio: cuota por vencer - Rapicredit"
    cuerpo_p = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le recordamos que tiene una cuota por vencer.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "Número de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago a tiempo.\n\n"
        "Saludos,\nRapicredit"
    )
    asunto_h = "Vencimiento hoy: cuota de pago - Rapicredit"
    cuerpo_h = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le informamos que su cuota vence HOY.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "Número de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago hoy.\n\n"
        "Saludos,\nRapicredit"
    )
    asunto_r = "Cuenta con cuota atrasada - Rapicredit"
    cuerpo_r = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le recordamos que tiene una cuota en mora.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "Número de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor regularice su pago lo antes posible.\n\n"
        "Saludos,\nRapicredit"
    )
    asunto_pre = "Aviso prejudicial - Rapicredit"
    cuerpo_pre = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le informamos que su cuenta presenta varias cuotas en mora.\n"
        "Fecha de vencimiento de referencia: {fecha_vencimiento}\n"
        "Cuota de referencia: {numero_cuota}\n"
        "Monto de referencia: {monto}\n\n"
        "Por favor contacte a la entidad para regularizar su situación.\n\n"
        "Saludos,\nRapicredit"
    )

    lotes: List[Tuple[str, List[dict], str, str, Callable[[dict], str]]] = [
        (
            "previas",
            data["dias_5"] + data["dias_3"] + data["dias_1"],
            asunto_p,
            cuerpo_p,
            _tipo_previas,
        ),
        ("dia_pago", data["hoy"], asunto_h, cuerpo_h, _tipo_dia_pago),
        (
            "retrasadas",
            data["dias_1_retraso"] + data["dias_3_retraso"] + data["dias_5_retraso"],
            asunto_r,
            cuerpo_r,
            _tipo_retrasadas,
        ),
        ("prejudicial", data["prejudicial"], asunto_pre, cuerpo_pre, _tipo_prejudicial),
    ]

    total_e = total_f = total_se = total_oc = total_op = total_wok = total_wf = 0
    detalles: Dict[str, Any] = {}

    def filt(items: List[dict], get_tipo: Callable[[dict], str]) -> List[dict]:
        return [
            it
            for it in items
            if _item_entra(it, get_tipo, config, hm, fecha_str, dedup)
        ]

    for nombre, items_all, asunto, cuerpo, get_tipo in lotes:
        items_f = filt(items_all, get_tipo)
        if not items_f:
            continue
        r = _enviar_correos_items(items_f, asunto, cuerpo, config, get_tipo, db)
        detalles[nombre] = r
        total_e += int(r.get("enviados", 0) or 0)
        total_f += int(r.get("fallidos", 0) or 0)
        total_se += int(r.get("sin_email", 0) or 0)
        total_oc += int(r.get("omitidos_config", 0) or 0)
        total_op += int(r.get("omitidos_paquete_incompleto", 0) or 0)
        total_wok += int(r.get("enviados_whatsapp", 0) or 0)
        total_wf += int(r.get("fallidos_whatsapp", 0) or 0)
        sk = _slot_key(fecha_str, hm)
        for it in items_f:
            dedup[get_tipo(it)] = sk

    if detalles:
        _save_dedup(db, dedup)
        try:
            db.commit()
        except Exception as e:
            logger.exception("ejecutar_envios_por_programador commit dedup: %s", e)
            db.rollback()

    return {
        "skipped": False,
        "hm_caracas": f"{hm[0]:02d}:{hm[1]:02d}",
        "fecha_caracas": fecha_str,
        "enviados": total_e,
        "fallidos": total_f,
        "sin_email": total_se,
        "omitidos_config": total_oc,
        "omitidos_paquete_incompleto": total_op,
        "enviados_whatsapp": total_wok,
        "fallidos_whatsapp": total_wf,
        "detalles": detalles,
    }
