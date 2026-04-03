"""
Resolucion de monto USD vs BS para altas de pago (todas las vias que usan PagoCreate o equivalente).

- USD: monto_pagado se interpreta en dolares; sin conversion ni lista Bs.
- BS: exige cliente en BD; cedula en lista autorizada (cedulas_reportar_bs) salvo montos en Bs.
  >= settings.PAGOS_BS_MONTO_EXENTO_LISTA_CEDULA.
  monto_pagado se interpreta en bolivares; tasa desde BD por fecha de pago o tasa_cambio_manual si no hay en BD.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cliente import Cliente
from app.services.cobros.cedula_reportar_bs_service import (
    cedula_autorizada_para_bs,
    cedula_coincide_autorizados_bs,
    load_autorizados_bs_claves,
    normalize_cedula_lookup_key,
)
from app.services.tasa_cambio_service import convertir_bs_a_usd, obtener_tasa_por_fecha

def normalizar_moneda_registro(raw: Optional[str]) -> str:
    u = (raw or "USD").strip().upper()
    if u == "USDT":
        u = "USD"
    if u not in ("USD", "BS"):
        raise HTTPException(
            status_code=400,
            detail="moneda_registro debe ser USD o BS",
        )
    return u


def cliente_existe_upper(db: Session, cedula_upper: str) -> bool:
    if not cedula_upper:
        return False
    r = db.execute(
        select(Cliente.id).where(func.upper(Cliente.cedula) == cedula_upper)
    ).first()
    return r is not None


def resolver_monto_registro_pago(
    db: Session,
    *,
    cedula_normalizada: str,
    fecha_pago: date,
    monto_pagado: Decimal,
    moneda_registro: str,
    tasa_cambio_manual: Optional[Decimal],
    autorizados_bs: Optional[frozenset[str]] = None,
) -> Tuple[Decimal, str, Optional[Decimal], Optional[Decimal], Optional[date]]:
    """
    Devuelve (monto_usd, moneda_final, monto_bs, tasa_aplicada, fecha_tasa_ref).

    Si moneda_registro es USD: monto_pagado ya es USD.
    Si es BS: monto_pagado es monto en bolivares; se convierte a USD con la tasa.
    """
    moneda = normalizar_moneda_registro(moneda_registro)
    if moneda == "USD":
        return (monto_pagado, "USD", None, None, None)

    if not cliente_existe_upper(db, cedula_normalizada):
        raise HTTPException(
            status_code=404,
            detail="No existe cliente con esa cedula; no se puede registrar en bolivares.",
        )
    raw_key = (cedula_normalizada or "").replace("-", "").strip()
    if autorizados_bs is None:
        ok = cedula_autorizada_para_bs(db, raw_key)
    else:
        norm = normalize_cedula_lookup_key(raw_key)
        ok = cedula_coincide_autorizados_bs(norm, autorizados_bs)
    if not ok and float(monto_pagado) < settings.PAGOS_BS_MONTO_EXENTO_LISTA_CEDULA:
        raise HTTPException(
            status_code=400,
            detail="La cedula no esta autorizada para pagos en bolivares.",
        )

    tasa_obj = obtener_tasa_por_fecha(db, fecha_pago)
    tasa: Optional[float] = None
    if tasa_obj is not None:
        tasa = float(tasa_obj.tasa_oficial)
    if tasa is None and tasa_cambio_manual is not None:
        tasa = float(tasa_cambio_manual)
    if tasa is None or tasa <= 0:
        raise HTTPException(
            status_code=400,
            detail="No hay tasa de cambio para la fecha de pago. Ingrese la tasa en Administracion o indique tasa manual en el formulario.",
        )

    monto_bs = float(monto_pagado)
    try:
        monto_usd = convertir_bs_a_usd(monto_bs, tasa)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return (
        Decimal(str(round(monto_usd, 2))),
        "BS",
        Decimal(str(round(monto_bs, 2))),
        Decimal(str(round(tasa, 6))),
        fecha_pago,
    )


def preload_autorizados_bs(db: Session) -> frozenset[str]:
    """Una consulta por lote (batch) para validar lista Bs."""
    return load_autorizados_bs_claves(db)
