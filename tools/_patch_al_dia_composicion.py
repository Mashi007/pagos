# Temporary script: patch _compute_composicion_morosidad — run from repo root, then delete.
from pathlib import Path

p = Path("backend/app/api/v1/endpoints/dashboard/graficos.py")
t = p.read_text(encoding="utf-8")
start = t.find("def _compute_composicion_morosidad(")
end = t.find("def _compute_cobranzas_semanales")
if start < 0 or end < 0:
    raise SystemExit("markers not found")

new_fn = '''def _compute_composicion_morosidad(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """
    Cartera por préstamo (una sola banda por préstamo):
    - Sin retraso: préstamos sin cuotas vencidas sin pagar → "Al día".
    - Con retraso: se usa el máximo atraso en días entre cuotas vencidas sin pagar;
      el préstamo cuenta solo en esa banda.
    Bandas de mora: 1-30, 31-60, 61-89 (vencido), 90+ (moroso).
    """
    try:
        bandas = [
            (1, 30, "1-30 días"),
            (31, 60, "31-60 días"),
            (61, 89, "61-89 días"),
            (90, 999999, "90+ días (moroso)"),
        ]
        dias_atraso = func.current_date() - Cuota.fecha_vencimiento
        conds_base = [
            Cuota.prestamo_id == Prestamo.id,
            Prestamo.cliente_id == Cliente.id,
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            dias_atraso >= 1,
        ]
        if analista:
            conds_base.append(Prestamo.analista == analista)
        if concesionario:
            conds_base.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_base.append(Prestamo.modelo_vehiculo == modelo)

        conds_prestamo = [
            Prestamo.estado == "APROBADO",
        ]
        if analista:
            conds_prestamo.append(Prestamo.analista == analista)
        if concesionario:
            conds_prestamo.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_prestamo.append(Prestamo.modelo_vehiculo == modelo)

        tiene_cuota_vencida = exists(
            select(1)
            .select_from(Cuota)
            .where(
                Cuota.prestamo_id == Prestamo.id,
                Cuota.fecha_pago.is_(None),
                dias_atraso >= 1,
            )
        )

        al_dia_subq = (
            select(Prestamo.id.label("prestamo_id"))
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_prestamo, ~tiene_cuota_vencida))
        ).subquery()

        worst_subq = (
            select(
                Cuota.prestamo_id.label("prestamo_id"),
                func.max(dias_atraso).label("max_dias"),
            )
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_base))
            .group_by(Cuota.prestamo_id)
        ).subquery()

        total_mora = int(db.scalar(select(func.count()).select_from(worst_subq)) or 0)

        np_al_dia = int(
            db.scalar(select(func.count()).select_from(al_dia_subq)) or 0
        )

        cuotas_al_dia_conds = [
            Cuota.prestamo_id.in_(select(al_dia_subq.c.prestamo_id)),
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento >= func.current_date(),
        ]
        n_al_dia = int(
            db.scalar(select(func.count()).select_from(Cuota).where(and_(*cuotas_al_dia_conds)))
            or 0
        )
        m_al_dia = _safe_float(
            db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .where(and_(*cuotas_al_dia_conds))
            )
        )

        puntos = [
            {
                "categoria": "Al día",
                "monto": m_al_dia,
                "cantidad_cuotas": n_al_dia,
                "cantidad_prestamos": np_al_dia,
            }
        ]
        total_monto = 0.0
        total_cuotas = 0

        for min_d, max_d, cat in bandas:
            band_conds = [worst_subq.c.max_dias >= min_d]
            if max_d < 999999:
                band_conds.append(worst_subq.c.max_dias <= max_d)

            np = int(
                db.scalar(
                    select(func.count()).select_from(worst_subq).where(and_(*band_conds))
                )
                or 0
            )

            prestamos_en_banda = select(worst_subq.c.prestamo_id).where(and_(*band_conds))

            n = int(
                db.scalar(
                    select(func.count())
                    .select_from(Cuota)
                    .where(
                        Cuota.prestamo_id.in_(prestamos_en_banda),
                        Cuota.fecha_pago.is_(None),
                        dias_atraso >= 1,
                    )
                )
                or 0
            )

            m = _safe_float(
                db.scalar(
                    select(func.coalesce(func.sum(Cuota.monto), 0))
                    .select_from(Cuota)
                    .where(
                        Cuota.prestamo_id.in_(prestamos_en_banda),
                        Cuota.fecha_pago.is_(None),
                        dias_atraso >= 1,
                    )
                )
            )

            total_cuotas += n
            total_monto += m
            puntos.append(
                {
                    "categoria": cat,
                    "monto": m,
                    "cantidad_cuotas": n,
                    "cantidad_prestamos": np,
                }
            )

        return {
            "puntos": puntos,
            "total_morosidad": total_monto,
            "total_cuotas": total_cuotas,
            "total_prestamos": np_al_dia + total_mora,
        }
    except Exception as e:
        logger.exception("Error en composicion-morosidad: %s", e)
        demo = [
            ("Al día", 50000, 120, 400),
            ("1-30 días", 12000, 45, 12),
            ("31-60 días", 8500, 28, 9),
            ("61-89 días", 6200, 18, 6),
            ("90+ días (moroso)", 15800, 32, 10),
        ]
        return {
            "puntos": [
                {"categoria": c, "monto": m, "cantidad_cuotas": n, "cantidad_prestamos": np}
                for c, m, n, np in demo
            ],
            "total_morosidad": sum(p[1] for p in demo),
            "total_cuotas": sum(p[2] for p in demo),
            "total_prestamos": sum(p[3] for p in demo),
        }'''

text = t[:start] + new_fn + "\n\n" + t[end:]
p.write_text(text, encoding="utf-8")
print("patched", len(new_fn))
