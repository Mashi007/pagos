"""Overrides itmaster solo para tabla Desempeño en /pagos/cobranzas (GET universo/analisis).

No modifica extracto ACTIVO, conciliación ni dashboard; solo ``cobranzas_pagos_confirmados_manual``.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cobranzas_pagos_confirmados_manual import CobranzasPagosConfirmadosManual


def _parse_fecha(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    s = str(val).strip()[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def propagar_manual_acumulado_mes_a_columna_hoy(
    lecturas: list[dict[str, Any]], *, hoy: date, manual: Dict[date, CobranzasPagosConfirmadosManual]
) -> None:
    """Coherencia UI Cobranzas: manual del 1° del mes (Acumulado) también netea la columna Hoy.

    Solo afecta lecturas en memoria para GET universo/analisis. La fila Hoy sigue sumando
    confirmados automáticos (p. ej. residual + hoy); el estimativo manual del mes no se pierde.
    """
    mes_inicio = date(hoy.year, hoy.month, 1)
    if hoy.day == 1 or mes_inicio not in manual or hoy in manual:
        return
    row_mes = manual[mes_inicio]
    for L in lecturas:
        fd = _parse_fecha(L.get("fecha"))
        if fd != hoy:
            continue
        auto_c = int(L.get("cantidad_automatica") if L.get("cantidad_automatica") is not None else L.get("cantidad") or 0)
        auto_m = round(
            float(
                L.get("monto_usd_automatico")
                if L.get("monto_usd_automatico") is not None
                else L.get("monto_usd") or 0
            ),
            2,
        )
        if L.get("cantidad_automatica") is None:
            L["cantidad_automatica"] = auto_c
        if L.get("monto_usd_automatico") is None:
            L["monto_usd_automatico"] = auto_m
        L["cantidad"] = int(row_mes.cantidad or 0) + auto_c
        L["monto_usd"] = round(float(row_mes.monto_usd or 0) + auto_m, 2)
        L["manual_override"] = True
        L["manual_mes_inicio_aplicado"] = mes_inicio.isoformat()
        break


def load_manual_pagos_confirmados_map(db: Session) -> Dict[date, CobranzasPagosConfirmadosManual]:
    rows = db.execute(select(CobranzasPagosConfirmadosManual)).scalars().all()
    out: Dict[date, CobranzasPagosConfirmadosManual] = {}
    for row in rows:
        if row.fecha_lectura is not None:
            out[row.fecha_lectura] = row
    return out


def aplicar_manual_a_lecturas_pagos_confirmados(
    db: Session, lecturas: list[dict[str, Any]]
) -> None:
    """Sustituye cantidad/monto_usd donde hay override; conserva valores automáticos en *_automatico."""
    manual = load_manual_pagos_confirmados_map(db)
    for L in lecturas:
        fd = _parse_fecha(L.get("fecha"))
        if L.get("cantidad_automatica") is not None and L.get(
            "monto_usd_automatico"
        ) is not None:
            auto_cant = int(L.get("cantidad_automatica") or 0)
            auto_monto = round(float(L.get("monto_usd_automatico") or 0), 2)
        else:
            auto_cant = int(L.get("cantidad") or 0)
            auto_monto = round(float(L.get("monto_usd") or 0), 2)
            L["cantidad_automatica"] = auto_cant
            L["monto_usd_automatico"] = auto_monto
        row = manual.get(fd) if fd else None
        if row is not None:
            L["cantidad"] = int(row.cantidad or 0)
            L["monto_usd"] = round(float(row.monto_usd or 0), 2)
            L["manual_override"] = True
        else:
            L["cantidad"] = auto_cant
            L["monto_usd"] = auto_monto
            L["manual_override"] = False


def upsert_manual_pagos_confirmados(
    db: Session,
    *,
    fecha_lectura: date,
    cantidad: int,
    monto_usd: float,
    updated_by: str,
) -> None:
    cantidad = max(0, int(cantidad))
    monto_usd = round(max(0.0, float(monto_usd)), 2)
    row = db.get(CobranzasPagosConfirmadosManual, fecha_lectura)
    if row is None:
        row = CobranzasPagosConfirmadosManual(
            fecha_lectura=fecha_lectura,
            cantidad=cantidad,
            monto_usd=monto_usd,
            updated_by=(updated_by or "")[:255],
        )
        db.add(row)
    else:
        row.cantidad = cantidad
        row.monto_usd = monto_usd
        row.updated_by = (updated_by or "")[:255]
    db.commit()


def delete_manual_pagos_confirmados(db: Session, *, fecha_lectura: date) -> bool:
    row = db.get(CobranzasPagosConfirmadosManual, fecha_lectura)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
