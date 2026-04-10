# -*- coding: utf-8 -*-
"""
Campos legacy `programador` en notificaciones_envios: parseo y normalizacion al guardar (PUT).

El valor `programador` (hora en JSON) es solo metadato / compatibilidad con la UI: ningun job del
servidor lee esa hora para enviar correos. Los envios de mora son solo manuales (POST desde la UI).
No hay ejecucion periodica de notificaciones por hora en este modulo. Zona America/Caracas donde aplique.
"""
from __future__ import annotations

from typing import Any, Tuple

# Valor por defecto si falta programador en JSON (compatibilidad con datos antiguos).
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


def snap_hm_to_quarter_hour(hm: Tuple[int, int]) -> Tuple[int, int]:
    """Redondea al cuarto de hora mas cercano (0, 15, 30, 45). Usado al persistir config."""
    total = (hm[0] % 24) * 60 + (hm[1] % 60)
    rounded = ((total + 7) // 15) * 15
    h2 = (rounded // 60) % 24
    m2 = rounded % 60
    return (h2, m2)


def formato_hm_programador(hm: Tuple[int, int]) -> str:
    return f"{hm[0]:02d}:{hm[1]:02d}"


def normalizar_payload_envios_programadores(payload: dict) -> None:
    """
    Al guardar PUT /configuracion/notificaciones/envios, alinea campos `programador`
    a cuartos de hora (solo formato JSON legacy). Mutacion in-place.
    """
    if not isinstance(payload, dict):
        return
    for k, v in payload.items():
        if k in GLOBAL_KEYS or k == "masivos_campanas" or not isinstance(v, dict):
            continue
        if "programador" in v:
            ph = snap_hm_to_quarter_hour(parse_programador_hm(v.get("programador")))
            v["programador"] = formato_hm_programador(ph)
    raw = payload.get("masivos_campanas")
    if isinstance(raw, list):
        for camp in raw:
            if isinstance(camp, dict) and "programador" in camp:
                ph = snap_hm_to_quarter_hour(parse_programador_hm(camp.get("programador")))
                camp["programador"] = formato_hm_programador(ph)
