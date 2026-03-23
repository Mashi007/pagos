# Temporary script to inject endpoints into prestamos.py
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
text = p.read_text(encoding="utf-8", errors="replace")

old_import = "from app.services.pagos_cuotas_sincronizacion import sincronizar_pagos_pendientes_a_prestamos\n"
new_import = (
    "from app.services.pagos_cuotas_sincronizacion import sincronizar_pagos_pendientes_a_prestamos\n"
    "from app.services.pagos_cuotas_reaplicacion import reset_y_reaplicar_fifo_prestamo\n"
)
if new_import.splitlines()[1].strip() not in text:
    if old_import not in text:
        raise SystemExit("import anchor not found")
    text = text.replace(old_import, new_import, 1)

marker = "class ConciliarAmortizacionMasivaBody(BaseModel):"
if marker not in text:
    raise SystemExit("marker not found")

injection = '''

class ReaplicarFifoMasivaBody(BaseModel):
    """Lista de prestamo_id a reaplicar FIFO (reset cuota_pagos + aplicar de nuevo). Maximo 500."""

    prestamo_ids: List[int]


@router.post("/{prestamo_id}/reaplicar-fifo-aplicacion", response_model=dict)
def reaplicar_fifo_aplicacion_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Reaplicacion integral FIFO para un prestamo: borra cuota_pagos, resetea totales en cuotas
    y vuelve a aplicar todos los pagos conciliados en orden (fecha_pago, id).

    Usar cuando la tabla de amortizacion no refleja los pagos pese a filas en `pagos`
    (articulacion vieja, regeneracion de cuotas, o desalineacion total_pagado vs cuota_pagos).

    Solo administrador.
    """
    if (getattr(current_user, "rol", None) or "").lower() != "administrador":
        raise HTTPException(
            status_code=403,
            detail="Solo administracion puede reaplicar FIFO sobre cuotas.",
        )
    try:
        r = reset_y_reaplicar_fifo_prestamo(db, prestamo_id)
        if not r.get("ok"):
            raise HTTPException(status_code=404, detail=r.get("error") or "No se pudo reaplicar")
        db.commit()
        return {
            **r,
            "mensaje": "FIFO reaplicado: cuota_pagos reiniciado y pagos conciliados aplicados de nuevo.",
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("reaplicar-fifo-aplicacion prestamo_id=%s: %s", prestamo_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reaplicar-fifo-aplicacion-masiva", response_model=dict)
def reaplicar_fifo_aplicacion_masiva(
    body: ReaplicarFifoMasivaBody,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Igual que /{prestamo_id}/reaplicar-fifo-aplicacion pero para varios prestamos.
    Solo administrador. Maximo 500 IDs por solicitud.
    """
    if (getattr(current_user, "rol", None) or "").lower() != "administrador":
        raise HTTPException(
            status_code=403,
            detail="Solo administracion puede reaplicar FIFO masivo.",
        )
    ids = [int(x) for x in (body.prestamo_ids or []) if x is not None]
    if not ids:
        raise HTTPException(status_code=400, detail="prestamo_ids requerido")
    if len(ids) > 500:
        raise HTTPException(status_code=400, detail="Maximo 500 prestamo_ids por solicitud")
    ok: list[dict] = []
    errores: list[dict] = []
    for pid in ids:
        try:
            r = reset_y_reaplicar_fifo_prestamo(db, pid)
            if r.get("ok"):
                ok.append(r)
                db.commit()
            else:
                db.rollback()
                errores.append({"prestamo_id": pid, "error": r.get("error") or "fallo"})
        except HTTPException as he:
            db.rollback()
            errores.append({"prestamo_id": pid, "error": he.detail})
        except Exception as e:
            db.rollback()
            logger.exception("reaplicar-fifo-masiva prestamo_id=%s: %s", pid, e)
            errores.append({"prestamo_id": pid, "error": str(e)})
    return {
        "procesados": len(ids),
        "exitosos": len(ok),
        "resultados": ok,
        "errores": errores,
        "mensaje": f"FIFO masivo: {len(ok)} ok, {len(errores)} error(es).",
    }

'''

if "reaplicar_fifo_aplicacion_prestamo" in text:
    print("already injected")
else:
    text = text.replace(marker, injection + marker, 1)
    p.write_text(text, encoding="utf-8", newline="\n")
    print("injected")
