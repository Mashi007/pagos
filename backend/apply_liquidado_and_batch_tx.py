"""
Aplica: (1) estado LIQUIDADO en prestamos cuando todas las cuotas estan pagadas;
        (2) batch de pagos con transaccion unica por lote.
Ejecutar desde backend: python apply_liquidado_and_batch_tx.py
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parent

# 1) Schema prestamo: anadir LIQUIDADO
prestamo_schema = BACKEND / "app" / "schemas" / "prestamo.py"
t = prestamo_schema.read_text(encoding="utf-8", errors="replace")
t = t.replace(
    'PRESTAMO_ESTADOS_VALIDOS = frozenset({"APROBADO", "DRAFT", "EN_REVISION", "EVALUADO", "RECHAZADO"})',
    'PRESTAMO_ESTADOS_VALIDOS = frozenset({"APROBADO", "DRAFT", "EN_REVISION", "EVALUADO", "RECHAZADO", "LIQUIDADO"})',
)
prestamo_schema.write_text(t, encoding="utf-8")
print("OK prestamo schema LIQUIDADO")

# 2) prestamo_estado_validator si existe
validator = BACKEND / "app" / "schemas" / "prestamo_estado_validator.py"
if validator.exists():
    t = validator.read_text(encoding="utf-8", errors="replace")
    t = t.replace(
        'PRESTAMO_ESTADOS_VALIDOS = frozenset({"APROBADO", "DRAFT", "EN_REVISION", "EVALUADO", "RECHAZADO"})',
        'PRESTAMO_ESTADOS_VALIDOS = frozenset({"APROBADO", "DRAFT", "EN_REVISION", "EVALUADO", "RECHAZADO", "LIQUIDADO"})',
    )
    validator.write_text(t, encoding="utf-8")
    print("OK prestamo_estado_validator LIQUIDADO")

# 3) pagos.py: al final de _aplicar_pago_a_cuotas_interno, antes del return, anadir logica LIQUIDADO
pagos_py = BACKEND / "app" / "api" / "v1" / "endpoints" / "pagos.py"
t = pagos_py.read_text(encoding="utf-8", errors="replace")

# Buscar el return cuotas_completadas, cuotas_parciales justo despues de monto_restante -= a_aplicar
liquidado_logic = '''
    # Si todas las cuotas del prestamo quedaron pagadas, marcar prestamo como LIQUIDADO
    _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)
    return cuotas_completadas, cuotas_parciales'''

old_return = "        monto_restante -= a_aplicar\n    return cuotas_completadas, cuotas_parciales"
if old_return not in t:
    # puede ser con espacios distintos
    old_return2 = "        monto_restante -= a_aplicar\n    return cuotas_completadas, cuotas_parciales\n\n\n@router.post"
    if old_return2 in t:
        t = t.replace(
            "        monto_restante -= a_aplicar\n    return cuotas_completadas, cuotas_parciales\n\n\n@router.post",
            "        monto_restante -= a_aplicar\n    _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)\n    return cuotas_completadas, cuotas_parciales\n\n\n@router.post",
        )
    else:
        t = t.replace(
            "        monto_restante -= a_aplicar\n    return cuotas_completadas, cuotas_parciales",
            "        monto_restante -= a_aplicar\n    _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)\n    return cuotas_completadas, cuotas_parciales",
        )
else:
    t = t.replace(
        "        monto_restante -= a_aplicar\n    return cuotas_completadas, cuotas_parciales",
        "        monto_restante -= a_aplicar\n    _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)\n    return cuotas_completadas, cuotas_parciales",
    )

# Anadir la funcion _marcar_prestamo_liquidado_si_corresponde antes de _aplicar_pago_a_cuotas_interno
# Buscar "def _aplicar_pago_a_cuotas_interno"
marker = "def _aplicar_pago_a_cuotas_interno(pago: Pago, db: Session) -> tuple[int, int]:"
helper_func = '''
def _marcar_prestamo_liquidado_si_corresponde(prestamo_id: int, db: Session) -> None:
    """Si todas las cuotas del prestamo estan pagadas (total_pagado >= monto), actualiza prestamo.estado a LIQUIDADO. No hace commit."""
    from sqlalchemy import and_
    cuotas = db.execute(
        select(Cuota).where(Cuota.prestamo_id == prestamo_id)
    ).scalars().all()
    if not cuotas:
        return
    pendientes = sum(1 for c in cuotas if (c.total_pagado or 0) < (float(c.monto) if c.monto else 0) - 0.01)
    if pendientes == 0:
        prestamo = db.execute(select(Prestamo).where(Prestamo.id == prestamo_id)).scalars().first()
        if prestamo and (prestamo.estado or "").upper() == "APROBADO":
            prestamo.estado = "LIQUIDADO"
            logger.info("Prestamo id=%s marcado como LIQUIDADO (todas las cuotas pagadas).", prestamo_id)


'''
if "_marcar_prestamo_liquidado_si_corresponde" not in t:
    t = t.replace(marker, helper_func + marker)
pagos_py.write_text(t, encoding="utf-8")
print("OK pagos.py LIQUIDADO")

# 4) Batch: transaccion unica. Reemplazar el bloque del for en crear_pagos_batch.
# Estrategia: validar todo primero; si hay errores devolver sin insertar. Si todo OK: add+flush+apply para cada uno, luego un solo commit.
batch_old = """        docs_added_in_batch: set[str] = set()
        results: list[dict] = []
        ok_count = 0
        fail_count = 0
        for idx, payload in enumerate(pagos_list):
            try:
                num_doc = docs_en_payload[idx] if idx < len(docs_en_payload) else normalize_documento(payload.numero_documento)
                if num_doc and (num_doc in existing_docs or num_doc in docs_added_in_batch):
                    results.append({"index": idx, "success": False, "error": "Ya existe un pago con ese NA de documento.", "status_code": 409})
                    fail_count += 1
                    continue
                ref = (num_doc or "N/A")[:_MAX_LEN_NUMERO_DOCUMENTO]
                fecha_pago_ts = datetime.combine(payload.fecha_pago, dt_time.min)
                conciliado = payload.conciliado if payload.conciliado is not None else False
                cedula_normalizada = payload.cedula_cliente.strip().upper() if payload.cedula_cliente else ""
                if payload.prestamo_id and payload.prestamo_id not in valid_prestamo_ids:
                    results.append({"index": idx, "success": False, "error": f"CrAcdito #{payload.prestamo_id} no existe.", "status_code": 400})
                    fail_count += 1
                    continue
                if cedula_normalizada and payload.prestamo_id and cedula_normalizada not in valid_cedulas:
                    results.append({"index": idx, "success": False, "error": f"No existe cliente con cAcdula {cedula_normalizada}", "status_code": 404})
                    fail_count += 1
                    continue
                row = Pago(
                    cedula_cliente=cedula_normalizada,
                    prestamo_id=payload.prestamo_id,
                    fecha_pago=fecha_pago_ts,
                    monto_pagado=payload.monto_pagado,
                    numero_documento=num_doc,
                    institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,
                    estado="PENDIENTE",
                    notas=payload.notas.strip() if payload.notas else None,
                    referencia_pago=ref,
                    conciliado=conciliado,
                    fecha_conciliacion=datetime.now(ZoneInfo(TZ_NEGOCIO)) if conciliado else None,
                    verificado_concordancia="SI" if conciliado else "",
                    usuario_registro=usuario_email,
                )
                db.add(row)
                db.commit()
                db.refresh(row)
                if row.prestamo_id and float(row.monto_pagado or 0) > 0:
                    try:
                        _aplicar_pago_a_cuotas_interno(row, db)
                        row.estado = "PAGADO"
                        db.commit()
                        db.refresh(row)
                    except Exception as e:
                        logger.warning("Batch: no se pudo aplicar a cuotas (A-ndice %s): %s", idx, e)
                        db.rollback()
                results.append({"index": idx, "success": True, "pago": _pago_to_response(row)})
                ok_count += 1
                if num_doc:
                    docs_added_in_batch.add(num_doc)
            except IntegrityError as e:
                db.rollback()
                if getattr(getattr(e, "orig", None), "pgcode", None) == "23505":
                    results.append({"index": idx, "success": False, "error": "NA de documento duplicado.", "status_code": 409})
                else:
                    results.append({"index": idx, "success": False, "error": str(e), "status_code": 500})
                fail_count += 1
            except Exception as e:
                db.rollback()
                logger.exception("Batch A-ndice %s: %s", idx, e)
                results.append({"index": idx, "success": False, "error": str(e), "status_code": 500})
                fail_count += 1
        return {"results": results, "ok_count": ok_count, "fail_count": fail_count}"""

# Version con transaccion unica: primera pasada solo validacion; segunda pasada add+flush+apply y un commit al final
batch_new = """        # Fase 1: validacion (sin insertar). Si hay errores, devolver sin commit.
        validation_errors: list[dict] = []
        docs_added_in_batch: set[str] = set()
        for idx, payload in enumerate(pagos_list):
            num_doc = docs_en_payload[idx] if idx < len(docs_en_payload) else normalize_documento(payload.numero_documento)
            if num_doc and (num_doc in existing_docs or num_doc in docs_added_in_batch):
                validation_errors.append({"index": idx, "error": "Ya existe un pago con ese numero de documento.", "status_code": 409})
                continue
            ref = (num_doc or "N/A")[:_MAX_LEN_NUMERO_DOCUMENTO]
            cedula_normalizada = payload.cedula_cliente.strip().upper() if payload.cedula_cliente else ""
            if payload.prestamo_id and payload.prestamo_id not in valid_prestamo_ids:
                validation_errors.append({"index": idx, "error": f"Credito #{payload.prestamo_id} no existe.", "status_code": 400})
                continue
            if cedula_normalizada and payload.prestamo_id and cedula_normalizada not in valid_cedulas:
                validation_errors.append({"index": idx, "error": f"No existe cliente con cedula {cedula_normalizada}", "status_code": 404})
                continue
            if num_doc:
                docs_added_in_batch.add(num_doc)
        if validation_errors:
            return {"results": [{"index": e["index"], "success": False, "error": e["error"], "status_code": e["status_code"]} for e in validation_errors], "ok_count": 0, "fail_count": len(validation_errors)}

        # Fase 2: transaccion unica. Crear todos los pagos (flush), aplicar a cuotas, un commit al final.
        results: list[dict] = []
        created_rows: list[Pago] = []
        try:
            for idx, payload in enumerate(pagos_list):
                num_doc = docs_en_payload[idx] if idx < len(docs_en_payload) else normalize_documento(payload.numero_documento)
                ref = (num_doc or "N/A")[:_MAX_LEN_NUMERO_DOCUMENTO]
                fecha_pago_ts = datetime.combine(payload.fecha_pago, dt_time.min)
                conciliado = payload.conciliado if payload.conciliado is not None else False
                cedula_normalizada = payload.cedula_cliente.strip().upper() if payload.cedula_cliente else ""
                row = Pago(
                    cedula_cliente=cedula_normalizada,
                    prestamo_id=payload.prestamo_id,
                    fecha_pago=fecha_pago_ts,
                    monto_pagado=payload.monto_pagado,
                    numero_documento=num_doc,
                    institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,
                    estado="PENDIENTE",
                    notas=payload.notas.strip() if payload.notas else None,
                    referencia_pago=ref,
                    conciliado=conciliado,
                    fecha_conciliacion=datetime.now(ZoneInfo(TZ_NEGOCIO)) if conciliado else None,
                    verificado_concordancia="SI" if conciliado else "",
                    usuario_registro=usuario_email,
                )
                db.add(row)
                db.flush()
                db.refresh(row)
                if row.prestamo_id and float(row.monto_pagado or 0) > 0:
                    _aplicar_pago_a_cuotas_interno(row, db)
                    row.estado = "PAGADO"
                results.append({"index": idx, "success": True, "pago": _pago_to_response(row)})
                created_rows.append(row)
            db.commit()
            return {"results": results, "ok_count": len(results), "fail_count": 0}
        except Exception as e:
            db.rollback()
            logger.exception("Batch: error en transaccion unica: %s", e)
            raise HTTPException(status_code=500, detail=f"Error al guardar el lote. Ningun pago fue creado. Detalle: {str(e)}")"""

# En pagos.py el texto puede tener caracteres distintos (encoding). Buscar por fragmento unico.
t = pagos_py.read_text(encoding="utf-8", errors="replace")
if "Fase 1: validacion" in t:
    print("Batch ya aplicado, skip")
else:
    # Reemplazo por partes para evitar problemas de encoding
    t = pagos_py.read_text(encoding="utf-8", errors="replace")
    # Quitar el bloque viejo del for y reemplazar por el nuevo
    import re
    pattern = r"docs_added_in_batch: set\[str\] = set\(\)\s+results: list\[dict\] = \[\]\s+ok_count = 0\s+fail_count = 0\s+for idx, payload in enumerate\(pagos_list\):.*?return \{\"results\": results, \"ok_count\": ok_count, \"fail_count\": fail_count\}"
    if re.search(pattern, t, re.DOTALL):
        t = re.sub(pattern, batch_new.strip(), t, count=1, flags=re.DOTALL)
        pagos_py.write_text(t, encoding="utf-8")
        print("OK batch transaccion unica")
    else:
        print("WARN: no se encontro el bloque batch exacto para reemplazar (regex)")

print("Listo.")
