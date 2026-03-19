# Run from repo root: python scripts/patch_pagos_importar_un.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "backend/app/api/v1/endpoints/pagos.py"
text = P.read_text(encoding="utf-8")

ANCHOR = '\n\nORIGEN_COBROS_REPORTADOS = "Cobros (reportados aprobados)"\n'
if ANCHOR not in text:
    raise SystemExit("anchor not found")

FUNC = '''

def importar_un_pago_reportado_a_pagos(
    db: Session,
    pr: PagoReportado,
    *,
    usuario_email: str,
    documentos_ya_en_bd: set[str],
    docs_en_lote: set[str],
    registrar_error_en_tabla: bool = True,
) -> dict:
    """
    Crea un Pago desde un PagoReportado con las mismas validaciones que importar-desde-cobros.
    No hace commit ni aplica a cuotas (el lote o el caller aplican después).
    Retorna {"ok": True, "pago": Pago} o {"ok": False, "error": str, "referencia": ..., "pce_id": int|None}.
    """
    ref_display = (pr.referencia_interna or "").strip()[:100] or None

    def _err(msg: str) -> dict:
        return {"ok": False, "error": msg, "referencia": pr.referencia_interna, "pce_id": None}

    def _err_con_pce(msg: str, **pce_kw) -> dict:
        if not registrar_error_en_tabla:
            return _err(msg)
        ref = (pr.referencia_interna or "").strip()[:100] or "N/A"
        pce = DatosImportadosConErrores(
            cedula_cliente=pce_kw.get("cedula_cliente", ""),
            prestamo_id=pce_kw.get("prestamo_id"),
            fecha_pago=datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now(),
            monto_pagado=float(pr.monto or 0),
            numero_documento=(pr.referencia_interna or "")[:100],
            estado="PENDIENTE",
            referencia_pago=ref,
            errores_descripcion=[msg],
            observaciones=ORIGEN_COBROS_REPORTADOS,
            referencia_interna=(pr.referencia_interna or "")[:100] or None,
            fila_origen=pr.id,
        )
        db.add(pce)
        db.flush()
        return {"ok": False, "error": msg, "referencia": pr.referencia_interna, "pce_id": pce.id}

    cedula_raw = f"{pr.tipo_cedula or ''}{pr.numero_cedula or ''}".replace("-", "").strip().upper()
    if not cedula_raw:
        return _err_con_pce("Cédula vacía", cedula_cliente="")

    if not _looks_like_cedula_inline(cedula_raw):
        return _err_con_pce(
            "Cédula inválida. Formato: V, E o J + 6-11 dígitos (igual que Pagos desde Excel).",
            cedula_cliente=cedula_raw,
        )

    numero_doc_raw = (pr.referencia_interna or "").strip()[:100]
    numero_doc_norm = normalize_documento(numero_doc_raw)
    if numero_doc_norm and numero_doc_norm in documentos_ya_en_bd:
        return _err_con_pce("Ya existe un pago con ese Nº documento (duplicado en BD)", cedula_cliente=cedula_raw)
    if numero_doc_norm and numero_doc_norm in docs_en_lote:
        return _err_con_pce("Nº documento duplicado en este lote", cedula_cliente=cedula_raw)

    cliente = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_raw)
    ).scalars().first()
    if not cliente:
        return _err_con_pce("Cédula no encontrada en clientes", cedula_cliente=cedula_raw)

    prestamos = db.execute(
        select(Prestamo)
        .where(Prestamo.cliente_id == cliente.id, Prestamo.estado == "APROBADO")
        .order_by(Prestamo.id)
    ).scalars().all()
    prestamos = [p for p in prestamos if p is not None]
    if len(prestamos) == 0:
        return _err_con_pce("Sin crédito activo (APROBADO)", cedula_cliente=cedula_raw)
    if len(prestamos) > 1:
        return _err_con_pce(
            f"Cédula con {len(prestamos)} préstamos; indique ID del crédito",
            cedula_cliente=cedula_raw,
        )

    prestamo_id = prestamos[0].id
    monto = float(pr.monto or 0)
    if monto < _MIN_MONTO_PAGADO:
        return _err_con_pce(
            f"Monto debe ser mayor a {_MIN_MONTO_PAGADO}",
            cedula_cliente=cedula_raw,
            prestamo_id=prestamo_id,
        )

    ref_pago = (numero_doc_norm or numero_doc_raw or "Cobros")[:_MAX_LEN_NUMERO_DOCUMENTO]
    ahora_imp = datetime.now(ZoneInfo(TZ_NEGOCIO))
    p = Pago(
        cedula_cliente=cedula_raw,
        prestamo_id=prestamo_id,
        fecha_pago=datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now(),
        monto_pagado=Decimal(str(round(monto, 2))),
        numero_documento=numero_doc_norm,
        estado="PENDIENTE",
        referencia_pago=ref_pago,
        usuario_registro=usuario_email,
        conciliado=True,
        fecha_conciliacion=ahora_imp,
        verificado_concordancia="SI",
    )
    db.add(p)
    db.flush()
    if numero_doc_norm:
        docs_en_lote.add(numero_doc_norm)
        documentos_ya_en_bd.add(numero_doc_norm)
    return {"ok": True, "pago": p, "referencia": ref_display, "pce_id": None}

'''

if "def importar_un_pago_reportado_a_pagos(" not in text:
    text = text.replace(ANCHOR, FUNC + ANCHOR, 1)
    P.write_text(text, encoding="utf-8")
    print("inserted importar_un_pago_reportado_a_pagos")
else:
    print("importar_un already present, skip insert")

# Replace for-loop body: from "    for pr in reportados:" until "        pagos_creados.append(p)\n\n    cuotas_aplicadas"
P.read_text  # refresh
text = P.read_text(encoding="utf-8")
old_loop_start = "    for pr in reportados:\n        cedula_raw = f"
if old_loop_start not in text:
    raise SystemExit("for loop start not found (maybe already refactored)")

idx = text.find("    for pr in reportados:")
idx_end = text.find("\n\n    cuotas_aplicadas = 0", idx)
if idx_end < 0:
    raise SystemExit("cuotas_aplicadas anchor not found")

new_loop = """    for pr in reportados:
        res = importar_un_pago_reportado_a_pagos(
            db,
            pr,
            usuario_email=usuario_email,
            documentos_ya_en_bd=documentos_ya_en_bd,
            docs_en_lote=docs_en_lote,
            registrar_error_en_tabla=True,
        )
        if res.get("ok"):
            registros_procesados += 1
            pagos_creados.append(res["pago"])
            continue
        pce_id = res.get("pce_id")
        if pce_id is not None:
            ids_pagos_con_errores.append(pce_id)
        errores_detalle.append(
            {"referencia": res.get("referencia"), "error": res.get("error", "Error")}
        )
"""
text = text[:idx] + new_loop + text[idx_end:]
P.write_text(text, encoding="utf-8")
print("replaced import loop")
print("done")
