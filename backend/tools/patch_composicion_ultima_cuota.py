"""One-shot patch: replace _compute_composicion_morosidad in graficos.py."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "app" / "api" / "v1" / "endpoints" / "dashboard" / "graficos.py"
t = p.read_text(encoding="utf-8")
start = t.index("def _compute_composicion_morosidad(")
end = t.index("def _compute_cobranzas_semanales(")

new_fn = r'''def _compute_composicion_morosidad(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """
    Por prestamo: la ultima cuota de la tabla de amortizacion (mayor numero_cuota)
    define el estado del prestamo. Misma regla que `estado` en GET /prestamos/{id}/cuotas
    (America/Caracas): PAGADO, PAGO_ADELANTADO, PENDIENTE, PARCIAL, VENCIDO, MORA.

    Agrupacion del grafico: Pagado (PAGADO + PAGO_ADELANTADO), Pendiente, Pendiente parcial,
    Vencido, Mora (4 meses+).
    """
    try:
        mx = (
            select(Cuota.prestamo_id, func.max(Cuota.numero_cuota).label("max_n"))
            .group_by(Cuota.prestamo_id)
        ).subquery()

        c = aliased(Cuota, name="c")

        estado_expr = literal_column(
            "(" + SQL_PG_ESTADO_CUOTA_CASE_CORRELATED_TOTAL_PAGADO + ")"
        )

        conds_prestamo = [Prestamo.estado == "APROBADO"]
        if analista:
            conds_prestamo.append(Prestamo.analista == analista)
        if concesionario:
            conds_prestamo.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_prestamo.append(Prestamo.modelo_vehiculo == modelo)
        if fecha_inicio and fecha_fin:
            try:
                inicio = date.fromisoformat(fecha_inicio)
                fin = date.fromisoformat(fecha_fin)
                fref = prestamo_fecha_referencia_negocio()
                conds_prestamo.append(fref >= inicio)
                conds_prestamo.append(fref <= fin)
            except ValueError:
                pass

        q = (
            select(
                estado_expr.label("estado"),
                func.count().label("n"),
                func.coalesce(func.sum(c.monto), 0).label("monto"),
            )
            .select_from(c)
            .join(
                mx,
                and_(c.prestamo_id == mx.c.prestamo_id, c.numero_cuota == mx.c.max_n),
            )
            .join(Prestamo, c.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_prestamo))
            .group_by(estado_expr)
        )
        rows = db.execute(q).all()

        merged: dict[str, dict] = {}
        for estado, n, monto in rows:
            code = (estado or "").strip().upper()
            if code in ("PAGADO", "PAGO_ADELANTADO"):
                cat = "Pagado"
            elif code == "PENDIENTE":
                cat = "Pendiente"
            elif code == "PARCIAL":
                cat = "Pendiente parcial"
            elif code == "VENCIDO":
                cat = "Vencido"
            elif code == "MORA":
                cat = "Mora (4 meses+)"
            else:
                cat = code or "Otro"
            if cat not in merged:
                merged[cat] = {"n": 0, "m": 0.0}
            merged[cat]["n"] += int(n)
            merged[cat]["m"] += float(_safe_float(monto))

        orden = (
            "Pagado",
            "Pendiente",
            "Pendiente parcial",
            "Vencido",
            "Mora (4 meses+)",
        )
        puntos = []
        total_monto = 0.0
        total_cuotas = 0
        total_prestamos = 0
        for cat in orden:
            data = merged.get(cat, {"n": 0, "m": 0.0})
            n = int(data["n"])
            m = float(data["m"])
            total_prestamos += n
            total_monto += m
            total_cuotas += n
            puntos.append(
                {
                    "categoria": cat,
                    "monto": m,
                    "cantidad_cuotas": n,
                    "cantidad_prestamos": n,
                }
            )
        if merged.get("Otro", {}).get("n", 0):
            o = merged["Otro"]
            puntos.append(
                {
                    "categoria": "Otro",
                    "monto": float(o["m"]),
                    "cantidad_cuotas": int(o["n"]),
                    "cantidad_prestamos": int(o["n"]),
                }
            )
            total_prestamos += int(o["n"])
            total_monto += float(o["m"])
            total_cuotas += int(o["n"])

        return {
            "puntos": puntos,
            "total_morosidad": total_monto,
            "total_cuotas": total_cuotas,
            "total_prestamos": total_prestamos,
        }
    except Exception as e:
        logger.exception("Error en composicion-morosidad: %s", e)
        return {
            "puntos": [],
            "total_morosidad": 0.0,
            "total_cuotas": 0,
            "total_prestamos": 0,
        }


'''

p.write_text(t[:start] + new_fn + t[end:], encoding="utf-8")
print("patched", p)
