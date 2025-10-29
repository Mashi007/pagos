import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db

from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/admin")
def dashboard_administrador(
    periodo: Optional[str] = Query("mes", description="Periodo: dia, semana, mes, año"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dashboard para administradores con datos reales de la base de datos
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403, detail="Acceso denegado. Solo administradores."
            )

        hoy = date.today()

        # 1. CARTERA TOTAL - Suma de todos los préstamos activos
        cartera_total = db.query(func.sum(Prestamo.total_financiamiento)).filter(
            Prestamo.activo.is_(True)
        ).scalar() or Decimal("0")

        # 2. CARTERA VENCIDA - Monto de préstamos con cuotas vencidas (no pagadas)
        cartera_vencida = db.query(func.sum(Cuota.monto_cuota)).join(
            Prestamo, Cuota.prestamo_id == Prestamo.id
        ).filter(
            and_(
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != "PAGADO",
                Prestamo.activo.is_(True),
            )
        ).scalar() or Decimal(
            "0"
        )

        # 3. CARTERA AL DÍA - Cartera total menos cartera vencida
        cartera_al_dia = cartera_total - cartera_vencida

        # 4. PORCENTAJE DE MORA
        porcentaje_mora = (
            (float(cartera_vencida) / float(cartera_total) * 100)
            if cartera_total > 0
            else 0
        )

        # 5. PAGOS DE HOY
        pagos_hoy = (
            db.query(func.count(Pago.id))
            .filter(func.date(Pago.fecha_pago) == hoy)
            .scalar()
            or 0
        )

        monto_pagos_hoy = db.query(func.sum(Pago.monto_pagado)).filter(
            func.date(Pago.fecha_pago) == hoy
        ).scalar() or Decimal("0")

        # 6. CLIENTES ACTIVOS - Clientes con préstamos activos
        clientes_activos = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .filter(Prestamo.activo.is_(True))
            .scalar()
            or 0
        )

        # 7. CLIENTES EN MORA - Clientes con cuotas vencidas
        clientes_en_mora = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Cuota.fecha_vencimiento < hoy,
                    Cuota.estado != "PAGADO",
                    Prestamo.activo.is_(True),
                )
            )
            .scalar()
            or 0
        )

        # 8. PRÉSTAMOS ACTIVOS
        prestamos_activos = (
            db.query(func.count(Prestamo.id)).filter(Prestamo.activo.is_(True)).scalar()
            or 0
        )

        # 9. PRÉSTAMOS PAGADOS
        prestamos_pagados = (
            db.query(func.count(Prestamo.id))
            .filter(Prestamo.estado == "PAGADO")
            .scalar()
            or 0
        )

        # 10. PRÉSTAMOS VENCIDOS
        prestamos_vencidos = (
            db.query(func.count(func.distinct(Prestamo.id)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Cuota.fecha_vencimiento < hoy,
                    Cuota.estado != "PAGADO",
                    Prestamo.activo.is_(True),
                )
            )
            .scalar()
            or 0
        )

        # 11. TOTAL PAGADO (histórico)
        total_cobrado = db.query(func.sum(Pago.monto_pagado)).scalar() or Decimal("0")

        # 12. CUOTAS PAGADAS TOTALES
        cuotas_pagadas = (
            db.query(func.count(Cuota.id)).filter(Cuota.estado == "PAGADO").scalar()
            or 0
        )

        # 13. CUOTAS PENDIENTES
        cuotas_pendientes = (
            db.query(func.count(Cuota.id)).filter(Cuota.estado == "PENDIENTE").scalar()
            or 0
        )

        # 14. CUOTAS ATRASADAS
        cuotas_atrasadas = (
            db.query(func.count(Cuota.id))
            .filter(and_(Cuota.estado == "ATRASADO", Cuota.fecha_vencimiento < hoy))
            .scalar()
            or 0
        )

        return {
            "cartera_total": float(cartera_total),
            "cartera_anterior": 0,  # TODO: Calcular con período anterior
            "cartera_al_dia": float(cartera_al_dia),
            "cartera_vencida": float(cartera_vencida),
            "porcentaje_mora": round(porcentaje_mora, 2),
            "porcentaje_mora_anterior": 0,
            "pagos_hoy": pagos_hoy,
            "monto_pagos_hoy": float(monto_pagos_hoy),
            "clientes_activos": clientes_activos,
            "clientes_mora": clientes_en_mora,
            "clientes_anterior": 0,
            "meta_mensual": 500000,  # TODO: Configurable
            "avance_meta": float(total_cobrado),
            "financieros": {
                "totalCobrado": float(total_cobrado),
                "totalCobradoAnterior": 0,
                "ingresosCapital": 0,  # TODO: Calcular
                "ingresosInteres": 0,  # TODO: Calcular
                "ingresosMora": 0,  # TODO: Calcular
                "tasaRecuperacion": 0,  # TODO: Calcular
                "tasaRecuperacionAnterior": 0,
            },
            "cobranza": {
                "promedioDiasMora": 0,  # TODO: Calcular
                "promedioDiasMoraAnterior": 0,
                "porcentajeCumplimiento": 0,  # TODO: Calcular
                "porcentajeCumplimientoAnterior": 0,
                "clientesMora": clientes_en_mora,
            },
            "analistaes": {
                "totalAsesores": 0,  # TODO: Calcular
                "analistaesActivos": 0,
                "ventasMejorAsesor": 0,
                "montoMejorAsesor": 0,
                "promedioVentas": 0,
                "tasaConversion": 0,
                "tasaConversionAnterior": 0,
            },
            "productos": {
                "modeloMasVendido": "N/A",
                "ventasModeloMasVendido": 0,
                "ticketPromedio": 0,  # TODO: Calcular
                "ticketPromedioAnterior": 0,
                "totalModelos": 0,
                "modeloMenosVendido": "N/A",
            },
            "fecha_consulta": hoy.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error en dashboard admin: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/analista")
def dashboard_analista(
    fecha_inicio: Optional[date] = Query(None, description="Fecha de inicio"),
    fecha_fin: Optional[date] = Query(None, description="Fecha de fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # DASHBOARD ANALISTA - ACCESO LIMITADO
    # Acceso: Solo clientes asignados
    # Vista Dashboard:
    # - Gráfico de mora vs al día (solo sus clientes)
    # - Estadísticas de sus clientes

    hoy = date.today()

    # KPIs para clientes asignados al analista
    clientes_asignados = (
        db.query(Cliente)
        .filter(Cliente.activo, Cliente.analista_id == current_user.id)
        .all()
    )

    if not clientes_asignados:
        return {
            "kpis": {
                "cartera_total": 0,
                "clientes_al_dia": 0,
                "clientes_en_mora": 0,
                "porcentaje_mora": 0,
            },
            "evolucion_cartera": [],
            "top_clientes": [],
            "fecha_consulta": hoy.isoformat(),
        }

    cartera_total = sum(
        float(cliente.total_financiamiento or 0) for cliente in clientes_asignados
    )

    clientes_al_dia = len([c for c in clientes_asignados if (c.dias_mora or 0) == 0])
    clientes_en_mora = len([c for c in clientes_asignados if (c.dias_mora or 0) > 0])

    porcentaje_mora = (
        (clientes_en_mora / len(clientes_asignados) * 100) if clientes_asignados else 0
    )

    # Top 5 clientes con mayor financiamiento (del analista)
    top_clientes = sorted(
        clientes_asignados,
        key=lambda x: float(x.total_financiamiento or 0),
        reverse=True,
    )[:5]

    top_clientes_data = []
    for cliente in top_clientes:
        top_clientes_data.append(
            {
                "cedula": cliente.cedula,
                "nombre": cliente.nombre,
                "total_financiamiento": float(cliente.total_financiamiento or 0),
                "dias_mora": cliente.dias_mora or 0,
            }
        )

    return {
        "kpis": {
            "cartera_total": cartera_total,
            "clientes_al_dia": clientes_al_dia,
            "clientes_en_mora": clientes_en_mora,
            "porcentaje_mora": round(porcentaje_mora, 2),
        },
        "evolucion_cartera": [],
        "top_clientes": top_clientes_data,
        "fecha_consulta": hoy.isoformat(),
    }


@router.get("/resumen")
def resumen_general(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Resumen general del sistema
    try:
        # Estadísticas básicas
        total_clientes = db.query(Cliente).filter(Cliente.activo).count()
        total_prestamos = db.query(Prestamo).filter(Prestamo.activo).count()

        # Cartera total
        cartera_total = db.query(func.sum(Cliente.total_financiamiento)).filter(
            Cliente.activo, Cliente.total_financiamiento.isnot(None)
        ).scalar() or Decimal("0")

        # Clientes en mora
        clientes_mora = (
            db.query(Cliente).filter(Cliente.activo, Cliente.dias_mora > 0).count()
        )

        return {
            "total_clientes": total_clientes,
            "total_prestamos": total_prestamos,
            "cartera_total": float(cartera_total),
            "clientes_mora": clientes_mora,
            "fecha_consulta": date.today().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )
