# -*- coding: utf-8 -*-
"""Cobranzas Seriales: un depósito por mes, el más cercano a lo que falta (±20%)."""
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


def _cuota(n, venc, monto="110"):
    return SimpleNamespace(
        numero_cuota=n,
        fecha_vencimiento=venc,
        monto=Decimal(monto),
        total_pagado=Decimal("0"),
    )


def _setup(monkeypatch, cuotas, en_bd=()):
    prest = SimpleNamespace(id=10, cedula="V123456", requiere_revision=False)
    monkeypatch.setattr(svc, "hoy_negocio", lambda: date(2025, 12, 1))
    monkeypatch.setattr(svc, "_prestamo_mas_atrasado", lambda db, c, h: (prest, cuotas))
    monkeypatch.setattr(
        svc, "numero_documento_ya_registrado", lambda db, nd: nd in set(en_bd)
    )
    monkeypatch.setattr(svc, "invalidate_universo_analisis_cache", lambda: None)

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
        return SimpleNamespace(id=1000 + dep["id"]), "ok"

    monkeypatch.setattr(svc, "_crear_pago_mercantil", fake_crear)


def _dep(i, fecha, monto, serial=None):
    return {"id": i, "fecha": fecha, "serial": serial or f"7400874{i:08d}", "monto": monto}


def _r(out):
    return out["resultados"][0]


def _ids(out):
    return [p["deposito_id"] for p in _r(out)["pagos"]]


JUNIO = [
    _dep(0, "30-06-2025", "54"),
    _dep(1, "30-06-2025", "120"),
    _dep(2, "30-06-2025", "128"),
    _dep(3, "30-06-2025", "114"),
    _dep(4, "30-06-2025", "96.00"),
    _dep(5, "27-06-2025", "79"),
    _dep(6, "27-06-2025", "115"),
    _dep(7, "27-06-2025", "100"),
    _dep(8, "26-06-2025", "160"),
]


def test_un_pago_del_mes_el_mas_cercano_dentro_20(monkeypatch):
    cuotas = [_cuota(1, date(2025, 6, 18))]
    _setup(monkeypatch, cuotas)
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=JUNIO)
    assert _ids(out) == [3]  # 114: diferencia 4 (115 → 5, 100 → 10)
    assert _r(out)["pagos"][0]["mes"] == "06/2025"


def test_empate_toma_fecha_mas_antigua(monkeypatch):
    cuotas = [_cuota(1, date(2025, 6, 18))]
    _setup(monkeypatch, cuotas)
    deps = [_dep(0, "30-06-2025", "105"), _dep(1, "10-06-2025", "115")]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    assert _ids(out) == [1]


def test_solo_un_deposito_por_mes_y_mes_siguiente_para_la_otra_cuota(monkeypatch):
    cuotas = [_cuota(1, date(2025, 6, 18)), _cuota(2, date(2025, 7, 18))]
    _setup(monkeypatch, cuotas)
    deps = JUNIO + [_dep(20, "05-07-2025", "110")]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    assert _ids(out) == [3, 20]
    assert [p["mes"] for p in _r(out)["pagos"]] == ["06/2025", "07/2025"]


def test_menor_deja_resto_y_cascada_lo_cubre_con_el_siguiente(monkeypatch):
    cuotas = [_cuota(1, date(2025, 6, 18)), _cuota(2, date(2025, 7, 18))]
    _setup(monkeypatch, cuotas)
    deps = [_dep(0, "20-06-2025", "100"), _dep(1, "20-07-2025", "110")]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    assert _ids(out) == [0, 1]
    # julio: 10 completan junio por cascada, 100 a julio → julio queda con 10
    assert cuotas[0].total_pagado == Decimal("110")
    assert cuotas[1].total_pagado == Decimal("100")
    assert _r(out)["estado"] == "PARCIAL"


def test_mes_sin_candidato_pasa_al_siguiente(monkeypatch):
    cuotas = [_cuota(1, date(2025, 6, 18))]
    _setup(monkeypatch, cuotas)
    deps = [
        _dep(0, "20-06-2025", "50"),  # fuera de ±20%
        _dep(1, "15-07-2025", "110"),
    ]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    assert _ids(out) == [1]
    assert _r(out)["estado"] == "COMPLETO"


def test_no_busca_antes_del_mes_de_la_cuota(monkeypatch):
    cuotas = [_cuota(1, date(2025, 6, 18))]
    _setup(monkeypatch, cuotas)
    deps = [_dep(0, "30-05-2025", "110")]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    assert _ids(out) == []
    assert _r(out)["estado"] == "SIN_COINCIDENCIA"
    assert "fin de la lista de depósitos" in _r(out)["detalle"]


def test_veinte_por_ciento_sobre_lo_que_falta(monkeypatch):
    c = _cuota(1, date(2025, 6, 18))
    c.total_pagado = Decimal("60")  # falta 50 → rango 40..60
    _setup(monkeypatch, [c])
    deps = [_dep(0, "20-06-2025", "100"), _dep(1, "21-06-2025", "55")]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    assert _ids(out) == [1]


def test_serial_en_bd_toma_siguiente_mas_cercano(monkeypatch):
    cuotas = [_cuota(1, date(2025, 6, 18))]
    _setup(monkeypatch, cuotas, en_bd={"740087400000003"})
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=JUNIO)
    assert _ids(out) == [6]  # 114 ya en BD → 115
    assert out["depositos_serial_en_bd"] == [3]


def test_usados_en_lote_previo_no_se_repiten(monkeypatch):
    cuotas = [_cuota(1, date(2025, 6, 18))]
    _setup(monkeypatch, cuotas)
    out = svc.procesar_lote_seriales(
        _DB(), cedulas=["V123456"], depositos=JUNIO, usados=[3]
    )
    assert _ids(out) == [6]


def test_fechas_iso_y_dd_mm_yyyy():
    assert svc._fecha("2025-06-26") == date(2025, 6, 26)
    assert svc._fecha("26-06-2025") == date(2025, 6, 26)
    assert svc._fecha("26/06/2025") == date(2025, 6, 26)


def test_limite_20_cedulas():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as e:
        svc.procesar_lote_seriales(_DB(), cedulas=["V1"] * 21, depositos=[])
    assert e.value.status_code == 400
