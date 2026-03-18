"""
Add POST /pagos/con-errores/batch to create multiple pagos con errores in one request.
"""
path = "app/api/v1/endpoints/pagos_con_errores.py"

batch_body_class = '''
class PagoConErrorBatchBody(BaseModel):
    """Hasta 500 pagos con error en una sola peticion."""
    pagos: list[PagoConErrorCreate]

    @field_validator("pagos")
    @classmethod
    def pagos_limite(cls, v: list) -> list:
        if len(v) > 500:
            raise ValueError("Maximo 500 items por lote.")
        return v


'''

batch_endpoint = '''
@router.post("/batch", response_model=dict, status_code=201)
def crear_pagos_con_error_batch(body: PagoConErrorBatchBody, db: Session = Depends(get_db)):
    """Crea varios pagos con errores en una sola transaccion (Guardar todos desde Carga Masiva)."""
    from pydantic import field_validator
    results: list[dict] = []
    try:
        for payload in body.pagos:
            try:
                fecha_ts = datetime.strptime(payload.fecha_pago, "%Y-%m-%d").replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            except ValueError:
                results.append({"success": False, "error": "fecha_pago debe ser YYYY-MM-DD", "payload_index": len(results)})
                continue
            ref = (payload.numero_documento or "").strip() or "N/A"
            row = PagoConError(
                cedula_cliente=(payload.cedula_cliente or "").strip(),
                prestamo_id=payload.prestamo_id,
                fecha_pago=fecha_ts,
                monto_pagado=payload.monto_pagado,
                numero_documento=(payload.numero_documento or "").strip() or None,
                institucion_bancaria=(payload.institucion_bancaria or "").strip() or None if payload.institucion_bancaria else None,
                estado="PENDIENTE",
                conciliado=payload.conciliado if payload.conciliado is not None else False,
                notas=payload.notas,
                referencia_pago=ref,
                errores_descripcion=payload.errores_descripcion,
                observaciones=(payload.observaciones or "").strip() or None if payload.observaciones else None,
                fila_origen=payload.fila_origen,
            )
            db.add(row)
            db.flush()
            db.refresh(row)
            results.append({"success": True, "pago": _pago_con_error_to_response(row)})
        db.commit()
        return {"results": results, "ok_count": sum(1 for r in results if r.get("success")), "fail_count": sum(1 for r in results if not r.get("success"))}
    except Exception as e:
        db.rollback()
        logger.exception("Error en POST /pagos/con-errores/batch: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

'''

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add field_validator import if not present
if "field_validator" not in content and "from pydantic import" in content:
    content = content.replace("from pydantic import BaseModel", "from pydantic import BaseModel, field_validator")

# Insert batch body class after PagoConErrorUpdate
if "class PagoConErrorBatchBody" not in content:
    content = content.replace(
        "    observaciones: Optional[str] = None\n\n\ndef _pago_con_error_to_response",
        "    observaciones: Optional[str] = None\n\n\nclass PagoConErrorBatchBody(BaseModel):\n    \"\"\"Hasta 500 pagos con error en una sola peticion.\"\"\"\n    pagos: list[PagoConErrorCreate]\n\n    @field_validator(\"pagos\")\n    @classmethod\n    def pagos_limite(cls, v: list) -> list:\n        if len(v) > 500:\n            raise ValueError(\"Maximo 500 items por lote.\")\n        return v\n\n\ndef _pago_con_error_to_response",
    )
    print("Added PagoConErrorBatchBody")
else:
    print("PagoConErrorBatchBody already present")

# Insert batch endpoint after crear_pago_con_error (after "return _pago_con_error_to_response(row)" and before EliminarPorDescargaBody)
if 'def crear_pago_con_error_batch' not in content:
    content = content.replace(
        "    return _pago_con_error_to_response(row)\n\n\nclass EliminarPorDescargaBody",
        "    return _pago_con_error_to_response(row)\n\n\n@router.post(\"/batch\", response_model=dict, status_code=201)\n"
        "def crear_pagos_con_error_batch(body: PagoConErrorBatchBody, db: Session = Depends(get_db)):\n"
        '    """Crea varios pagos con errores en una sola transaccion (Guardar todos desde Carga Masiva)."""\n'
        "    results: list[dict] = []\n"
        "    try:\n"
        "        for payload in body.pagos:\n"
        "            try:\n"
        "                fecha_ts = datetime.strptime(payload.fecha_pago, \"%Y-%m-%d\").replace(\n"
        "                    hour=0, minute=0, second=0, microsecond=0\n"
        "                )\n"
        "            except ValueError:\n"
        "                results.append({\"success\": False, \"error\": \"fecha_pago debe ser YYYY-MM-DD\", \"payload_index\": len(results)})\n"
        "                continue\n"
        "            ref = (payload.numero_documento or \"\").strip() or \"N/A\"\n"
        "            row = PagoConError(\n"
        "                cedula_cliente=(payload.cedula_cliente or \"\").strip(),\n"
        "                prestamo_id=payload.prestamo_id,\n"
        "                fecha_pago=fecha_ts,\n"
        "                monto_pagado=payload.monto_pagado,\n"
        "                numero_documento=(payload.numero_documento or \"\").strip() or None,\n"
        "                institucion_bancaria=(payload.institucion_bancaria or \"\").strip() or None if payload.institucion_bancaria else None,\n"
        "                estado=\"PENDIENTE\",\n"
        "                conciliado=payload.conciliado if payload.conciliado is not None else False,\n"
        "                notas=payload.notas,\n"
        "                referencia_pago=ref,\n"
        "                errores_descripcion=payload.errores_descripcion,\n"
        "                observaciones=(payload.observaciones or \"\").strip() or None if payload.observaciones else None,\n"
        "                fila_origen=payload.fila_origen,\n"
        "            )\n"
        "            db.add(row)\n"
        "            db.flush()\n"
        "            db.refresh(row)\n"
        "            results.append({\"success\": True, \"pago\": _pago_con_error_to_response(row)})\n"
        "        db.commit()\n"
        "        ok = sum(1 for r in results if r.get(\"success\"))\n"
        "        return {\"results\": results, \"ok_count\": ok, \"fail_count\": len(results) - ok}\n"
        "    except Exception as e:\n"
        "        db.rollback()\n"
        "        logger.exception(\"Error en POST /pagos/con-errores/batch: %s\", e)\n"
        "        raise HTTPException(status_code=500, detail=str(e)) from e\n\n\nclass EliminarPorDescargaBody",
    )
    print("Added crear_pagos_con_error_batch endpoint")
else:
    print("Batch endpoint already present")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done.")
