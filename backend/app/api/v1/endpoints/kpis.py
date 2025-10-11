# backend/app/api/v1/endpoints/kpis.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from datetime import datetime, date, timedelta
from typing import Optional, List
from decimal import Decimal

from app.db.session import get_db
from app.models.prestamo import Prestamo, EstadoPrestamo
from app.models.pago import Pago
from app.models.cliente import Cliente
from app.schemas.kpis import (
    KPIDashboard,
    KPICartera,
    KPICobranza,
    KPIMorosidad,
    TendenciaMetrica
)

router = APIRouter()


@router.get("/dashboard", response_model=KPIDashboard)
def obtener_kpis_dashboard(
    db: Session = Depends(get_db)
):
    """
    Obtiene los KPIs principales para el dashboard.
    """
    hoy = date.today()
    mes_actual = hoy.month
    anio_actual = hoy.year
    
    # CARTERA
    cartera_total = db.query(
        func.sum(Prestamo.monto_total)
    ).filter(
        Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
    ).scalar() or Decimal('0')
    
    saldo_pendiente = db.query(
        func.sum(Prestamo.saldo_pendiente)
    ).filter(
        Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
    ).scalar() or Decimal('0')
    
    # PRÉSTAMOS ACTIVOS
    total_activos = db.query(Prestamo).filter(
        Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
    ).count()
    
    # MOROSIDAD
    total_mora = db.query(Prestamo).filter(
        Prestamo.estado == EstadoPrestamo.EN_MORA
    ).count()
    
    monto_mora = db.query(
        func.sum(Prestamo.saldo_pendiente)
    ).filter(
        Prestamo.estado == EstadoPrestamo.EN_MORA
    ).scalar() or Decimal('0')
    
    tasa_morosidad = (total_mora / total_activos * 100) if total_activos > 0 else 0
    
    # COBRANZA DEL MES
    primer_dia_mes = date(anio_actual, mes_actual, 1)
    recaudacion_mes = db.query(
        func.sum(Pago.monto)
    ).filter(
        Pago.fecha_pago >= primer_dia_mes,
        Pago.fecha_pago <= hoy
    ).scalar() or Decimal('0')
    
    # CLIENTES
    total_clientes = db.query(Cliente).count()
    clientes_activos = db.query(Cliente.id).join(Prestamo).filter(
        Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
    ).distinct().count()
    
    # NUEVOS PRÉSTAMOS DEL MES
    nuevos_prestamos = db.query(Prestamo).filter(
        extract('month', Prestamo.fecha_desembolso) == mes_actual,
        extract('year', Prestamo.fecha_desembolso) == anio_actual
    ).count()
    
    return KPIDashboard(
        cartera_total=cartera_total,
        saldo_pendiente=saldo_pendiente,
        total_prestamos_activos=total_activos,
        total_prestamos_mora=total_mora,
        monto_en_mora=monto_mora,
        tasa_morosidad=round(tasa_morosidad, 2),
        recaudacion_mes_actual=recaudacion_mes,
        total_clientes=total_clientes,
        clientes_activos=clientes_activos,
        nuevos_prestamos_mes=nuevos_prestamos
    )


@router.get("/cartera-evolucion")
def evolucion_cartera(
    meses: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db)
):
    """
    Obtiene la evolución de la cartera en los últimos N meses.
    """
    hoy = date.today()
    resultado = []
    
    for i in range(meses):
        fecha_mes = hoy - timedelta(days=30 * i)
        mes = fecha_mes.month
        anio = fecha_mes.year
        
        # Préstamos activos al final del mes
        ultimo_dia = 30  # Simplificado
        fecha_corte = date(anio, mes, ultimo_dia)
        
        cartera_mes = db.query(
            func.sum(Prestamo.monto_total)
        ).filter(
            Prestamo.fecha_desembolso <= fecha_corte,
            Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
        ).scalar() or Decimal('0')
        
        resultado.append({
            "mes": fecha_mes.strftime("%b %Y"),
            "cartera": float(cartera_mes)
        })
    
    return list(reversed(resultado))


@router.get("/cobranza-efectividad")
def efectividad_cobranza(
    meses: int = Query(3, ge=1, le=12),
    db: Session = Depends(get_db)
):
    """
    Calcula la efectividad de cobranza por mes.
    """
    hoy = date.today()
    resultado = []
    
    for i in range(meses):
        fecha_mes = hoy - timedelta(days=30 * i)
        mes = fecha_mes.month
        anio = fecha_mes.year
        
        # Monto esperado (cuotas del mes)
        primer_dia = date(anio, mes, 1)
        ultimo_dia = date(anio, mes, 30)  # Simplificado
        
        # Monto recaudado
        recaudado = db.query(
            func.sum(Pago.monto)
        ).filter(
            Pago.fecha_pago >= primer_dia,
            Pago.fecha_pago <= ultimo_dia
        ).scalar() or Decimal('0')
        
        # Monto esperado (estimación basada en préstamos activos)
        esperado = db.query(
            func.sum(Prestamo.cuota)
        ).filter(
            Prestamo.fecha_desembolso <= ultimo_dia,
            Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
        ).scalar() or Decimal('0')
        
        efectividad = (float(recaudado) / float(esperado) * 100) if esperado > 0 else 0
        
        resultado.append({
            "mes": fecha_mes.strftime("%b %Y"),
            "recaudado": float(recaudado),
            "esperado": float(esperado),
            "efectividad": round(efectividad, 2)
        })
    
    return list(reversed(resultado))


@router.get("/morosidad-tendencia")
def tendencia_morosidad(
    meses: int = Query(6, ge=1, le=12),
    db: Session = Depends(get_db)
):
    """
    Muestra la tendencia de morosidad.
    """
    hoy = date.today()
    resultado = []
    
    for i in range(meses):
        fecha_mes = hoy - timedelta(days=30 * i)
        
        # Simular cálculo de morosidad al final del mes
        total_activos = db.query(Prestamo).filter(
            Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
        ).count()
        
        total_mora = db.query(Prestamo).filter(
            Prestamo.estado == EstadoPrestamo.EN_MORA
        ).count()
        
        tasa_morosidad = (total_mora / total_activos * 100) if total_activos > 0 else 0
        
        resultado.append({
            "mes": fecha_mes.strftime("%b %Y"),
            "tasa_morosidad": round(tasa_morosidad, 2),
            "cantidad_mora": total_mora
        })
    
    return list(reversed(resultado))


@router.get("/distribucion-cartera")
def distribucion_cartera(
    db: Session = Depends(get_db)
):
    """
    Muestra la distribución de la cartera por rangos de monto.
    """
    resultado = db.query(
        func.case(
            (Prestamo.monto_total <= 1000, 'Hasta $1,000'),
            (Prestamo.monto_total <= 5000, '$1,001 - $5,000'),
            (Prestamo.monto_total <= 10000, '$5,001 - $10,000'),
            (Prestamo.monto_total <= 20000, '$10,001 - $20,000'),
            else_='Más de $20,000'
        ).label('rango'),
        func.count(Prestamo.id).label('cantidad'),
        func.sum(Prestamo.monto_total).label('monto_total'),
        func.sum(Prestamo.saldo_pendiente).label('saldo_pendiente')
    ).filter(
        Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
    ).group_by('rango').all()
    
    return [
        {
            "rango": r[0],
            "cantidad": r[1],
            "monto_total": float(r[2]),
            "saldo_pendiente": float(r[3])
        }
        for r in resultado
    ]


@router.get("/top-clientes")
def top_clientes_kpi(
    limite: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Top clientes por saldo pendiente.
    """
    resultado = db.query(
        Cliente,
        func.count(Prestamo.id).label('total_prestamos'),
        func.sum(Prestamo.saldo_pendiente).label('saldo_total')
    ).join(Prestamo).filter(
        Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
    ).group_by(Cliente.id).order_by(
        func.sum(Prestamo.saldo_pendiente).desc()
    ).limit(limite).all()
    
    return [
        {
            "cliente_id": r[0].id,
            "nombre": f"{r[0].nombres} {r[0].apellidos}",
            "total_prestamos": r[1],
            "saldo_pendiente": float(r[2])
        }
        for r in resultado
    ]


@router.get("/metricas-periodo")
def metricas_periodo(
    fecha_inicio: date,
    fecha_fin: date,
    db: Session = Depends(get_db)
):
    """
    Métricas consolidadas de un período específico.
    """
    # Préstamos desembolsados
    prestamos_periodo = db.query(Prestamo).filter(
        Prestamo.fecha_desembolso >= fecha_inicio,
        Prestamo.fecha_desembolso <= fecha_fin
    ).all()
    
    total_desembolsado = sum(p.monto_total for p in prestamos_periodo)
    cantidad_prestamos = len(prestamos_periodo)
    
    # Recaudación
    pagos_periodo = db.query(Pago).filter(
        Pago.fecha_pago >= fecha_inicio,
        Pago.fecha_pago <= fecha_fin
    ).all()
    
    total_recaudado = sum(p.monto for p in pagos_periodo)
    cantidad_pagos = len(pagos_periodo)
    
    # Clientes nuevos
    clientes_nuevos = db.query(Cliente).filter(
        Cliente.created_at >= fecha_inicio,
        Cliente.created_at <= fecha_fin
    ).count()
    
    return {
        "periodo": {
            "inicio": fecha_inicio,
            "fin": fecha_fin
        },
        "desembolsos": {
            "total": float(total_desembolsado),
            "cantidad": cantidad_prestamos,
            "promedio": float(total_desembolsado / cantidad_prestamos) if cantidad_prestamos > 0 else 0
        },
        "recaudacion": {
            "total": float(total_recaudado),
            "cantidad": cantidad_pagos,
            "promedio": float(total_recaudado / cantidad_pagos) if cantidad_pagos > 0 else 0
        },
        "clientes_nuevos": clientes_nuevos
    }


@router.get("/alerta-morosidad")
def alertas_morosidad(
    db: Session = Depends(get_db)
):
    """
    Genera alertas de préstamos con alta morosidad.
    """
    # Préstamos con más de 30 días de mora
    alertas_criticas = db.query(Prestamo).filter(
        Prestamo.estado == EstadoPrestamo.EN_MORA,
        Prestamo.dias_mora > 30
    ).all()
    
    # Préstamos próximos a vencer sin pago
    hoy = date.today()
    proximos_vencer = db.query(Prestamo).filter(
        Prestamo.estado == EstadoPrestamo.ACTIVO,
        Prestamo.fecha_vencimiento <= hoy + timedelta(days=7)
    ).all()
    
    return {
        "criticas": [
            {
                "prestamo_id": p.id,
                "cliente": f"{p.cliente.nombres} {p.cliente.apellidos}",
                "dias_mora": p.dias_mora,
                "saldo_pendiente": float(p.saldo_pendiente)
            }
            for p in alertas_criticas
        ],
        "proximos_vencer": [
            {
                "prestamo_id": p.id,
                "cliente": f"{p.cliente.nombres} {p.cliente.apellidos}",
                "fecha_vencimiento": p.fecha_vencimiento,
                "saldo_pendiente": float(p.saldo_pendiente)
            }
            for p in proximos_vencer
        ]
    }
