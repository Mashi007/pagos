# -*- coding: utf-8 -*-
"""Auditoría Seriales: normalización y marcado si/no en Excel."""
import io

from openpyxl import Workbook

from app.services.auditoria_seriales_excel_service import (
    _clave_serial,
    _claves_desde_campos_pago,
    exportar_excel_con_si_no,
)


def test_clave_serial_quita_prefijos_y_sufijos():
    assert _clave_serial("740087486821077") == "740087486821077"
    assert _clave_serial("BNC/740087486821077") == "740087486821077"
    assert _clave_serial("740087486821077 §CD:D0001") == "740087486821077"
    assert _clave_serial("740087486821077_A0001") == "740087486821077"
    assert _clave_serial(740087486821077.0) == "740087486821077"
    assert _clave_serial("") == ""
    assert _clave_serial(None) == ""


def test_claves_desde_campos_pago_numero_y_referencia():
    keys = _claves_desde_campos_pago("BNC/125201931", "103917175")
    assert "125201931" in keys
    assert "103917175" in keys


def test_consultar_lote_vacio_y_limite():
    from fastapi import HTTPException
    from app.services.auditoria_seriales_excel_service import (
        MAX_SERIALES_LOTE,
        consultar_seriales_lote,
    )

    class FakeDB:
        def execute(self, *_a, **_k):
            class R:
                def all(self):
                    return []

            return R()

    out = consultar_seriales_lote(FakeDB(), ["", "12345"])
    assert out["total_filas"] == 2
    assert out["encontrados_si"] == 0
    assert out["items"][0]["resultado"] == "no"
    assert out["items"][1]["resultado"] == "no"

    try:
        consultar_seriales_lote(FakeDB(), ["x"] * (MAX_SERIALES_LOTE + 1))
        assert False, "debía rechazar lote grande"
    except HTTPException as e:
        assert e.status_code == 400


def test_exportar_escribe_columna_d():
    wb = Workbook()
    ws = wb.active
    ws.append(["Deposito", "Referencia", "Monto", "SI/NO"])
    ws.append(["31-03-2025", "740087486821077", 140, None])
    ws.append(["31-03-2025", "999999999999999", 80, None])
    buf = io.BytesIO()
    wb.save(buf)
    content = buf.getvalue()

    payload = {
        "items": [
            {"fila": 2, "serial_archivo": "740087486821077", "resultado": "si"},
            {"fila": 3, "serial_archivo": "999999999999999", "resultado": "no"},
        ]
    }
    out = exportar_excel_con_si_no(content, payload)
    from openpyxl import load_workbook

    wb2 = load_workbook(io.BytesIO(out))
    ws2 = wb2.active
    assert ws2.cell(2, 4).value == "si"
    assert ws2.cell(3, 4).value == "no"
