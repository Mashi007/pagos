# -*- coding: utf-8 -*-
"""Apply Cobros alignment + duplicate doc normalization + UI importado."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COBROS_PUBLICO = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "cobros_publico.py"
COBROS = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "cobros.py"
PAGOS_PAGE = ROOT / "frontend" / "src" / "pages" / "CobrosPagosReportadosPage.tsx"

HELPER = '''

def _prestamos_aprobados_del_cliente(db: Session, cliente_id: int) -> list:
    """Misma regla que importar reportados a pagos: solo préstamos en estado APROBADO."""
    rows = db.execute(
        select(Prestamo)
        .where(Prestamo.cliente_id == cliente_id, Prestamo.estado == "APROBADO")
        .order_by(Prestamo.id)
    ).scalars().all()
    return [p for p in rows if p is not None]


def _error_si_no_puede_reportar_en_web(prestamos_aprobados: list) -> Optional[str]:
    """
    El formulario web asigna el pago a un único préstamo APROBADO. Si hay 0 o >1, coherente con importación a pagos.
    """
    if len(prestamos_aprobados) == 0:
        return (
            "No tiene un crédito en estado APROBADO para reportar pagos en línea. "
            "Si su crédito está en otro estado o ya fue liquidado, contacte a cobranza."
        )
    if len(prestamos_aprobados) > 1:
        return (
            "Su cédula tiene más de un crédito aprobado activo; el reporte en línea no está disponible. "
            "Contacte a RapiCredit / cobranza para indicar a qué crédito corresponde el pago."
        )
    return None
'''


def patch_cobros_publico() -> None:
    t = COBROS_PUBLICO.read_text(encoding="utf-8")
    if "_prestamos_aprobados_del_cliente" in t:
        print("cobros_publico: already patched")
        return
    anchor = "logger = logging.getLogger(__name__)\n\ndef _intentar_importar_reportado_automatico"
    if anchor not in t:
        raise SystemExit("cobros_publico: anchor for helper not found")
    t = t.replace(
        anchor,
        "logger = logging.getLogger(__name__)" + HELPER + "\n\ndef _intentar_importar_reportado_automatico",
        1,
    )

    old_val = """    # ¿Tiene préstamo? (cualquier préstamo asociado al cliente)
    prestamo = db.execute(
        select(Prestamo).where(Prestamo.cliente_id == cliente.id).limit(1)
    ).scalars().first()
    if not prestamo:
        return ValidarCedulaResponse(ok=False, error="La cédula no tiene un préstamo asociado en nuestro sistema.")"""
    new_val = """    prestamos_aprob = _prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = _error_si_no_puede_reportar_en_web(prestamos_aprob)
    if err_pres:
        return ValidarCedulaResponse(ok=False, error=err_pres)"""
    if old_val not in t:
        raise SystemExit("cobros_publico: validar block not found")
    t = t.replace(old_val, new_val, 1)

    old_env = """    if not cliente:
        return EnviarReporteResponse(ok=False, error="La cédula no está registrada.")
    prestamo = db.execute(select(Prestamo).where(Prestamo.cliente_id == cliente.id).limit(1)).scalars().first()
    if not prestamo:
        return EnviarReporteResponse(ok=False, error="No tiene préstamo asociado.")"""
    new_env = """    if not cliente:
        return EnviarReporteResponse(ok=False, error="La cédula no está registrada.")
    prestamos_aprob = _prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = _error_si_no_puede_reportar_en_web(prestamos_aprob)
    if err_pres:
        return EnviarReporteResponse(ok=False, error=err_pres)"""
    if old_env not in t:
        raise SystemExit("cobros_publico: enviar-reporte block not found")
    t = t.replace(old_env, new_env, 1)

    old_info = """    if not cliente:
        return EnviarReporteInfopagosResponse(ok=False, error="La cédula no está registrada.")
    prestamo = db.execute(select(Prestamo).where(Prestamo.cliente_id == cliente.id).limit(1)).scalars().first()
    if not prestamo:
        return EnviarReporteInfopagosResponse(ok=False, error="No tiene préstamo asociado.")"""
    new_info = """    if not cliente:
        return EnviarReporteInfopagosResponse(ok=False, error="La cédula no está registrada.")
    prestamos_aprob = _prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = _error_si_no_puede_reportar_en_web(prestamos_aprob)
    if err_pres:
        return EnviarReporteInfopagosResponse(ok=False, error=err_pres)"""
    if old_info not in t:
        raise SystemExit("cobros_publico: infopagos block not found")
    t = t.replace(old_info, new_info, 1)

    COBROS_PUBLICO.write_text(t, encoding="utf-8")
    print("cobros_publico: OK")


def patch_cobros() -> None:
    t = COBROS.read_text(encoding="utf-8")
    if "from app.core.documento import normalize_documento" not in t:
        # after other app.core imports
        ins = "from app.core.database import get_db\n"
        if ins not in t:
            raise SystemExit("cobros: database import not found")
        t = t.replace(ins, ins + "from app.core.documento import normalize_documento\n", 1)

    old_block = """    num_ops = list({(r.numero_operacion or "").strip() for r in rows if (r.numero_operacion or "").strip()})
    numeros_doc_en_pagos = set()
    if num_ops:
        existing_docs = db.execute(
            select(Pago.numero_documento).where(Pago.numero_documento.in_(num_ops))
        ).scalars().all()
        numeros_doc_en_pagos = {row[0] for row in existing_docs if row[0]}"""
    new_block = """    num_ops_raw = list({(r.numero_operacion or "").strip() for r in rows if (r.numero_operacion or "").strip()})
    norms_for_query = {n for o in num_ops_raw for n in [normalize_documento(o)] if n}
    numeros_doc_en_pagos = set()
    if norms_for_query:
        existing_docs = db.execute(
            select(Pago.numero_documento).where(Pago.numero_documento.in_(list(norms_for_query)))
        ).scalars().all()
        numeros_doc_en_pagos = {str(d) for d in existing_docs if d}"""
    if old_block not in t:
        raise SystemExit("cobros: num_ops block not found")
    t = t.replace(old_block, new_block, 1)

    old_loop = """        num_op = (r.numero_operacion or "").strip()
        if num_op and num_op in numeros_doc_en_pagos:
            partes.append("DUPLICADO DOC")"""
    new_loop = """        num_op = (r.numero_operacion or "").strip()
        n_doc = normalize_documento(num_op) if num_op else None
        if n_doc and n_doc in numeros_doc_en_pagos:
            partes.append("DUPLICADO DOC")"""
    if old_loop not in t:
        raise SystemExit("cobros: observacion loop not found")
    t = t.replace(old_loop, new_loop, 1)

    COBROS.write_text(t, encoding="utf-8")
    print("cobros.py: OK")


def patch_frontend() -> None:
    t = PAGOS_PAGE.read_text(encoding="utf-8")
    old_cfg = """const ESTADO_CONFIG: Record<string, { label: string; short: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; Icon: typeof Clock }> = {
  pendiente: { label: 'Pendiente', short: 'Pend.', variant: 'secondary', Icon: Clock },
  en_revision: { label: 'En revisión (manual)', short: 'Revisión', variant: 'outline', Icon: Search },
  aprobado: { label: 'Aprobado', short: 'Aprobado', variant: 'default', Icon: CheckCircle },
  rechazado: { label: 'Rechazado', short: 'Rechazado', variant: 'destructive', Icon: XCircle },
}"""
    new_cfg = """const ESTADO_CONFIG: Record<string, { label: string; short: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; Icon: typeof Clock }> = {
  pendiente: { label: 'Pendiente', short: 'Pend.', variant: 'secondary', Icon: Clock },
  en_revision: { label: 'En revisión (manual)', short: 'Revisión', variant: 'outline', Icon: Search },
  aprobado: { label: 'Aprobado', short: 'Aprobado', variant: 'default', Icon: CheckCircle },
  importado: { label: 'Importado a Pagos', short: 'Import.', variant: 'default', Icon: CheckCircle },
  rechazado: { label: 'Rechazado', short: 'Rechazado', variant: 'destructive', Icon: XCircle },
}"""
    if "importado:" in t and "Importado a Pagos" in t:
        print("frontend: ESTADO_CONFIG already has importado")
    else:
        if old_cfg not in t:
            raise SystemExit("frontend: ESTADO_CONFIG not found")
        t = t.replace(old_cfg, new_cfg, 1)

    old_opt = """            <option value="rechazado">Rechazado</option>
          </select>"""
    new_opt = """            <option value="rechazado">Rechazado</option>
            <option value="importado">Importado a Pagos</option>
          </select>"""
    if '<option value="importado">' not in t:
        if old_opt not in t:
            raise SystemExit("frontend: select options not found")
        t = t.replace(old_opt, new_opt, 1)

    PAGOS_PAGE.write_text(t, encoding="utf-8")
    print("CobrosPagosReportadosPage: OK")


def main() -> None:
    patch_cobros_publico()
    patch_cobros()
    patch_frontend()


if __name__ == "__main__":
    main()
