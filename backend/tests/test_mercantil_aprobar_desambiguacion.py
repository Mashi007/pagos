# -*- coding: utf-8 -*-
"""Mercantil: aprobar con serial en otro préstamo asigna §CD:D####."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros.reportados_dedup_helpers import (  # noqa: E402
    _es_duplicado_entre_prestamos_distintos,
    _mercantil_auto_desambiguar_para_aprobar,
)
from app.services.cobros.pago_reportado_documento import (  # noqa: E402
    _pago_cierra_reportado_como_importado,
    pago_reportado_colisiona_tabla_pagos,
)


def test_es_duplicado_entre_prestamos_distintos_flag_false():
    diag = SimpleNamespace(
        duplicado_en_pagos=True,
        prestamo_duplicado_es_objetivo=False,
        prestamo_existente_id=1225,
        prestamo_objetivo_id=6075,
    )
    assert _es_duplicado_entre_prestamos_distintos(diag) is True


def test_pago_cierra_no_confunde_otro_prestamo_si_reporte_tiene_cd():
    db = MagicMock()
    pago = SimpleNamespace(
        numero_documento="740087464410397",
        referencia_pago="740087464410397",
        doc_canon_numero="740087464410397",
        cedula_cliente="V12345678",
        estado="PAGADO",
    )
    pr = SimpleNamespace(
        numero_operacion="740087464410397 §CD:D1234",
        tipo_cedula="V",
        numero_cedula="12345678",
    )
    db.get.return_value = pago
    with patch(
        "app.services.cuota_pago_integridad.pago_tiene_aplicaciones_cuotas",
        return_value=True,
    ):
        assert _pago_cierra_reportado_como_importado(db, 53896, pr) is False


def test_colisiona_false_con_cd_unico():
    db = MagicMock()
    pr = SimpleNamespace(
        numero_operacion="740087464410397 §CD:D9999",
        referencia_interna="RPC-20261007-00001",
    )
    with patch(
        "app.services.pago_numero_documento.numero_documento_ya_registrado",
        return_value=False,
    ):
        assert pago_reportado_colisiona_tabla_pagos(db, pr) is False


def test_mercantil_auto_desambiguar_asigna_codigo():
    db = MagicMock()
    pr = SimpleNamespace(
        referencia_interna="RPC-1",
        numero_operacion="740087464410397",
        institucion_financiera="Mercantil",
        tipo_cedula="V",
        numero_cedula="12345678",
    )
    diag = SimpleNamespace(
        duplicado_en_pagos=True,
        prestamo_duplicado_es_objetivo=False,
        prestamo_existente_id=1225,
        prestamo_objetivo_id=6075,
    )
    with patch(
        "app.api.v1.endpoints.cobros.reportados_validadores_helpers._diagnostico_duplicado_reportado",
        return_value=diag,
    ), patch(
        "app.services.pago_numero_documento.generar_numero_documento_desambiguado_unico",
        return_value="740087464410397 §CD:D4321",
    ):
        _mercantil_auto_desambiguar_para_aprobar(
            db, pr, prestamo_objetivo_id=6075
        )
    assert "§CD:D4321" in pr.numero_operacion
