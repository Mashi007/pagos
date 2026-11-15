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


def _setup(monkeypatch, cuotas, en_bd=(), otras=()):
    prest = SimpleNamespace(id=10, cedula="V123456", requiere_revision=False)
    monkeypatch.setattr(svc, "hoy_negocio", lambda: date(2025, 12, 1))
    monkeypatch.setattr(svc, "_prestamo_mas_atrasado", lambda db, c, h: (prest, cuotas))
    monkeypatch.setattr(
        svc, "numero_documento_ya_registrado", lambda db, nd: nd in set(en_bd)
    )
    monkeypatch.setattr(svc, "invalidate_universo_analisis_cache", lambda: None)
    monkeypatch.setattr(svc, "_claves_en_otras_tablas", lambda db: set(otras))
    llamadas: list[int] = []

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
        llamadas.append(dep["id"])
        return SimpleNamespace(id=1000 + dep["id"]), "ok"

    monkeypatch.setattr(svc, "_crear_pago_mercantil", fake_crear)
    return llamadas


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
    assert "se detiene" in _r(out)["detalle"]


def test_tolerancia_sobre_monto_de_la_cuota_aunque_tenga_abono(monkeypatch):
    c = _cuota(1, date(2025, 6, 18))
    c.total_pagado = Decimal("60")  # cuota 110, falta 50 → rango 88..132
    _setup(monkeypatch, [c])
    deps = [_dep(0, "20-06-2025", "100"), _dep(1, "21-06-2025", "55")]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    assert _ids(out) == [0]


def test_dentro_del_rango_elige_el_mas_cercano_a_lo_que_falta(monkeypatch):
    c = _cuota(1, date(2025, 6, 18))
    c.total_pagado = Decimal("20")  # cuota 110, falta 90 → rango 88..132
    _setup(monkeypatch, [c])
    deps = [_dep(0, "20-06-2025", "110"), _dep(1, "21-06-2025", "92")]
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


def test_simulacion_no_crea_pagos_pero_simula_cascada(monkeypatch):
    cuotas = [_cuota(1, date(2025, 6, 18)), _cuota(2, date(2025, 7, 18))]
    llamadas = _setup(monkeypatch, cuotas)
    deps = [_dep(0, "20-06-2025", "100"), _dep(1, "20-07-2025", "110")]
    out = svc.procesar_lote_seriales(
        _DB(), cedulas=["V123456"], depositos=deps, simular=True
    )
    assert llamadas == []
    assert out["simulado"] is True and out["pagos_creados"] == 0
    assert _ids(out) == [0, 1]
    assert all(p["pago_id"] is None for p in _r(out)["pagos"])
    assert _r(out)["estado"] == "PARCIAL"  # julio queda con 10 (simulado)
    assert cuotas[0].total_pagado == Decimal("0")


def test_tolerancia_configurable(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 6, 18))])
    deps = [_dep(0, "20-06-2025", "100")]  # 9% menos
    out = svc.procesar_lote_seriales(
        _DB(), cedulas=["V123456"], depositos=deps, tolerancia_pct=5
    )
    assert _ids(out) == []


def test_max_meses_adelante(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 6, 18))])
    deps = [_dep(0, "20-09-2025", "110")]  # 3 meses después
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps)
    assert _ids(out) == []
    _setup(monkeypatch, [_cuota(1, date(2025, 6, 18))])
    out = svc.procesar_lote_seriales(
        _DB(), cedulas=["V123456"], depositos=deps, max_meses_adelante=0
    )
    assert _ids(out) == [0]


def test_serial_en_otras_tablas_se_omite(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 6, 18))], otras={"740087400000003"})
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=JUNIO)
    assert _ids(out) == [6]
    assert out["depositos_en_otras_tablas"] == [3]


def test_alternativas_reporta_otros_candidatos(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 6, 18))])
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=JUNIO)
    # junio 88..132: 114 elegido; quedan 115, 100, 120, 128, 96
    assert _r(out)["pagos"][0]["alternativas"] == 5


def test_deshacer_solo_pagos_de_seriales(monkeypatch):
    import app.services.pagos_eliminar_service as elim

    pagos = {
        1: SimpleNamespace(usuario_registro=svc.USUARIO_REGISTRO),
        2: SimpleNamespace(usuario_registro="otro@x.com"),
    }

    class DB(_DB):
        def get(self, model, pid):
            return pagos.get(pid)

    borrados = []
    monkeypatch.setattr(elim, "ejecutar_eliminar_pago", lambda db, pid, current_user=None: borrados.append(pid))
    monkeypatch.setattr(svc, "invalidate_universo_analisis_cache", lambda: None)
    out = svc.deshacer_pagos_seriales(DB(), [1, 2, 3])
    assert borrados == [1]
    assert out["eliminados"] == [1]
    assert {o["pago_id"] for o in out["omitidos"]} == {2, 3}


def test_serial_usado_en_lote_anterior_no_se_repite(monkeypatch):
    _setup(monkeypatch, [_cuota(1, date(2025, 6, 18))])
    deps = [
        _dep(0, "20-06-2025", "110", serial="555666777"),
        _dep(1, "21-06-2025", "110", serial="555666777"),
    ]
    out = svc.procesar_lote_seriales(_DB(), cedulas=["V123456"], depositos=deps, usados=[0])
    assert _ids(out) == []


def test_aprobar_subconjunto_respeta_asignacion_simulada(monkeypatch):
    def prestamos():
        return {
            "V1": (SimpleNamespace(id=1, cedula="V1", requiere_revision=False), [_cuota(1, date(2025, 6, 18))]),
            "V2": (SimpleNamespace(id=2, cedula="V2", requiere_revision=False), [_cuota(1, date(2025, 6, 18))]),
            "V3": (SimpleNamespace(id=3, cedula="V3", requiere_revision=False), [_cuota(1, date(2025, 6, 18))]),
        }

    _setup(monkeypatch, [])
    datos = prestamos()
    monkeypatch.setattr(svc, "_prestamo_mas_atrasado", lambda db, c, h: datos.get(c, (None, [])))
    monkeypatch.setattr(svc, "_cedula_canon", lambda v: str(v or "").strip().upper())
    deps = [
        _dep(0, "20-06-2025", "110"),
        _dep(1, "21-06-2025", "109"),
        _dep(2, "22-06-2025", "108"),
    ]
    sim = svc.procesar_lote_seriales(_DB(), cedulas=["V1", "V2", "V3"], depositos=deps, simular=True)
    asign = {r["cedula"]: [p["deposito_id"] for p in r["pagos"]] for r in sim["resultados"]}
    assert asign == {"V1": [0], "V2": [1], "V3": [2]}

    # Se aprueba solo V3; lo simulado para V1 y V2 queda reservado.
    datos.update(prestamos())
    real = svc.procesar_lote_seriales(_DB(), cedulas=["V3"], depositos=deps, usados=[0, 1])
    assert [p["deposito_id"] for p in real["resultados"][0]["pagos"]] == [2]



def test_cedula_sin_cliente_no_rompe_lote(monkeypatch):
    """Si la cédula no existe en clientes (FK), ese préstamo se detiene y el lote sigue."""
    from app.utils.cedula_almacenamiento import CedulaPagoFkError

    cuotas_a = [_cuota(1, date(2025, 6, 18))]
    cuotas_b = [_cuota(1, date(2025, 6, 18))]
    prest_a = SimpleNamespace(id=10, cedula="V31158608", requiere_revision=False)
    prest_b = SimpleNamespace(id=11, cedula="V123456", requiere_revision=False)

    def prestamo_por_cedula(db, c, h):
        if c == "V31158608":
            return prest_a, cuotas_a
        if c == "V123456":
            return prest_b, cuotas_b
        return None, []

    monkeypatch.setattr(svc, "hoy_negocio", lambda: date(2025, 12, 1))
    monkeypatch.setattr(svc, "_prestamo_mas_atrasado", prestamo_por_cedula)
    monkeypatch.setattr(svc, "_cedula_canon", lambda v: str(v or "").strip().upper())
    monkeypatch.setattr(svc, "numero_documento_ya_registrado", lambda db, nd: False)
    monkeypatch.setattr(svc, "invalidate_universo_analisis_cache", lambda: None)
    monkeypatch.setattr(svc, "_claves_en_otras_tablas", lambda db: set())

    def asegurar(db, *, cedula_raw, prestamo_id):
        if int(prestamo_id) == 10:
            raise CedulaPagoFkError(
                "La cédula «V31158608» no existe en clientes. "
                "Asigne un crédito válido o corrija el documento del cliente en CRM."
            )
        return "V123456"

    monkeypatch.setattr(svc, "asegurar_cedula_pago_para_fk", asegurar)

    creados: list[int] = []

    def crear(db, *, prestamo, cedula, dep, numero_doc):
        try:
            svc.asegurar_cedula_pago_para_fk(
                db, cedula_raw=cedula, prestamo_id=int(prestamo.id)
            )
        except CedulaPagoFkError as e:
            return None, str(e)
        cuotas = cuotas_a if int(prestamo.id) == 10 else cuotas_b
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
        return SimpleNamespace(id=2000 + dep["id"]), "ok"

    monkeypatch.setattr(svc, "_crear_pago_mercantil", crear)

    deps = [_dep(0, "20-06-2025", "110"), _dep(1, "21-06-2025", "110")]
    out = svc.procesar_lote_seriales(
        _DB(), cedulas=["V31158608", "V123456"], depositos=deps
    )
    assert out["resultados"][0]["estado"] == "SIN_COINCIDENCIA"
    assert "no existe en clientes" in out["resultados"][0]["detalle"]
    assert out["resultados"][1]["estado"] == "COMPLETO"
    assert creados == [0]


def test_crear_pago_usa_asegurar_fk(monkeypatch):
    from app.utils.cedula_almacenamiento import CedulaPagoFkError

    monkeypatch.setattr(
        svc,
        "asegurar_cedula_pago_para_fk",
        lambda db, *, cedula_raw, prestamo_id: (_ for _ in ()).throw(
            CedulaPagoFkError("La cédula «V31158608» no existe en clientes.")
        ),
    )
    prest = SimpleNamespace(id=2615, cedula="V31158608")
    pago, det = svc._crear_pago_mercantil(
        _DB(),
        prestamo=prest,
        cedula="V31158608",
        dep={"id": 1, "fecha": date(2025, 9, 25), "monto": Decimal("92.00"), "serial_norm": "740"},
        numero_doc="740",
    )
    assert pago is None
    assert "no existe en clientes" in det
