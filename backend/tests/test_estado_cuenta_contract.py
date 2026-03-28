# -*- coding: utf-8 -*-
"""
Contrato: amortizacion del estado de cuenta vs listado GET /prestamos/{id}/cuotas (misma regla estado_cuota_para_mostrar).

pytest tests/test_estado_cuenta_contract.py -v
"""
from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.prestamos import _listado_cuotas_prestamo_dicts
from app.core.database import SessionLocal
from app.models.prestamo import Prestamo
from app.services.estado_cuenta_datos import obtener_datos_estado_cuenta_prestamo


@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _primer_prestamo_con_amortizacion(db):
    """Prestamo APROBADO o LIQUIDADO con al menos una cuota."""
    for estado in ("APROBADO", "LIQUIDADO"):
        row = db.execute(select(Prestamo).where(Prestamo.estado == estado).limit(1)).scalars().first()
        p = row[0] if row is not None and hasattr(row, "__getitem__") else row
        if not p:
            continue
        datos = obtener_datos_estado_cuenta_prestamo(db, p.id)
        if not datos:
            continue
        blocks = datos.get("amortizaciones_por_prestamo") or []
        if blocks and (blocks[0].get("cuotas") or []):
            return p.id
    return None


def test_amortizacion_coincide_con_listado_cuotas(db):
    pid = _primer_prestamo_con_amortizacion(db)
    if pid is None:
        pytest.skip("Sin prestamo APROBADO/LIQUIDADO con cuotas en BD")

    datos = obtener_datos_estado_cuenta_prestamo(db, pid)
    listado = _listado_cuotas_prestamo_dicts(db, pid)
    assert datos and listado

    by_id = {c["id"]: c for c in listado}
    amort_rows = []
    for block in datos.get("amortizaciones_por_prestamo") or []:
        amort_rows.extend(block.get("cuotas") or [])

    assert amort_rows, "Se esperaba tabla de amortizacion para este prestamo"

    for row in amort_rows:
        cid = row.get("id")
        assert cid in by_id, f"cuota id {cid} no aparece en listado"
        assert row.get("estado") == by_id[cid].get("estado")
        assert row.get("estado_etiqueta") == by_id[cid].get("estado_etiqueta")
