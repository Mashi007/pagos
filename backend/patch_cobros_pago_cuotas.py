# Script one-off historico (COB-+RPC). La app usa documento efectivo en cobros.py
# (pago_reportado_documento). No ejecutar salvo migracion puntual; conservar solo referencia.
# Script to add helper and call in cobros.py - run once then delete
from pathlib import Path

p = Path("app/api/v1/endpoints/cobros.py")
t = p.read_text(encoding="utf-8", errors="replace")

helper = r'''
def _crear_pago_desde_reportado_y_aplicar_cuotas(db: Session, pr: PagoReportado, usuario_email: Optional[str]) -> None:
    """Tras aprobar un pago reportado: crea registro en tabla pagos y aplica a cuotas (cascada) para que prestamos y estado de cuenta se actualicen igual que por /pagos/pagos."""
    try:
        cedula_norm = ((pr.tipo_cedula or "") + (pr.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
        if not cedula_norm:
            return
        cliente = db.execute(
            select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_norm)
        ).scalars().first()
        if not cliente:
            logger.info("[COBROS] Aprobar ref=%s: no se encontro cliente con cedula; no se crea pago en tabla pagos.", pr.referencia_interna)
            return
        prestamo = db.execute(
            select(Prestamo)
            .where(Prestamo.cliente_id == cliente.id, Prestamo.estado == "APROBADO")
            .order_by(Prestamo.id.desc())
            .limit(1)
        ).scalars().first()
        if not prestamo:
            logger.info("[COBROS] Aprobar ref=%s: cliente sin prestamo APROBADO; no se crea pago.", pr.referencia_interna)
            return
        num_doc = ("COB-" + pr.referencia_interna)[:100]
        if db.execute(select(Pago.id).where(Pago.numero_documento == num_doc)).scalar() is not None:
            logger.info("[COBROS] Aprobar ref=%s: ya existe pago con documento %s; omitir creacion.", pr.referencia_interna, num_doc)
            return
        fecha_ts = datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now()
        monto = Decimal(str(round(float(pr.monto), 2)))
        if monto <= 0:
            return
        row = Pago(
            cedula_cliente=cedula_norm,
            prestamo_id=prestamo.id,
            fecha_pago=fecha_ts,
            monto_pagado=monto,
            numero_documento=num_doc,
            institucion_bancaria=(pr.institucion_financiera or "").strip()[:255] or None,
            estado="PENDIENTE",
            referencia_pago=num_doc,
            usuario_registro=usuario_email or "cobros@rapicredit.com",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        _aplicar_pago_a_cuotas_interno(row, db)
        row.estado = "PAGADO"
        db.commit()
        logger.info("[COBROS] Aprobar ref=%s: creado pago id=%s y aplicado a cuotas del prestamo %s.", pr.referencia_interna, row.id, prestamo.id)
    except Exception as e:
        logger.warning("[COBROS] Aprobar ref=%s: no se pudo crear pago/aplicar cuotas: %s", pr.referencia_interna, e, exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass


'''

old = '    _registrar_historial(db, pago_id, estado_anterior, "aprobado", usuario_email, None)\n    db.commit()\n    return {"ok": True, "mensaje": mensaje_final}'
new = '    _registrar_historial(db, pago_id, estado_anterior, "aprobado", usuario_email, None)\n    db.commit()\n    _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)\n    return {"ok": True, "mensaje": mensaje_final}'

t = t.replace("    db.add(h)\n\n\n@router.post(\"/pagos-reportados/{pago_id}/aprobar\")", "    db.add(h)\n\n\n" + helper + "@router.post(\"/pagos-reportados/{pago_id}/aprobar\")")
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")
print("done")
