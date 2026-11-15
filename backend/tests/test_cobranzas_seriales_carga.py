# -*- coding: utf-8 -*-
"""Cobranzas Seriales: cuota atrasada ↔ depósitos por ventana de fecha (monto libre, parciales)."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

import app.services.cobranzas.seriales_carga_service as svc


class _DB:
    def commit(self):
        pass

    def rollback(self):
        pass


def _cuota(n, venc, monto="140"):
    return SimpleNamespace(
        numero_cuota=n,
        fecha_vencimiento=venc,
        monto=Decimal(monto),
        total_pagado=Decimal("0"),
    )


def _setup(monkeypatch, cuotas, en_bd=()):
    prest = SimpleNamespace(id=10, cedula="V123456", requiere_revision=False)
    monkeypatch.setattr(svc, "hoy_negocio", lambda: date(2025, 6, 1))
    monkeypatch.setattr(svc, "_prestamo_mas_atrasado", lambda db, c, h: (prest, cuotas))
    monkeypatch.setattr(
        svc, "numero_documento_ya_registrado", lambda db, nd: nd in set(en_bd)
    )
    monkeypatch.setattr(svc, "invalidate_universo_analisis_cache", lambda: None)
    creados = []

    def fake_crear(db, *, prestamo, cedula, dep, numero_doc):
        resto = Decimal(dep["monto"])
        for c in cuotas:
            falta = c.monto - c.total_pagado
            if falta <= 0:
                continue
            aplica = min(falta, resto)
            c.total_pagado += aplica
            resto -= aplica
            if resto <= 0:
                break
        creados.append(dep["id"])
        return SimpleNamespace(id=1000 + len(creados)), "ok"

    monkeypatch.setattr(svc, "_crear_pago_mercantil", fake_crear)
    return creados


def _dep(i, fecha, serial, monto):
    return {"id": i, "fecha": fecha, "serial": serial, "monto": monto}


def _ids(out):
    return [p["deposito_id"] for p in out["resultados"][0]["pagos"]]


def test_monto_libre_parcial_se_completa_con_siguiente(monkeypatch):
    cuotas = [_cuota(1, date(2025, 1, 1)), _cuota(2, date(2025, 2, 1))]
    _setup(monkeypatch, cuotas)
    deps = [
        _dep(0, "05-01-2025", "740087000000001", "100"),  # enero parcial (falta 40)
        _dep(1, "20-01-2025", "740087000000002", "40"),  # completa enero
        _dep(2, "10-02-2025", "740087000000003", "140"),  # febrero
    ]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    r = out["resultados"][0]
    assert r["estado"] == "COMPLETO"
    assert _ids(out) == [0, 1, 2]
    assert [p["cuota_numero"] for p in r["pagos"]] == [1, 1, 2]
    assert r["cuotas_cubiertas"] == 2


def test_varios_depositos_para_una_cuota(monkeypatch):
    cuotas = [_cuota(1, date(2025, 1, 1))]
    _setup(monkeypatch, cuotas)
    deps = [_dep(i, "05-01-2025", f"74008700000010{i}", "50") for i in range(4)]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    # 50+50+50 = 150 ≥ 140: el cuarto no se usa (ya no hay cuotas atrasadas)
    assert _ids(out) == [0, 1, 2]
    assert out["resultados"][0]["estado"] == "COMPLETO"


def test_sobrante_cubre_siguientes_cuotas_sin_su_ventana(monkeypatch):
    cuotas = [
        _cuota(1, date(2025, 1, 1)),
        _cuota(2, date(2025, 2, 1)),
        _cuota(3, date(2025, 3, 1)),
    ]
    _setup(monkeypatch, cuotas)
    deps = [
        _dep(0, "05-01-2025", "740087000000020", "300"),  # enero + febrero + 20 a marzo
        _dep(1, "10-03-2025", "740087000000021", "120"),  # completa marzo
    ]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    r = out["resultados"][0]
    assert r["estado"] == "COMPLETO"
    assert [p["cuota_numero"] for p in r["pagos"]] == [1, 3]


def test_sin_deposito_en_ventana_queda_parcial_y_se_detiene(monkeypatch):
    cuotas = [_cuota(1, date(2025, 1, 1)), _cuota(2, date(2025, 2, 1))]
    _setup(monkeypatch, cuotas)
    deps = [
        _dep(0, "05-01-2025", "740087000000030", "100"),  # enero parcial
        _dep(1, "20-04-2025", "740087000000031", "500"),  # fuera de ventana de enero (+109)
    ]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    r = out["resultados"][0]
    assert r["estado"] == "PARCIAL"
    assert _ids(out) == [0]
    assert "Cuota #1" in r["detalle"]
    assert r["cuotas_cubiertas"] == 0


def test_ultimo_deposito_se_carga_completo_aunque_exceda(monkeypatch):
    cuotas = [_cuota(1, date(2025, 1, 1))]
    _setup(monkeypatch, cuotas)
    deps = [_dep(0, "05-01-2025", "740087000000040", "500")]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    assert _ids(out) == [0]
    assert out["resultados"][0]["pagos"][0]["monto"] == 500.0


def test_ventana_10_antes_60_despues(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 1, 1))])
    deps = [
        _dep(0, "21-12-2024", "740087000000050", "140"),  # -11
        _dep(1, "03-03-2025", "740087000000051", "140"),  # +61
        _dep(2, "22-12-2024", "740087000000052", "140"),  # -10
    ]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    assert _ids(out) == [2]


def test_serial_en_bd_se_omite_y_usados_no_se_repiten(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 1, 1))], en_bd={"740087000000060"})
    deps = [
        _dep(0, "05-01-2025", "740087000000060", "140"),  # ya en BD
        _dep(1, "05-01-2025", "740087000000061", "140"),  # usado en lote previo
        _dep(2, "06-01-2025", "740087000000062", "140"),
    ]
    out = svc.procesar_lote_seriales(
        _DB(), cedulas=["V123456"], depositos=deps, usados=[1]
    )
    assert _ids(out) == [2]
    assert out["depositos_serial_en_bd"] == [0]


def test_limite_20_cedulas():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as e:
        svc.procesar_lote_seriales(_DB(), cedulas=["V1"] * 21, depositos=[])
    assert e.value.status_code == 400
