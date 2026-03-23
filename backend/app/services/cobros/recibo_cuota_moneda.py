"""
Moneda y montos para recibo PDF por cuota: USD (cartera / tabla de amortizacion) vs Bs.

Regla de negocio: el recibo muestra bolivares solo si la cedula esta en lista autorizada
para pagos en Bs Y el pago quedo registrado en Bs (moneda_registro BS con monto_bs_original).
En caso contrario se usa USD, alineado con monto_pagado y la amortizacion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.cobros.cedula_reportar_bs_service import cedula_autorizada_para_bs


@dataclass(frozen=True)
class ContextoReciboCuotaMoneda:
    moneda: str  # "USD" | "BS"
    monto_str: str
    saldo_inicial: str
    saldo_final: str
    tasa_cambio: Optional[float]


def contexto_moneda_montos_recibo_cuota(
    db: Session,
    prestamo: Prestamo,
    cuota: Cuota,
    pago: Optional[Pago],
) -> ContextoReciboCuotaMoneda:
    monto_cuota = float(cuota.monto or 0)
    total_pagado = float(cuota.total_pagado or 0)
    base_usd = total_pagado if total_pagado > 0 else monto_cuota

    ced = (getattr(prestamo, "cedula", "") or "").strip()
    autorizado_bs = cedula_autorizada_para_bs(db, ced) if ced else False
    moneda_reg = (pago.moneda_registro or "").strip().upper() if pago else ""

    saldo_i_usd = float(cuota.saldo_capital_inicial) if cuota.saldo_capital_inicial is not None else None
    saldo_f_usd = float(cuota.saldo_capital_final) if cuota.saldo_capital_final is not None else None

    puede_bs = (
        autorizado_bs
        and moneda_reg == "BS"
        and pago is not None
        and pago.monto_bs_original is not None
    )

    if puede_bs:
        m_bs = float(pago.monto_bs_original)
        tasa = float(pago.tasa_cambio_bs_usd) if pago.tasa_cambio_bs_usd is not None else None
        if tasa and tasa > 0 and saldo_i_usd is not None:
            si_bs = saldo_i_usd * tasa
            sf_bs = saldo_f_usd * tasa if saldo_f_usd is not None else None
            return ContextoReciboCuotaMoneda(
                moneda="BS",
                monto_str=f"{m_bs:.2f}",
                saldo_inicial=f"{si_bs:.2f}",
                saldo_final=f"{sf_bs:.2f}" if sf_bs is not None else "-",
                tasa_cambio=tasa,
            )

    return ContextoReciboCuotaMoneda(
        moneda="USD",
        monto_str=f"{base_usd:.2f}",
        saldo_inicial=f"{saldo_i_usd:.2f}" if saldo_i_usd is not None else "-",
        saldo_final=f"{saldo_f_usd:.2f}" if saldo_f_usd is not None else "-",
        tasa_cambio=None,
    )
