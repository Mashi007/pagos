# -*- coding: utf-8 -*-
"""Endpoint Excel: Saldos menores 200."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/exportar/saldos-menores-200")
def exportar_saldos_menores_200(db: Session = Depends(get_db)):
    """
    Deudores con saldo final del préstamo ≤ 200 USD (terminan de pagar con ese monto).
    Columnas: cédula, nombres, teléfono, email, saldo final, cuotas vencidas, cuotas mora.
    """
    from app.services.reporte_saldos_menores_200 import (
        construir_excel_saldos_menores_200,
    )

    try:
        content, n_filas = construir_excel_saldos_menores_200(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:500]) from e

    hoy_str = date.today().isoformat()
    filename = f"saldos_menores_200_{hoy_str}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "X-Filas": str(n_filas),
        "Access-Control-Expose-Headers": "X-Filas, Content-Disposition",
    }
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
