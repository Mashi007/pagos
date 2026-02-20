"""
Endpoints y lógica de cobranzas (reportes de cuotas vencidas, clientes atrasados).
Usado por el scheduler a las 1:00 y 13:00 para actualizar resumen de reportes.
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cuota import Cuota
from app.models.prestamo import Prestamo


def ejecutar_actualizacion_reportes(db: Session) -> dict:
    """
    Actualiza resumen de cobranzas: cuotas vencidas, monto adeudado, clientes atrasados.
    Usado por el scheduler a las 1:00 y 13:00. Datos reales desde BD.
    """
    hoy = date.today()
    # Cuotas impagas con vencimiento <= hoy
    q_resumen = (
        select(
            func.count(Cuota.id).label("total_cuotas_vencidas"),
            func.coalesce(func.sum(Cuota.monto), 0).label("monto_total_adeudado"),
            func.count(func.distinct(Prestamo.cliente_id)).label("clientes_atrasados"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento <= hoy,
            Prestamo.estado == "APROBADO",
        )
    )
    row = db.execute(q_resumen).fetchone()
    return {
        "total_cuotas_vencidas": int(row.total_cuotas_vencidas or 0),
        "monto_total_adeudado": float(row.monto_total_adeudado or 0),
        "clientes_atrasados": int(row.clientes_atrasados or 0),
    }
