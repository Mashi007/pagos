# backend/app/api/v1/endpoints/kpis.py
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.analista import Analista
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard")
def dashboard_kpis_principales(
    fecha_corte: Optional[date] = Query(None, description="Fecha de corte (default: hoy)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    KPIs principales para el dashboard

    📊 KPIs mostrados:
    - 💰 Cartera Total
    - ✅ Clientes al Día
    - ⚠️ Clientes en Mora
    - 📈 Tasa de Morosidad
    - 💸 Cobrado Hoy
    - 📅 Vencimientos Hoy
    """
    if not fecha_corte:
        fecha_corte = date.today()

    # 💰 CARTERA TOTAL
    cartera_total = db.query(func.sum(Cliente.total_financiamiento)).filter(
        Cliente.activo, Cliente.total_financiamiento.isnot(None)
    ).scalar() or Decimal("0")

    # ✅ CLIENTES AL DÍA
    clientes_al_dia = (
        db.query(Cliente)
        .filter(
            Cliente.activo,
            or_(Cliente.estado_financiero == "AL_DIA", Cliente.dias_mora == 0),
        )
        .count()
    )

    # ⚠️ CLIENTES EN MORA
    clientes_en_mora = (
        db.query(Cliente).filter(Cliente.activo, Cliente.estado_financiero == "MORA", Cliente.dias_mora > 0).count()
    )

    # 📈 TASA DE MOROSIDAD
    total_clientes = clientes_al_dia + clientes_en_mora
    tasa_morosidad = (clientes_en_mora / total_clientes * 100) if total_clientes > 0 else 0

    # 💸 COBRADO HOY
    cobrado_hoy = db.query(func.sum(Pago.monto_pagado)).filter(
        Pago.fecha_pago == fecha_corte, Pago.estado != "ANULADO"
    ).scalar() or Decimal("0")

    # 📅 VENCIMIENTOS HOY
    vencimientos_hoy = (
        db.query(Cuota)
        .filter(
            Cuota.fecha_vencimiento == fecha_corte,
            Cuota.estado.in_(["PENDIENTE", "PARCIAL"]),
        )
        .count()
    )

    return {
        "fecha_corte": fecha_corte,
        "kpis_principales": {
            "cartera_total": {
                "valor": float(cartera_total),
                "formato": f"${float(cartera_total):,.0f}",
                "icono": "💰",
                "color": "primary",
            },
            "clientes_al_dia": {
                "valor": clientes_al_dia,
                "formato": f"{clientes_al_dia:,}",
                "icono": "✅",
                "color": "success",
            },
            "clientes_en_mora": {
                "valor": clientes_en_mora,
                "formato": f"{clientes_en_mora:,}",
                "icono": "⚠️",
                "color": "warning",
            },
            "tasa_morosidad": {
                "valor": round(tasa_morosidad, 2),
                "formato": f"{tasa_morosidad:.2f}%",
                "icono": "📈",
                "color": "danger" if tasa_morosidad > 10 else "warning",
            },
            "cobrado_hoy": {
                "valor": float(cobrado_hoy),
                "formato": f"${float(cobrado_hoy):,.0f}",
                "icono": "💸",
                "color": "success",
            },
            "vencimientos_hoy": {
                "valor": vencimientos_hoy,
                "formato": f"{vencimientos_hoy:,}",
                "icono": "📅",
                "color": "info",
            },
        },
        "resumen": {
            "total_clientes": total_clientes,
            "porcentaje_al_dia": (round((clientes_al_dia / total_clientes * 100), 2) if total_clientes > 0 else 0),
            "porcentaje_mora": round(tasa_morosidad, 2),
        },
    }


@router.get("/financieros")
def kpis_financieros(
    periodo: str = Query("mes", description="dia, semana, mes, año"),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📈 KPIs Financieros
    - Cartera total
    - Total cobrado por período
    - Proyección de flujo de caja
    - Ingresos por período
    - Tasa de recuperación
    - Rentabilidad por modalidad
    """
    # Calcular fechas según período
    hoy = date.today()

    if not fecha_inicio or not fecha_fin:
        if periodo == "dia":
            fecha_inicio = fecha_fin = hoy
        elif periodo == "semana":
            fecha_inicio = hoy - timedelta(days=hoy.weekday())
            fecha_fin = fecha_inicio + timedelta(days=6)
        elif periodo == "mes":
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = (fecha_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        elif periodo == "año":
            fecha_inicio = hoy.replace(month=1, day=1)
            fecha_fin = hoy.replace(month=12, day=31)

    # Cartera total (saldos pendientes)
    cartera_total = db.query(func.sum(Cliente.total_financiamiento - Cliente.cuota_inicial)).filter(
        Cliente.activo, Cliente.total_financiamiento.isnot(None)
    ).scalar() or Decimal("0")

    # Total cobrado en el período
    total_cobrado = db.query(func.sum(Pago.monto_pagado)).filter(
        Pago.fecha_pago >= fecha_inicio,
        Pago.fecha_pago <= fecha_fin,
        Pago.estado != "ANULADO",
    ).scalar() or Decimal("0")

    # Proyección próximos 30 días
    fecha_proyeccion = hoy + timedelta(days=30)
    flujo_proyectado = db.query(func.sum(Cuota.monto_cuota)).filter(
        Cuota.fecha_vencimiento >= hoy,
        Cuota.fecha_vencimiento <= fecha_proyeccion,
        Cuota.estado.in_(["PENDIENTE", "PARCIAL"]),
    ).scalar() or Decimal("0")

    # Ingresos por período (capital + interés + mora)
    ingresos_capital = db.query(func.sum(Pago.monto_capital)).filter(
        Pago.fecha_pago >= fecha_inicio, Pago.fecha_pago <= fecha_fin
    ).scalar() or Decimal("0")

    ingresos_interes = db.query(func.sum(Pago.monto_interes)).filter(
        Pago.fecha_pago >= fecha_inicio, Pago.fecha_pago <= fecha_fin
    ).scalar() or Decimal("0")

    ingresos_mora = db.query(func.sum(Pago.monto_mora)).filter(
        Pago.fecha_pago >= fecha_inicio, Pago.fecha_pago <= fecha_fin
    ).scalar() or Decimal("0")

    # Tasa de recuperación
    total_vencido = db.query(func.sum(Cuota.monto_cuota)).filter(
        Cuota.fecha_vencimiento <= hoy,
        Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]),
    ).scalar() or Decimal("0")

    tasa_recuperacion = (total_cobrado / total_vencido * 100) if total_vencido > 0 else 100

    # Rentabilidad por modalidad
    rentabilidad_modalidad = (
        db.query(
            Cliente.modalidad_pago,
            func.count(Cliente.id).label("clientes"),
            func.sum(Cliente.total_financiamiento).label("monto_total"),
            func.avg(Cliente.total_financiamiento).label("ticket_promedio"),
        )
        .filter(Cliente.activo, Cliente.modalidad_pago.isnot(None))
        .group_by(Cliente.modalidad_pago)
        .all()
    )

    return {
        "periodo": {
            "tipo": periodo,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
        },
        "kpis_financieros": {
            "cartera_total": float(cartera_total),
            "total_cobrado_periodo": float(total_cobrado),
            "proyeccion_30_dias": float(flujo_proyectado),
            "ingresos_detalle": {
                "capital": float(ingresos_capital),
                "interes": float(ingresos_interes),
                "mora": float(ingresos_mora),
                "total": float(ingresos_capital + ingresos_interes + ingresos_mora),
            },
            "tasa_recuperacion": round(float(tasa_recuperacion), 2),
            "rentabilidad_por_modalidad": [
                {
                    "modalidad": modalidad,
                    "clientes": clientes,
                    "monto_total": float(monto),
                    "ticket_promedio": float(ticket),
                }
                for modalidad, clientes, monto, ticket in rentabilidad_modalidad
            ],
        },
    }


@router.get("/cobranza")
def kpis_cobranza(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    👥 KPIs de Cobranza
    - Tasa de morosidad general
    - Tasa de morosidad por analista
    - Promedio de días de retraso
    - Porcentaje de cumplimiento
    - Top 10 clientes morosos
    - Evolución mensual
    """
    # Tasa de morosidad general
    total_clientes = db.query(Cliente).filter(Cliente.activo).count()
    clientes_mora = db.query(Cliente).filter(Cliente.activo, Cliente.dias_mora > 0).count()

    clientes_al_dia = db.query(Cliente).filter(Cliente.activo, Cliente.dias_mora == 0).count()

    tasa_morosidad_general = (clientes_mora / total_clientes * 100) if total_clientes > 0 else 0

    # Tasa de morosidad por analista
    morosidad_por_analista = (
        db.query(
            User.full_name,
            func.count(Cliente.id).label("total_clientes"),
            func.sum(case((Cliente.dias_mora > 0, 1), else_=0)).label("clientes_mora"),
        )
        .outerjoin(Cliente, Analista.id == Cliente.analista_id)
        .filter(Analista.activo, Cliente.activo)
        .group_by(User.id, User.full_name)
        .all()
    )

    # Promedio de días de retraso
    promedio_dias_mora = db.query(func.avg(Cliente.dias_mora)).filter(Cliente.activo, Cliente.dias_mora > 0).scalar() or 0

    # Porcentaje de cumplimiento de pagos (cuotas pagadas a tiempo)
    cuotas_vencidas = db.query(Cuota).filter(Cuota.fecha_vencimiento <= date.today()).count()

    cuotas_pagadas_tiempo = (
        db.query(Cuota).filter(Cuota.estado == "PAGADA", Cuota.fecha_pago <= Cuota.fecha_vencimiento).count()
    )

    porcentaje_cumplimiento = (cuotas_pagadas_tiempo / cuotas_vencidas * 100) if cuotas_vencidas > 0 else 0

    # Top 10 clientes morosos
    top_morosos = (
        db.query(
            Cliente.id,
            Cliente.nombres,
            Cliente.apellidos,
            Cliente.cedula,
            Cliente.dias_mora,
            Cliente.total_financiamiento,
        )
        .filter(Cliente.activo, Cliente.dias_mora > 0)
        .order_by(Cliente.dias_mora.desc())
        .limit(10)
        .all()
    )

    # Evolución mensual de mora (últimos 6 meses)
    evolucion_mensual = []
    for i in range(6):
        mes_fecha = date.today().replace(day=1) - timedelta(days=30 * i)
        # Simulación - en implementación real calcularías histórico
        evolucion_mensual.append(
            {
                "mes": mes_fecha.strftime("%Y-%m"),
                "tasa_morosidad": round(tasa_morosidad_general - (i * 0.5), 2),
                "clientes_mora": max(0, clientes_mora - (i * 10)),
            }
        )

    return {
        "kpis_cobranza": {
            "tasa_morosidad_general": round(tasa_morosidad_general, 2),
            "promedio_dias_retraso": round(float(promedio_dias_mora), 1),
            "porcentaje_cumplimiento": round(porcentaje_cumplimiento, 2),
            "clientes_al_dia_vs_mora": {
                "al_dia": clientes_al_dia,
                "en_mora": clientes_mora,
                "total": total_clientes,
            },
        },
        "morosidad_por_analista": [
            {
                "analista": analista,
                "total_clientes": total,
                "clientes_mora": mora,
                "tasa_morosidad": round((mora / total * 100), 2) if total > 0 else 0,
            }
            for analista, total, mora in morosidad_por_analista
        ],
        "top_clientes_morosos": [
            {
                "id": cliente_id,
                "nombre": f"{nombres} {apellidos}",
                "cedula": cedula,
                "dias_mora": dias_mora,
                "monto_financiamiento": float(monto or 0),
            }
            for cliente_id, nombres, apellidos, cedula, dias_mora, monto in top_morosos
        ],
        "evolucion_mensual": evolucion_mensual,
    }


@router.get("/analistaes")
def kpis_analistaes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    🏆 KPIs de Analistaes
    - Ranking de ventas
    - Gestión de cobranza
    - Comparativa entre analistaes
    """
    # Ranking de ventas
    ventas_por_analista = (
        db.query(
            User.id,
            User.full_name,
            func.count(Cliente.id).label("total_ventas"),
            func.sum(Cliente.total_financiamiento).label("monto_vendido"),
            func.avg(Cliente.total_financiamiento).label("ticket_promedio"),
        )
        .outerjoin(Cliente, Analista.id == Cliente.analista_id)
        .filter(Analista.activo, Cliente.activo)
        .group_by(User.id, User.full_name)
        .order_by(func.sum(Cliente.total_financiamiento).desc())
        .all()
    )

    # Gestión de cobranza por analista
    cobranza_por_analista = (
        db.query(
            User.id,
            User.full_name,
            func.count(Cliente.id).label("total_clientes"),
            func.sum(case((Cliente.dias_mora == 0, 1), else_=0)).label("clientes_al_dia"),
            func.sum(case((Cliente.dias_mora > 0, 1), else_=0)).label("clientes_mora"),
        )
        .outerjoin(Cliente, Analista.id == Cliente.analista_id)
        .filter(Analista.activo, Cliente.activo)
        .group_by(User.id, User.full_name)
        .all()
    )

    # Procesar datos para ranking
    ranking_ventas = []
    ranking_cobranza = []

    for analista_id, nombre, ventas, monto, ticket in ventas_por_analista:
        ranking_ventas.append(
            {
                "analista_id": analista_id,
                "nombre": nombre,
                "total_ventas": ventas or 0,
                "monto_vendido": float(monto or 0),
                "ticket_promedio": float(ticket or 0),
            }
        )

    for analista_id, nombre, total, al_dia, mora in cobranza_por_analista:
        tasa_cobro = (al_dia / total * 100) if total > 0 else 0
        ranking_cobranza.append(
            {
                "analista_id": analista_id,
                "nombre": nombre,
                "total_clientes": total or 0,
                "clientes_al_dia": al_dia or 0,
                "clientes_mora": mora or 0,
                "tasa_cobro": round(tasa_cobro, 2),
            }
        )

    # Identificar mejores y peores
    mejor_vendedor = max(ranking_ventas, key=lambda x: x["total_ventas"]) if ranking_ventas else None
    mayor_monto = max(ranking_ventas, key=lambda x: x["monto_vendido"]) if ranking_ventas else None
    menor_ventas = min(ranking_ventas, key=lambda x: x["total_ventas"]) if ranking_ventas else None

    mejor_cobrador = max(ranking_cobranza, key=lambda x: x["tasa_cobro"]) if ranking_cobranza else None
    peor_cobrador = min(ranking_cobranza, key=lambda x: x["tasa_cobro"]) if ranking_cobranza else None

    return {
        "ranking_ventas": {
            "mejor_vendedor_unidades": mejor_vendedor,
            "mayor_monto_vendido": mayor_monto,
            "menor_ventas": menor_ventas,
            "todos_analistaes": ranking_ventas,
        },
        "gestion_cobranza": {
            "mejor_cobrador": mejor_cobrador,
            "peor_cobrador": peor_cobrador,
            "todos_analistaes": ranking_cobranza,
        },
        "comparativa": {
            "total_analistaes": len(ranking_ventas),
            "promedio_ventas": (sum(r["total_ventas"] for r in ranking_ventas) / len(ranking_ventas) if ranking_ventas else 0),
            "promedio_tasa_cobro": (
                sum(r["tasa_cobro"] for r in ranking_cobranza) / len(ranking_cobranza) if ranking_cobranza else 0
            ),
        },
    }


@router.get("/productos")
def kpis_productos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    🏍️ KPIs de Producto
    - Modelo más/menos vendido
    - Ventas por modelo
    - Ticket promedio por modelo
    - Mora por modelo
    """
    # Ventas por modelo
    ventas_por_modelo = (
        db.query(
            Cliente.modelo_vehiculo,
            Cliente.marca_vehiculo,
            func.count(Cliente.id).label("total_ventas"),
            func.sum(Cliente.total_financiamiento).label("monto_total"),
            func.avg(Cliente.total_financiamiento).label("ticket_promedio"),
        )
        .filter(Cliente.activo, Cliente.modelo_vehiculo.isnot(None))
        .group_by(Cliente.modelo_vehiculo, Cliente.marca_vehiculo)
        .all()
    )

    # Mora por modelo
    mora_por_modelo = (
        db.query(
            Cliente.modelo_vehiculo,
            func.count(Cliente.id).label("total_clientes"),
            func.sum(case((Cliente.dias_mora > 0, 1), else_=0)).label("clientes_mora"),
        )
        .filter(Cliente.activo, Cliente.modelo_vehiculo.isnot(None))
        .group_by(Cliente.modelo_vehiculo)
        .all()
    )

    # Procesar datos
    modelos_data = []
    for modelo, marca, ventas, monto, ticket in ventas_por_modelo:
        # Buscar datos de mora para este modelo
        mora_data = next((m for m in mora_por_modelo if m[0] == modelo), (modelo, 0, 0))

        tasa_mora_modelo = (mora_data[2] / mora_data[1] * 100) if mora_data[1] > 0 else 0

        modelos_data.append(
            {
                "modelo": modelo,
                "marca": marca,
                "total_ventas": ventas,
                "monto_total": float(monto),
                "ticket_promedio": float(ticket),
                "clientes_mora": mora_data[2],
                "tasa_mora": round(tasa_mora_modelo, 2),
            }
        )

    # Identificar extremos
    modelo_mas_vendido = max(modelos_data, key=lambda x: x["total_ventas"]) if modelos_data else None
    modelo_menos_vendido = min(modelos_data, key=lambda x: x["total_ventas"]) if modelos_data else None

    return {
        "modelo_mas_vendido": modelo_mas_vendido,
        "modelo_menos_vendido": modelo_menos_vendido,
        "ventas_por_modelo": modelos_data,
        "grafico_barras": {
            "labels": [f"{m['marca']} {m['modelo']}" for m in modelos_data],
            "ventas": [m["total_ventas"] for m in modelos_data],
            "montos": [m["monto_total"] for m in modelos_data],
        },
        "estadisticas": {
            "total_modelos": len(modelos_data),
            "ticket_promedio_general": (
                sum(m["ticket_promedio"] for m in modelos_data) / len(modelos_data) if modelos_data else 0
            ),
        },
    }


@router.get("/concesionarios")
def kpis_concesionarios(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    🏢 KPIs de Concesionario
    - Ventas por concesionario
    - Mora por concesionario
    - Comparativa entre concesionarios
    """
    # Ventas por concesionario
    ventas_por_concesionario = (
        db.query(
            Cliente.concesionario,
            func.count(Cliente.id).label("total_ventas"),
            func.sum(Cliente.total_financiamiento).label("monto_total"),
            func.avg(Cliente.total_financiamiento).label("ticket_promedio"),
        )
        .filter(Cliente.activo, Cliente.concesionario.isnot(None))
        .group_by(Cliente.concesionario)
        .all()
    )

    # Mora por concesionario
    mora_por_concesionario = (
        db.query(
            Cliente.concesionario,
            func.count(Cliente.id).label("total_clientes"),
            func.sum(case((Cliente.dias_mora > 0, 1), else_=0)).label("clientes_mora"),
            func.avg(Cliente.dias_mora).label("promedio_dias_mora"),
        )
        .filter(Cliente.activo, Cliente.concesionario.isnot(None))
        .group_by(Cliente.concesionario)
        .all()
    )

    # Combinar datos
    concesionarios_data = []
    for concesionario, ventas, monto, ticket in ventas_por_concesionario:
        # Buscar datos de mora
        mora_data = next(
            (m for m in mora_por_concesionario if m[0] == concesionario),
            (concesionario, 0, 0, 0),
        )

        tasa_mora = (mora_data[2] / mora_data[1] * 100) if mora_data[1] > 0 else 0

        concesionarios_data.append(
            {
                "concesionario": concesionario,
                "total_ventas": ventas,
                "monto_total": float(monto),
                "ticket_promedio": float(ticket),
                "clientes_mora": mora_data[2],
                "tasa_mora": round(tasa_mora, 2),
                "promedio_dias_mora": round(float(mora_data[3] or 0), 1),
            }
        )

    # Ordenar por monto total
    concesionarios_data.sort(key=lambda x: x["monto_total"], reverse=True)

    return {
        "ventas_por_concesionario": concesionarios_data,
        "comparativa": {
            "mejor_concesionario": (concesionarios_data[0] if concesionarios_data else None),
            "peor_tasa_mora": (min(concesionarios_data, key=lambda x: x["tasa_mora"]) if concesionarios_data else None),
            "mayor_volumen": (max(concesionarios_data, key=lambda x: x["monto_total"]) if concesionarios_data else None),
        },
        "estadisticas_generales": {
            "total_concesionarios": len(concesionarios_data),
            "ticket_promedio_general": (
                sum(c["ticket_promedio"] for c in concesionarios_data) / len(concesionarios_data) if concesionarios_data else 0
            ),
            "tasa_mora_promedio": (
                sum(c["tasa_mora"] for c in concesionarios_data) / len(concesionarios_data) if concesionarios_data else 0
            ),
        },
    }
