# -*- coding: utf-8 -*-
"""Cobranzas Seriales: emparejamiento cuota atrasada ↔ depósito (reglas de negocio)."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import app.services.cobranzas.seriales_carga_service as svc


class _DB:
    def commit(self):
        pass

    def rollback(self):
        pass


def _cuota(n, venc, monto="140"):
    return SimpleNamespace(numero_cuota=n, fecha_vencimiento=venc, monto=Decimal(monto))


def _setup(monkeypatch, cuotas, en_bd=()):
    prest = SimpleNamespace(id=10, cedula="V123456", requiere_revision=False)
    monkeypatch.setattr(svc, "hoy_negocio", lambda: date(2025, 6, 1))
    monkeypatch.setattr(svc, "_prestamo_mas_atrasado", lambda db, c, h: (prest, cuotas))
    monkeypatch.setattr(
        svc, "numero_documento_ya_registrado", lambda db, nd: nd in set(en_bd)
    )
    creados = []

    def fake_crear(db, *, prestamo, cedula, dep, numero_doc):
        creados.append(dep["id"])
        return SimpleNamespace(id=1000 + len(creados)), "ok"

    monkeypatch.setattr(svc, "_crear_pago_mercantil", fake_crear)
    monkeypatch.setattr(svc, "invalidate_universo_analisis_cache", lambda: None, raising=False)
    return creados


def _dep(i, fecha, serial, monto):
    return {"id": i, "fecha": fecha, "serial": serial, "monto": monto}


def test_toma_por_orden_monto_exacto_y_ventana(monkeypatch):
    cuotas = [
        _cuota(1, date(2025, 1, 1)),
        _cuota(2, date(2025, 2, 1)),
        _cuota(3, date(2025, 3, 1)),
    ]
    _setup(monkeypatch, cuotas)
    deps = [
        _dep(0, "15-12-2024", "740087000000001", "140"),  # 17 días antes de enero: fuera
        _dep(1, "05-01-2025", "740087000000002", "139"),  # monto distinto
        _dep(2, "05-01-2025", "740087000000003", "140"),  # enero
        _dep(3, "25-01-2025", "740087000000004", "140"),  # febrero (7 días antes)
        _dep(4, "10-03-2025", "740087000000005", "140"),  # marzo
    ]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    r = out["resultados"][0]
    assert r["estado"] == "COMPLETO"
    assert [p["deposito_id"] for p in r["pagos"]] == [2, 3, 4]
    assert out["depositos_usados"] == [2, 3, 4]


def test_si_una_cuota_no_coincide_se_detiene(monkeypatch):
    cuotas = [
        _cuota(1, date(2025, 1, 1)),
        _cuota(2, date(2025, 2, 1)),
        _cuota(3, date(2025, 3, 1)),
    ]
    _setup(monkeypatch, cuotas)
    deps = [
        _dep(0, "05-01-2025", "740087000000010", "140"),  # enero
        _dep(1, "20-04-2025", "740087000000011", "140"),  # cabría en marzo (+50), no en febrero (+78)
    ]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    r = out["resultados"][0]
    assert r["estado"] == "PARCIAL"
    assert [p["deposito_id"] for p in r["pagos"]] == [0]
    assert "Cuota #2" in r["detalle"]


def test_60_dias_despues_si_61_no(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 1, 1))])
    deps = [
        _dep(0, "03-03-2025", "740087000000020", "140"),  # +61
        _dep(1, "02-03-2025", "740087000000021", "140"),  # +60
    ]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    assert [p["deposito_id"] for p in out["resultados"][0]["pagos"]] == [1]


def test_serial_en_bd_se_omite_y_usados_no_se_repiten(monkeypatch):
    _setup(
        monkeypatch,
        [_cuota(1, date(2025, 1, 1))],
        en_bd={"740087000000030"},
    )
    deps = [
        _dep(0, "05-01-2025", "740087000000030", "140"),  # ya en BD
        _dep(1, "05-01-2025", "740087000000031", "140"),  # usado en lote previo
        _dep(2, "06-01-2025", "740087000000032", "140"),
    ]
    out = svc.procesar_lote_seriales(
        _DB(), cedulas=["V123456"], depositos=deps, usados=[1]
    )
    assert [p["deposito_id"] for p in out["resultados"][0]["pagos"]] == [2]
    assert out["depositos_serial_en_bd"] == [0]


def test_limite_20_cedulas():
    from fastapi import HTTPException

    try:
        svc.procesar_lote_seriales(_DB(), cedulas=["V1"] * 21, depositos=[])
        assert False
    except HTTPException as e:
        assert e.status_code == 400
