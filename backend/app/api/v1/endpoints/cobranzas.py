"""
Endpoints para el módulo de Cobranzas
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/clientes-atrasados")
def obtener_clientes_atrasados(
    dias_retraso: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener clientes atrasados filtrados por días de retraso
    
    Args:
        dias_retraso: Filtrar por días específicos de retraso (1, 3, 5, etc.)
                     Si es None, devuelve todos los clientes atrasados
    """
    try:
        # Calcular fecha límite según días de retraso
        hoy = date.today()
        
        # Cuotas vencidas (fecha_vencimiento < hoy y estado != PAGADO)
        query = db.query(
            Cliente.cedula,
            Cliente.nombres,
            Prestamo.analista,
            Prestamo.id.label('prestamo_id'),
            func.count(Cuota.id).label('cuotas_vencidas'),
            func.sum(Cuota.monto_cuota).label('total_adeudado'),
            func.min(Cuota.fecha_vencimiento).label('fecha_primera_vencida')
        ).join(
            Prestamo, Prestamo.cedula == Cliente.cedula
        ).join(
            Cuota, Cuota.prestamo_id == Prestamo.id
        ).filter(
            Cuota.fecha_vencimiento < hoy,
            Cuota.estado != 'PAGADO'
        ).group_by(
            Cliente.cedula, Cliente.nombres, Prestamo.analista, Prestamo.id
        )
        
        # Si se especifica días de retraso, filtrar por rango
        if dias_retraso:
            fecha_limite = hoy - timedelta(days=dias_retraso)
            query = query.filter(
                Cuota.fecha_vencimiento <= fecha_limite
            )
        
        resultados = query.all()
        
        # Convertir a diccionarios
        clientes_atrasados = []
        for row in resultados:
            clientes_atrasados.append({
                'cedula': row.cedula,
                'nombres': row.nombres,
                'analista': row.analista,
                'prestamo_id': row.prestamo_id,
                'cuotas_vencidas': row.cuotas_vencidas,
                'total_adeudado': float(row.total_adeudado) if row.total_adeudado else 0.0,
                'fecha_primera_vencida': row.fecha_primera_vencida.isoformat() if row.fecha_primera_vencida else None
            })
        
        return clientes_atrasados
    
    except Exception as e:
        logger.error(f"Error obteniendo clientes atrasados: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/clientes-por-cantidad-pagos")
def obtener_clientes_por_cantidad_pagos_atrasados(
    cantidad_pagos: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener clientes que tienen exactamente N cantidad de pagos atrasados
    """
    try:
        hoy = date.today()
        
        query = db.query(
            Cliente.cedula,
            Cliente.nombres,
            Prestamo.analista,
            Prestamo.id.label('prestamo_id'),
            func.sum(Cuota.monto_cuota).label('total_adeudado')
        ).join(
            Prestamo, Prestamo.cedula == Cliente.cedula
        ).join(
            Cuota, Cuota.prestamo_id == Prestamo.id
        ).filter(
            Cuota.fecha_vencimiento < hoy,
            Cuota.estado != 'PAGADO'
        ).group_by(
            Cliente.cedula, Cliente.nombres, Prestamo.analista, Prestamo.id
        ).having(
            func.count(Cuota.id) == cantidad_pagos
        )
        
        resultados = query.all()
        
        clientes = []
        for row in resultados:
            clientes.append({
                'cedula': row.cedula,
                'nombres': row.nombres,
                'analista': row.analista,
                'prestamo_id': row.prestamo_id,
                'total_adeudado': float(row.total_adeudado) if row.total_adeudado else 0.0
            })
        
        return clientes
    
    except Exception as e:
        logger.error(f"Error obteniendo clientes por cantidad de pagos: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/por-analista")
def obtener_cobranzas_por_analista(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estadísticas de cobranza por analista
    - Cantidad de clientes atrasados
    - Monto total sin cobrar
    """
    try:
        hoy = date.today()
        
        query = db.query(
            Prestamo.analista.label('nombre_analista'),
            func.count(func.distinct(Cliente.cedula)).label('cantidad_clientes'),
            func.sum(Cuota.monto_cuota).label('monto_total')
        ).join(
            Cliente, Cliente.cedula == Prestamo.cedula
        ).join(
            Cuota, Cuota.prestamo_id == Prestamo.id
        ).filter(
            Cuota.fecha_vencimiento < hoy,
            Cuota.estado != 'PAGADO',
            Prestamo.analista.isnot(None)
        ).group_by(
            Prestamo.analista
        ).having(
            func.count(func.distinct(Cliente.cedula)) > 0
        )
        
        resultados = query.all()
        
        analistas = []
        for row in resultados:
            analistas.append({
                'nombre': row.nombre_analista,
                'cantidad_clientes': row.cantidad_clientes,
                'monto_total': float(row.monto_total) if row.monto_total else 0.0
            })
        
        return analistas
    
    except Exception as e:
        logger.error(f"Error obteniendo cobranzas por analista: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/por-analista/{analista}/clientes")
def obtener_clientes_por_analista(
    analista: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener detalle de clientes atrasados para un analista específico
    """
    try:
        hoy = date.today()
        
        query = db.query(
            Cliente.cedula,
            Cliente.nombres,
            Cliente.telefono,
            Prestamo.id.label('prestamo_id'),
            func.count(Cuota.id).label('cuotas_vencidas'),
            func.sum(Cuota.monto_cuota).label('total_adeudado'),
            func.min(Cuota.fecha_vencimiento).label('fecha_primera_vencida')
        ).join(
            Prestamo, Prestamo.cedula == Cliente.cedula
        ).join(
            Cuota, Cuota.prestamo_id == Prestamo.id
        ).filter(
            Prestamo.analista == analista,
            Cuota.fecha_vencimiento < hoy,
            Cuota.estado != 'PAGADO'
        ).group_by(
            Cliente.cedula, Cliente.nombres, Cliente.telefono, Prestamo.id
        )
        
        resultados = query.all()
        
        clientes = []
        for row in resultados:
            clientes.append({
                'cedula': row.cedula,
                'nombres': row.nombres,
                'telefono': row.telefono,
                'prestamo_id': row.prestamo_id,
                'cuotas_vencidas': row.cuotas_vencidas,
                'total_adeudado': float(row.total_adeudado) if row.total_adeudado else 0.0,
                'fecha_primera_vencida': row.fecha_primera_vencida.isoformat() if row.fecha_primera_vencida else None
            })
        
        return clientes
    
    except Exception as e:
        logger.error(f"Error obteniendo clientes del analista {analista}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/montos-por-mes")
def obtener_montos_vencidos_por_mes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener montos vencidos agrupados por mes de vencimiento
    Solo incluye cuotas vencidas
    """
    try:
        hoy = date.today()
        
        query = db.query(
            func.date_trunc('month', Cuota.fecha_vencimiento).label('mes'),
            func.count(Cuota.id).label('cantidad_cuotas'),
            func.sum(Cuota.monto_cuota).label('monto_total')
        ).filter(
            Cuota.fecha_vencimiento < hoy,
            Cuota.estado != 'PAGADO'
        ).group_by(
            func.date_trunc('month', Cuota.fecha_vencimiento)
        ).order_by(
            func.date_trunc('month', Cuota.fecha_vencimiento)
        )
        
        resultados = query.all()
        
        montos_por_mes = []
        for row in resultados:
            montos_por_mes.append({
                'mes': row.mes.strftime('%Y-%m') if row.mes else None,
                'mes_display': row.mes.strftime('%B %Y') if row.mes else None,
                'cantidad_cuotas': row.cantidad_cuotas,
                'monto_total': float(row.monto_total) if row.monto_total else 0.0
            })
        
        return montos_por_mes
    
    except Exception as e:
        logger.error(f"Error obteniendo montos por mes: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/resumen")
def obtener_resumen_cobranzas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener resumen general de cobranzas
    """
    try:
        hoy = date.today()
        
        # Total de cuotas vencidas
        total_cuotas_vencidas = db.query(func.count(Cuota.id)).filter(
            Cuota.fecha_vencimiento < hoy,
            Cuota.estado != 'PAGADO'
        ).scalar() or 0
        
        # Monto total adeudado
        monto_total_adeudado = db.query(func.sum(Cuota.monto_cuota)).filter(
            Cuota.fecha_vencimiento < hoy,
            Cuota.estado != 'PAGADO'
        ).scalar() or 0.0
        
        # Cantidad de clientes únicos atrasados
        clientes_unicos = db.query(func.count(func.distinct(Prestamo.cedula))).join(
            Cuota, Cuota.prestamo_id == Prestamo.id
        ).filter(
            Cuota.fecha_vencimiento < hoy,
            Cuota.estado != 'PAGADO'
        ).scalar() or 0
        
        return {
            'total_cuotas_vencidas': total_cuotas_vencidas,
            'monto_total_adeudado': float(monto_total_adeudado),
            'clientes_atrasados': clientes_unicos
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo resumen de cobranzas: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

