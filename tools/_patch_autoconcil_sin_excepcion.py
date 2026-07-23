# -*- coding: utf-8 -*-
"""Patch pipeline: todos los pagos se autoconcilian sin excepcion."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"OLD not found in {path}")
    if text.count(old) != 1:
        raise SystemExit(f"OLD matches {text.count(old)} times in {path}")
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"patched {path.relative_to(ROOT)}")


def main() -> None:
    replace_once(
        ROOT / "backend/app/api/v1/endpoints/pagos/pago_conciliacion_estado.py",
        '''def _estado_conciliacion_post_cascada(pago: Pago, cuotas_completadas: int, cuotas_parciales: int) -> str:
    """
    Alinea estado tras cascada.

    Política de ingreso: un pago ya marcado conciliado (alta / autoconciliación)
    permanece conciliado y en PAGADO aunque la cascada no genere cuota_pagos
    (cupo cubierto, sin cuotas pendientes, etc.). No bajar a PENDIENTE+!conciliado.
    """
    estado = _estado_pago_tras_aplicar_cascada(cuotas_completadas, cuotas_parciales)

    if estado == "PAGADO":
        # Cascada con abono: el flag debe coincidir (evita PAGADO + conciliado=False).
        marcar_pago_autoconciliado(pago)
        return estado

    if pago_preserva_autoconciliacion_sin_cuotas(pago) or bool(
        getattr(pago, "conciliado", False)
    ):
        marcar_pago_autoconciliado(pago)
        return "PAGADO"

    return estado
''',
        '''def _estado_conciliacion_post_cascada(pago: Pago, cuotas_completadas: int, cuotas_parciales: int) -> str:
    """
    Alinea estado tras cascada.

    Política: todo pago operativo se autoconcilia sin excepción (conciliado + SI + PAGADO),
    aunque la cascada no genere cuota_pagos (cupo cubierto, sin pendientes, remanente, etc.).
    ``cuotas_completadas`` / ``cuotas_parciales`` quedan para trazabilidad del caller.
    """
    _ = (cuotas_completadas, cuotas_parciales, _estado_pago_tras_aplicar_cascada)
    marcar_pago_autoconciliado(pago)
    return "PAGADO"
''',
    )

    p = ROOT / "backend/app/api/v1/endpoints/pagos/pago_conciliacion_estado.py"
    text = p.read_text(encoding="utf-8")
    text2 = text.replace(
        "from app.services.pago_autoconciliacion import (\n"
        "    marcar_pago_autoconciliado,\n"
        "    pago_preserva_autoconciliacion_sin_cuotas,\n"
        ")\n",
        "from app.services.pago_autoconciliacion import marcar_pago_autoconciliado\n",
    )
    if text2 == text:
        raise SystemExit("import cleanup failed")
    p.write_text(text2, encoding="utf-8")
    print("cleaned import pago_conciliacion_estado")

    replace_once(
        ROOT / "backend/app/services/pagos_gmail/parse_campos_comprobante.py",
        '''def reportado_exento_autoconciliacion(val: Any, *, moneda: Optional[str] = None) -> bool:
    """
    Excepciones de negocio: no autoconciliar aunque el resto de validadores cuadre.

    - Pago en bolivares (BS).
    - Monto >= umbral en la moneda reportada (500 USD o 500 Bs; sin conversion).
    """
    if moneda_reportado_es_bolivares(moneda):
        return True
    return monto_requiere_revision_manual(val, moneda=moneda)
''',
        '''def reportado_exento_autoconciliacion(val: Any, *, moneda: Optional[str] = None) -> bool:
    """
    True si el reportado NO debe autoconciliar pese a validadores OK.

    Política actual: sin excepciones de monto/BS — siempre False.
    (``val`` / ``moneda`` se conservan por compatibilidad de firma con callers.)
    """
    _ = (val, moneda)
    return False
''',
    )

    replace_once(
        ROOT / "backend/app/services/pagos_gmail/plantilla_abcd_proceso_negocio.py",
        '''def monto_gmail_sync_requiere_revision_manual_usd(monto_str: Optional[str]) -> bool:
    """
    True si el valor numerico parseado del comprobante es >= 1000 (cualquier moneda en el texto).
    """
    raw = (monto_str or "").strip()
    if not raw or raw.upper() in ("NA", "NR"):
        return False
    txt = format_monto_excel_pagos_gmail(monto_str)
    if txt:
        return monto_requiere_revision_manual(txt)
    return monto_requiere_revision_manual(monto_str)
''',
        '''def monto_gmail_sync_requiere_revision_manual_usd(monto_str: Optional[str]) -> bool:
    """
    True si el monto Gmail debe ir a revision manual por umbral.

    Política actual: sin excepciones de monto — siempre False (autoconciliar).
    """
    _ = monto_str
    return False
''',
    )

    replace_once(
        ROOT / "backend/app/services/pagos_aplicacion_prestamo.py",
        '''            if cc > 0 or cp > 0:
                pago.estado = "PAGADO"
                n += 1
            elif pago_preserva_autoconciliacion_sin_cuotas(pago):
                marcar_pago_autoconciliado(pago)
            else:
                sin_abono.append(int(pago.id))
''',
        '''            if cc > 0 or cp > 0:
                marcar_pago_autoconciliado(pago)
                n += 1
            else:
                # Sin cuota_pagos nuevo: igual se autoconcilia (cupo cubierto / sin pendientes).
                marcar_pago_autoconciliado(pago)
                if not pago_preserva_autoconciliacion_sin_cuotas(pago):
                    sin_abono.append(int(pago.id))
''',
    )

    replace_once(
        ROOT / "backend/app/services/conciliacion_automatica_service.py",
        '''                if saldo_pago > Decimal('0.01'):
                    # Evitar pagos en limbo: dejar explícitamente no conciliado y pendiente de revisión manual.
                    pago.conciliado = False
                    pago.verificado_concordancia = 'NO'
                    pago.estado = 'PENDIENTE'
                    nota_limbo = f'Remanente sin asignar en conciliación automática: {saldo_pago}'
                    pago.notas = f'{(pago.notas or "").strip()} | {nota_limbo}'.strip(' |')
                    resultado['errores'].append(
                        f'Pago {pago.id}: Sobra {saldo_pago} sin asignar.'
                    )
                    resultado['fallidas'] += 1
''',
        '''                from app.services.pago_autoconciliacion import marcar_pago_autoconciliado

                # Política: todo pago operativo queda autoconciliado (también con remanente).
                marcar_pago_autoconciliado(pago)
                if saldo_pago > Decimal('0.01'):
                    nota_limbo = f'Remanente sin asignar en conciliación automática: {saldo_pago}'
                    pago.notas = f'{(pago.notas or "").strip()} | {nota_limbo}'.strip(' |')
                    resultado['errores'].append(
                        f'Pago {pago.id}: Sobra {saldo_pago} sin asignar (pago permanece conciliado).'
                    )
''',
    )

    replace_once(
        ROOT / "backend/tests/test_pago_autoconciliacion.py",
        '''def test_estado_post_cascada_pago_normal_sin_cuotas_baja_conciliado():
    p = _pago(conciliado=True, verificado_concordancia="NO", estado="PAGADO")
    estado = _estado_conciliacion_post_cascada(p, 0, 0)
    assert estado == "PENDIENTE"
    assert p.conciliado is False
    assert p.fecha_conciliacion is None
''',
        '''def test_estado_post_cascada_pago_normal_sin_cuotas_queda_autoconciliado():
    p = _pago(conciliado=False, verificado_concordancia="NO", estado="PENDIENTE")
    estado = _estado_conciliacion_post_cascada(p, 0, 0)
    assert estado == "PAGADO"
    assert p.conciliado is True
    assert (p.verificado_concordancia or "").upper() == "SI"
    assert p.fecha_conciliacion is not None
''',
    )

    replace_once(
        ROOT / "backend/tests/test_escaner_infopagos_parsers.py",
        '''def test_monto_requiere_revision_manual_umbral():
    from app.services.pagos_gmail.parse_campos_comprobante import (
        MONTO_UMBRAL_REVISION_MANUAL,
        fusionar_validacion_reglas_monto_alto_escaneo,
        monto_requiere_revision_manual,
    )

    assert MONTO_UMBRAL_REVISION_MANUAL == 500.0
    assert monto_requiere_revision_manual(500)
    assert monto_requiere_revision_manual(500.01)
    assert not monto_requiere_revision_manual(499.99)
    assert monto_requiere_revision_manual(1500, moneda="BS")
    assert monto_requiere_revision_manual(1500, moneda="USD")
    msg = fusionar_validacion_reglas_monto_alto_escaneo(None, 1500, moneda="USD")
    assert msg is not None
    assert "500" in msg


def test_reportado_exento_autoconciliacion_bs_y_monto():
    from app.services.pagos_gmail.parse_campos_comprobante import (
        reportado_exento_autoconciliacion,
    )

    assert reportado_exento_autoconciliacion(100, moneda="BS")
    assert not reportado_exento_autoconciliacion(100, moneda="USD")
    assert reportado_exento_autoconciliacion(500, moneda="USD")
    assert reportado_exento_autoconciliacion(600, moneda="USDT")
''',
        '''def test_monto_requiere_revision_manual_umbral():
    from app.services.pagos_gmail.parse_campos_comprobante import (
        MONTO_UMBRAL_REVISION_MANUAL,
        fusionar_validacion_reglas_monto_alto_escaneo,
        monto_requiere_revision_manual,
    )

    assert MONTO_UMBRAL_REVISION_MANUAL == 500.0
    assert monto_requiere_revision_manual(500)
    assert monto_requiere_revision_manual(500.01)
    assert not monto_requiere_revision_manual(499.99)
    assert monto_requiere_revision_manual(1500, moneda="BS")
    assert monto_requiere_revision_manual(1500, moneda="USD")
    # Política: no hay excepción de autoconciliación por monto/BS.
    assert fusionar_validacion_reglas_monto_alto_escaneo(None, 1500, moneda="USD") is None


def test_reportado_exento_autoconciliacion_sin_excepciones():
    from app.services.pagos_gmail.parse_campos_comprobante import (
        reportado_exento_autoconciliacion,
    )

    assert not reportado_exento_autoconciliacion(100, moneda="BS")
    assert not reportado_exento_autoconciliacion(100, moneda="USD")
    assert not reportado_exento_autoconciliacion(500, moneda="USD")
    assert not reportado_exento_autoconciliacion(600, moneda="USDT")
''',
    )

    replace_once(
        ROOT / "backend/tests/test_conciliacion_automatica_service.py",
        '''def test_conciliacion_remanente_marca_pago_pendiente_y_no_conciliado(db: Session):
''',
        '''def test_conciliacion_remanente_permanece_conciliado(db: Session):
''',
    )
    replace_once(
        ROOT / "backend/tests/test_conciliacion_automatica_service.py",
        '''    errores = out.get("errores") or []
    assert any(f"Pago {pago.id}: Sobra" in e for e in errores)
    assert int(out.get("fallidas") or 0) >= 1
    assert pago.conciliado is False
    assert (pago.verificado_concordancia or "").upper() == "NO"
    assert (pago.estado or "").upper() == "PENDIENTE"
    assert "Remanente sin asignar en conciliación automática" in (pago.notas or "")
''',
        '''    errores = out.get("errores") or []
    assert any(f"Pago {pago.id}: Sobra" in e for e in errores)
    assert pago.conciliado is True
    assert (pago.verificado_concordancia or "").upper() == "SI"
    assert (pago.estado or "").upper() == "PAGADO"
    assert "Remanente sin asignar en conciliación automática" in (pago.notas or "")
''',
    )

    print("done")


if __name__ == "__main__":
    main()
