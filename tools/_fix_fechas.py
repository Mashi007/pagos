from pathlib import Path

# --- backend service ---
p = Path("backend/app/services/conciliacion_bancos_service.py")
t = p.read_text(encoding="utf-8")

old_create_end = '''        n += 1

    if n == 0:
        db.rollback()
        raise HTTPException(status_code=400, detail="No hay filas validas (Fecha, Referencia, Monto)")

    db.commit()
    db.refresh(lote)
    return lote


def comparar_lote(
    db: Session,
    lote_id: int,
    *,
    bancos_filtro: Optional[list[str]] = None,
) -> dict[str, Any]:
    lote = db.get(ConciliacionBancoOcrLote, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    bancos_sel = normalizar_bancos_filtro(bancos_filtro)
'''

new_create_end = '''        n += 1
        if fecha_b is not None:
            fechas_excel.append(fecha_b)

    if n == 0:
        db.rollback()
        raise HTTPException(status_code=400, detail="No hay filas validas (Fecha, Referencia, Monto)")

    # Ampliar rango BD para cubrir el Excel (si el form quedo en "hoy" u otro rango corto)
    if fechas_excel:
        excel_min = min(fechas_excel)
        excel_max = max(fechas_excel)
        lote.fecha_desde = min(lote.fecha_desde, excel_min)
        lote.fecha_hasta = max(lote.fecha_hasta, excel_max)

    db.commit()
    db.refresh(lote)
    return lote


def comparar_lote(
    db: Session,
    lote_id: int,
    *,
    bancos_filtro: Optional[list[str]] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> dict[str, Any]:
    lote = db.get(ConciliacionBancoOcrLote, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    if fecha_desde is not None or fecha_hasta is not None:
        fd = fecha_desde or lote.fecha_desde
        fh = fecha_hasta or lote.fecha_hasta
        if fh < fd:
            raise HTTPException(status_code=400, detail="fecha_hasta debe ser >= fecha_desde")
        lote.fecha_desde = fd
        lote.fecha_hasta = fh

    bancos_sel = normalizar_bancos_filtro(bancos_filtro)
'''

# Need fechas_excel list at start of loop - insert after flush
if "fechas_excel" not in t:
    t = t.replace(
        "    db.add(lote)\n    db.flush()\n\n    n = 0\n",
        "    db.add(lote)\n    db.flush()\n\n    n = 0\n    fechas_excel: list[date] = []\n",
        1,
    )

if old_create_end not in t:
    raise SystemExit("create/comparar block missing")
t = t.replace(old_create_end, new_create_end, 1)

# Return fecha in comparar result - check return dict
old_ret = '''    return {
        "lote_id": lote_id,
        "estado": lote.estado,
        "stats": stats,
        "bancos_filtro": bancos_sel,
        "pagos_universo": len(pagos),
'''
if old_ret in t and '"fecha_desde"' not in t[t.find(old_ret):t.find(old_ret)+400]:
    t = t.replace(
        old_ret,
        '''    return {
        "lote_id": lote_id,
        "estado": lote.estado,
        "stats": stats,
        "bancos_filtro": bancos_sel,
        "fecha_desde": lote.fecha_desde.isoformat() if lote.fecha_desde else None,
        "fecha_hasta": lote.fecha_hasta.isoformat() if lote.fecha_hasta else None,
        "pagos_universo": len(pagos),
''',
        1,
    )

p.write_text(t, encoding="utf-8")
print("service ok")

# --- routes ---
r = Path("backend/app/api/v1/endpoints/conciliacion_bancos/routes.py")
rt = r.read_text(encoding="utf-8")
rt = rt.replace(
'''class CompararBody(BaseModel):
    bancos: List[str] = Field(
        default_factory=list,
        description="Categorias: Mercantil, BNC, Binance, BNV, Recibos, Drive, Otros",
    )
''',
'''class CompararBody(BaseModel):
    bancos: List[str] = Field(
        default_factory=list,
        description="Categorias: Mercantil, BNC, Binance, BNV, Recibos, Drive, Otros",
    )
    fecha_desde: Optional[date] = Field(
        None, description="Opcional: actualiza rango BD del lote antes de comparar"
    )
    fecha_hasta: Optional[date] = Field(
        None, description="Opcional: actualiza rango BD del lote antes de comparar"
    )
''',
)
rt = rt.replace(
'''    return {
        "ok": True,
        **svc.comparar_lote(db, lote_id, bancos_filtro=body.bancos),
    }
''',
'''    return {
        "ok": True,
        **svc.comparar_lote(
            db,
            lote_id,
            bancos_filtro=body.bancos,
            fecha_desde=body.fecha_desde,
            fecha_hasta=body.fecha_hasta,
        ),
    }
''',
)
r.write_text(rt, encoding="utf-8")
print("routes ok")
