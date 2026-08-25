# -*- coding: utf-8 -*-
"""Observación de cola: Gemini no exacto no deja la bandeja en blanco."""

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros import reportados_dedup_helpers as dedup


def _run_items(pr):
    db = MagicMock()
    empty = {
        "_cedulas_en_clientes_set_cached": {"V12345678"},
        "_autorizados_bs_claves_cached": frozenset(),
        "_collect_candidatos_canon_desde_reportados": set(),
        "_pagos_canonicos_presentes_para_claves": set(),
        "_pagos_existentes_info_por_clave": {},
        "_pago_existente_info_resuelto": None,
        "_observacion_reglas_carga": [[]],
        "_row_tiene_recibo_pdf": False,
        "_merge_prestamo_objetivo_acum": ({}, set(), {}, {}),
        "primer_reportado_id_por_norm_batch": {},
        "documento_numero_desde_pago_reportado": ("", "OPX"),
    }
    patches = []
    for name, val in empty.items():
        if name == "documento_numero_desde_pago_reportado":
            patches.append(
                patch.object(dedup, name, return_value=val)
            )
        elif name == "_observacion_reglas_carga":
            patches.append(patch.object(dedup, name, return_value=val))
        elif name in (
            "_cedulas_en_clientes_set_cached",
            "_autorizados_bs_claves_cached",
            "_collect_candidatos_canon_desde_reportados",
            "_pagos_canonicos_presentes_para_claves",
            "_pagos_existentes_info_por_clave",
            "_merge_prestamo_objetivo_acum",
            "primer_reportado_id_por_norm_batch",
        ):
            patches.append(patch.object(dedup, name, return_value=val))
        else:
            patches.append(patch.object(dedup, name, return_value=val))
    ctx = patches[0]
    for p in patches[1:]:
        ctx = ctx
    # Enter all patches
    entered = [p.start() for p in patches]
    try:
        return dedup._pago_reportado_list_items_from_rows(
            db, [pr], include_financial_fields=False
        )
    finally:
        for p in patches:
            p.stop()


def _pr(**kwargs):
    from datetime import date, datetime

    base = dict(
        id=1,
        referencia_interna="RPC-TEST-1",
        nombres="A",
        apellidos="B",
        tipo_cedula="V",
        numero_cedula="12345678",
        institucion_financiera="BNC",
        monto=50,
        moneda="USD",
        fecha_pago=date(2026, 8, 20),
        numero_operacion="OP1",
        created_at=datetime(2026, 8, 20, 12, 0, 0),
        estado="en_revision",
        gemini_coincide_exacto="false",
        gemini_comentario="",
        observacion=None,
        correo_enviado_a=None,
        comprobante_imagen_id=None,
        canal_ingreso="cobros_publico",
        falla_validadores_manual=True,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_obs_incluye_gemini_no_exacto_si_comentario_vacio():
    items = _run_items(_pr(gemini_coincide_exacto="false", gemini_comentario=""))
    assert len(items) == 1
    assert items[0].observacion
    assert "Gemini no coincide exacto" in (items[0].observacion or "")
    assert "(false)" in (items[0].observacion or "")


def test_obs_no_inventa_gemini_si_ya_es_exacto():
    items = _run_items(
        _pr(
            estado="pendiente",
            gemini_coincide_exacto="true",
            gemini_comentario="ok",
            falla_validadores_manual=False,
        )
    )
    assert len(items) == 1
    assert not (items[0].observacion or "").strip()
