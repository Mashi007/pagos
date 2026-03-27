# Temporary script: insert KPI dashboard helper + route into kpis.py
from pathlib import Path

p = Path(
    r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\api\v1\endpoints\dashboard\kpis.py"
)
text = p.read_text(encoding="utf-8")

old_import = "    _meses_desde_rango,\n)"
new_import = "    _meses_desde_rango,\n    _parse_fechas_concesionario,\n)"
if old_import not in text:
    raise SystemExit("import block not found")
text = text.replace(old_import, new_import, 1)

marker = '@router.get("/opciones-filtros")'
if marker not in text:
    raise SystemExit("marker not found")

insert = '''

def _compute_kpis_dashboard_flat(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """Totales de financiamiento por estado (activo / inactivo / liquidado) para GET /kpis/dashboard."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    inicio, fin = _parse_fechas_concesionario(fecha_inicio, fecha_fin)

    producto_valido = func.nullif(func.nullif(func.trim(Prestamo.producto), ""), "Financiamiento")
    modelo_lbl = _modelo_label_dashboard_expr(producto_valido, incluir_sin_modelo=False)

    conds = [
        Prestamo.estado.in_(["APROBADO", "LIQUIDADO"]),
        func.date(Prestamo.fecha_registro) >= inicio,
        func.date(Prestamo.fecha_registro) <= fin,
    ]
    if analista:
        conds.append(Prestamo.analista == analista)
    if concesionario:
        conds.append(Prestamo.concesionario == concesionario)
    if modelo:
        conds.append(modelo_lbl == modelo)

    tf = func.coalesce(Prestamo.total_financiamiento, 0)
    sum_activo = func.coalesce(
        func.sum(
            case(
                (and_(Prestamo.estado == "APROBADO", Cliente.estado == "ACTIVO"), tf),
                else_=0,
            )
        ),
        0,
    )
    sum_inactivo = func.coalesce(
        func.sum(
            case(
                (and_(Prestamo.estado == "APROBADO", Cliente.estado == "INACTIVO"), tf),
                else_=0,
            )
        ),
        0,
    )
    sum_finalizado = func.coalesce(
        func.sum(case((Prestamo.estado == "LIQUIDADO", tf), else_=0)),
        0,
    )
    q = (
        select(
            sum_activo.label("tf_activo"),
            sum_inactivo.label("tf_inactivo"),
            sum_finalizado.label("tf_finalizado"),
            func.count(Prestamo.id),
        )
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
        .where(and_(*conds))
    )
    row = db.execute(q).one()
    ta = _safe_float(row.tf_activo)
    ti = _safe_float(row.tf_inactivo)
    tfi = _safe_float(row.tf_finalizado)
    total_tf = ta + ti + tfi
    n_prestamos = int(row[3] or 0)
    return {
        "total_financiamiento": round(total_tf, 2),
        "total_financiamiento_activo": round(ta, 2),
        "total_financiamiento_inactivo": round(ti, 2),
        "total_financiamiento_finalizado": round(tfi, 2),
        "total_prestamos": n_prestamos,
    }


@router.get("/dashboard")
def get_kpis_dashboard(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """KPIs planos de financiamiento (usado por DashboardFinanciamiento: /api/v1/kpis/dashboard)."""
    try:
        return _compute_kpis_dashboard_flat(
            db, fecha_inicio, fecha_fin, analista, concesionario, modelo
        )
    except Exception as e:
        logger.exception("Error en GET /kpis/dashboard: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "total_financiamiento": 0.0,
            "total_financiamiento_activo": 0.0,
            "total_financiamiento_inactivo": 0.0,
            "total_financiamiento_finalizado": 0.0,
            "total_prestamos": 0,
        }


'''
text = text.replace(marker, insert + marker, 1)
p.write_text(text, encoding="utf-8")
print("inserted")
