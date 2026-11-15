# -*- coding: utf-8 -*-
"""Cobranzas Seriales: revisión manual por cédula (candidatos por mes y guardado)."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.services.cobranzas.seriales_carga_service as svc


class _DB:
    def commit(self):
        pass

    def rollback(self):
        pass


def _cuota(n, venc, monto="100", pagado="0"):
    return SimpleNamespace(
        id=500 + n,
        numero_cuota=n,
        fecha_vencimiento=venc,
        monto=Decimal(monto),
        total_pagado=Decimal(pagado),
        estado="VENCIDO",
    )


def _dep(i, fecha, monto, serial=None):
    return {"id": i, "fecha": fecha, "serial": serial or f"7400874{i:08d}", "monto": monto}


def _setup(monkeypatch, cuotas, en_bd=(), otras=(), prestamo_id=10):
    prest = SimpleNamespace(id=prestamo_id, cedula="V123456", nombres="Ana", requiere_revision=False)
    hoy = date(2025, 12, 1)
    monkeypatch.setattr(svc, "hoy_negocio", lambda: hoy)
    atrasadas = [c for c in cuotas if c.fecha_vencimiento < hoy and c.total_pagado < c.monto]
    monkeypatch.setattr(svc, "_prestamo_mas_atrasado", lambda db, c, h: (prest, atrasadas))
    monkeypatch.setattr(svc, "_todas_cuotas", lambda db, pid: cuotas)
    monkeypatch.setattr(svc, "numero_documento_ya_registrado", lambda db, nd: nd in set(en_bd))
    monkeypatch.setattr(svc, "invalidate_universo_analisis_cache", lambda: None)
    monkeypatch.setattr(svc, "_claves_en_otras_tablas", lambda db: set(otras))
    _bd = {svc._clave_colision(x) for x in en_bd}
    monkeypatch.setattr(svc, "_claves_registradas_bd", lambda db, claves: claves & _bd)
    creados: list[int] = []

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
        return SimpleNamespace(id=1000 + dep["id"]), "ok"

    monkeypatch.setattr(svc, "_crear_pago_mercantil", fake_crear)
    return creados


def _meses(out, i=0):
    return {m["mes"]: [c["deposito_id"] for c in m["candidatos"]] for m in out["bloques"][i]["meses"]}


def test_muestra_3_meses_posteriores_y_30_por_ciento_del_monto(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 2, 15))])
    deps = [
        _dep(0, "20-02-2025", "100"),  # mes del vencimiento: no se muestra
        _dep(1, "10-03-2025", "70"),
        _dep(2, "11-03-2025", "131"),  # fuera de ±30%
        _dep(3, "05-04-2025", "100"),
        _dep(4, "05-05-2025", "125"),
        _dep(5, "05-06-2025", "100"),  # 4.º mes: fuera
    ]
    out = svc.revision_cedula(_DB(), cedula="V123456", depositos=deps)
    assert _meses(out) == {"03/2025": [1], "04/2025": [3], "05/2025": [4]}
    assert out["cliente"] == "Ana"
    assert out["cuotas"][0]["atrasada"] is True


def test_sugerencia_mas_cercano_y_un_mes_por_prestamo(monkeypatch):
    cuotas = [_cuota(1, date(2025, 2, 15)), _cuota(2, date(2025, 3, 15))]
    _setup(monkeypatch, cuotas)
    deps = [
        _dep(0, "10-03-2025", "80"),
        _dep(1, "12-03-2025", "98"),
        _dep(2, "05-04-2025", "100"),
        _dep(3, "06-04-2025", "101"),
    ]
    out = svc.revision_cedula(_DB(), cedula="V123456", depositos=deps)
    # Cuota 1: marzo → 98; faltan 2 → abril 100 (sobrante a cuota 2). Abril ya tomado.
    assert out["sugeridos"] == [1, 2]


def test_sugerencia_completa_cuota_con_varios_meses(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 2, 15))])
    deps = [_dep(0, "10-03-2025", "75"), _dep(1, "10-04-2025", "75")]
    out = svc.revision_cedula(_DB(), cedula="V123456", depositos=deps)
    assert out["sugeridos"] == [0, 1]


def test_excluye_usados_bd_y_otras_tablas(monkeypatch):
    _setup(
        monkeypatch,
        [_cuota(1, date(2025, 2, 15))],
        en_bd={"740087400000001"},
        otras={"740087400000002"},
    )
    deps = [
        _dep(0, "10-03-2025", "100"),
        _dep(1, "11-03-2025", "100"),
        _dep(2, "12-03-2025", "100"),
        _dep(3, "13-03-2025", "100"),
    ]
    out = svc.revision_cedula(_DB(), cedula="V123456", depositos=deps, usados=[0])
    assert _meses(out)["03/2025"] == [3]
    assert out["depositos_serial_en_bd"] == [1]
    assert out["depositos_en_otras_tablas"] == [2]


def test_sin_atraso(monkeypatch):
    monkeypatch.setattr(svc, "hoy_negocio", lambda: date(2025, 12, 1))
    monkeypatch.setattr(svc, "_prestamo_mas_atrasado", lambda db, c, h: (None, []))
    out = svc.revision_cedula(_DB(), cedula="V123456", depositos=[])
    assert out["estado"] == "SIN_ATRASO"


def test_guardar_crea_en_orden_de_fecha_y_aplica_cascada(monkeypatch):
    cuotas = [_cuota(1, date(2025, 2, 15)), _cuota(2, date(2025, 3, 15))]
    creados = _setup(monkeypatch, cuotas)
    deps = [_dep(1, "10-04-2025", "120"), _dep(0, "10-03-2025", "90")]
    out = svc.guardar_revision_cedula(_DB(), cedula="V123456", prestamo_id=10, depositos=deps)
    assert creados == [0, 1]
    assert out["error"] is None
    assert [p["pago_id"] for p in out["pagos"]] == [1000, 1001]
    assert cuotas[0].total_pagado == Decimal("100")
    assert cuotas[1].total_pagado == Decimal("100")


def test_guardar_rechaza_dos_del_mismo_mes(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 2, 15))])
    deps = [_dep(0, "10-03-2025", "50"), _dep(1, "20-03-2025", "50")]
    with pytest.raises(HTTPException) as e:
        svc.guardar_revision_cedula(_DB(), cedula="V123456", prestamo_id=10, depositos=deps)
    assert "un depósito por mes" in e.value.detail


def test_guardar_rechaza_serial_registrado(monkeypatch):
    creados = _setup(monkeypatch, [_cuota(1, date(2025, 2, 15))], en_bd={"740087400000000"})
    with pytest.raises(HTTPException) as e:
        svc.guardar_revision_cedula(
            _DB(), cedula="V123456", prestamo_id=10, depositos=[_dep(0, "10-03-2025", "100")]
        )
    assert e.value.status_code == 409
    assert creados == []


def test_guardar_rechaza_si_cambio_el_prestamo(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 2, 15))], prestamo_id=11)
    with pytest.raises(HTTPException) as e:
        svc.guardar_revision_cedula(
            _DB(), cedula="V123456", prestamo_id=10, depositos=[_dep(0, "10-03-2025", "100")]
        )
    assert e.value.status_code == 409


def test_serial_tomado_en_otro_prestamo_no_se_ofrece(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 2, 15))])
    deps = [
        _dep(0, "10-03-2025", "100", serial="111222333"),
        _dep(1, "10-04-2025", "100", serial="111222333"),  # fila repetida del mismo serial
        _dep(2, "10-05-2025", "100", serial="999888777"),
    ]
    out = svc.revision_cedula(_DB(), cedula="V123456", depositos=deps, seriales_tomados=["111222333"])
    assert _meses(out) == {"03/2025": [], "04/2025": [], "05/2025": [2]}


def test_no_sugiere_mismo_serial_dos_veces(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 2, 15), monto="200")])
    deps = [
        _dep(0, "10-03-2025", "150", serial="111222333"),
        _dep(1, "10-04-2025", "150", serial="111222333"),
    ]
    out = svc.revision_cedula(_DB(), cedula="V123456", depositos=deps)
    assert out["sugeridos"] == [0]
