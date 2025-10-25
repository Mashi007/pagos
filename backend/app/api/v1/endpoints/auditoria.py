from datetime import date
"""Endpoints de auditoría del sistema
""""""

import io
import logging
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.auditoria import Auditoria
from app.models.user import User
from app.schemas.auditoria import 

router = APIRouter()
logger = logging.getLogger(__name__)

# ============================================
# CRUD DE AUDITORÍA
# ============================================


    query, usuario_email, modulo, accion, fecha_desde, fecha_hasta
    if usuario_email:
        query = query.filter
            Auditoria.usuario_email.ilike(f"%{usuario_email}%")
    if modulo:
        query = query.filter(Auditoria.modulo == modulo)
    if accion:
        query = query.filter(Auditoria.accion == accion)
    if fecha_desde:
        query = query.filter(Auditoria.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Auditoria.fecha <= fecha_hasta)
    return query


def _aplicar_ordenamiento_auditoria(query, ordenar_por, orden):
    """Aplicar ordenamiento a la query de auditoría"""
    if ordenar_por == "usuario_email":
        order_field = Auditoria.usuario_email
    elif ordenar_por == "modulo":
        order_field = Auditoria.modulo
    elif ordenar_por == "accion":
        order_field = Auditoria.accion
    else:
        order_field = Auditoria.fecha

    if orden == "asc":
        return query.order_by(asc(order_field))
    else:
        return query.order_by(desc(order_field))


def _calcular_paginacion_auditoria(total, limit, skip):
    """Calcular información de paginación"""
    total_pages = (total + limit - 1) // limit
    current_page = (skip // limit) + 1
    return total_pages, current_page

@router.get


def listar_auditoria
    usuario_email: Optional[str] = Query
    modulo: Optional[str] = Query(None, description="Filtrar por módulo"),
    accion: Optional[str] = Query(None, description="Filtrar por acción"),
    ordenar_por: str = Query("fecha", description="Campo para ordenar"),
    orden: str = Query("desc", description="Orden: asc o desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """"""
    REFACTORIZADA)
    """"""
    try:
        # Construir query base
        query = db.query(Auditoria)

            query, usuario_email, modulo, accion, fecha_desde, fecha_hasta

        # Contar total
        total = query.count()

        # Aplicar ordenamiento
        query = _aplicar_ordenamiento_auditoria(query, ordenar_por, orden)

        # Aplicar paginación
        auditorias = query.offset(skip).limit(limit).all()

        # Calcular páginas
        total_pages, current_page = _calcular_paginacion_auditoria

        return AuditoriaListResponse
    except Exception as e:
        logger.error(f"Error listando auditoría: {e}")
        raise HTTPException

@router.get


def obtener_estadisticas_auditoria
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """"""
    📊 Obtener estadísticas de auditoría
    """"""
    try:
        # Total de acciones
        total_acciones = db.query(Auditoria).count()

        # Acciones por módulo
        acciones_por_modulo = {}
            db.query(Auditoria.modulo, func.count(Auditoria.id))
            .group_by(Auditoria.modulo)
            .all()
            acciones_por_modulo[modulo] = count

        # Acciones por usuario (top 10)
        acciones_por_usuario = {}
            db.query(Auditoria.usuario_email, func.count(Auditoria.id))
            .group_by(Auditoria.usuario_email)
            .order_by(func.count(Auditoria.id).desc())
            .limit(10)
            .all()
            if email:  # Solo si tiene email
                acciones_por_usuario[email] = count

        # Acciones por período

        acciones_hoy = 
            db.query(Auditoria)
            .filter(func.date(Auditoria.fecha) == hoy)
            .count()
        acciones_esta_semana = 
            db.query(Auditoria)
            .filter(func.date(Auditoria.fecha) >= esta_semana)
            .count()
        acciones_este_mes = 
            db.query(Auditoria)
            .filter(func.date(Auditoria.fecha) >= este_mes)
            .count()

        return AuditoriaStatsResponse
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException


def _crear_dataframe_auditoria(auditorias):
    data = []
    for auditoria in auditorias:
        data.append
    return pd.DataFrame(data)


def _crear_excel_auditoria(df):
    """Crear archivo Excel en memoria"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Auditoría", index=False)
    output.seek(0)
    return output

@router.get("/export/excel", summary="Exportar auditoría a Excel")
def exportar_auditoria_excel
    modulo: Optional[str] = Query(None, description="Filtrar por módulo"),
    accion: Optional[str] = Query(None, description="Filtrar por acción"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """"""
    📊 Exportar auditoría a Excel (SOLO ADMIN)
    """"""
    try:
        if not current_user.is_admin:
            raise HTTPException

        query = db.query(Auditoria)
            query, usuario_email, modulo, accion, fecha_desde, fecha_hasta

        auditorias = query.order_by(desc(Auditoria.fecha)).all()
        df = _crear_dataframe_auditoria(auditorias)

        # Crear Excel y generar respuesta
        output = _crear_excel_auditoria(df)

        # Registrar la exportación
        logger.info

        return Response
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument. \
            spreadsheetml.sheet",
            headers=
            },
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando auditoría: {e}")
        raise HTTPException

@router.get


def obtener_auditoria
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """"""
    🔍 Obtener un registro de auditoría por ID
    """"""
    try:
        auditoria = 
            db.query(Auditoria).filter(Auditoria.id == auditoria_id).first()
        if not auditoria:
            raise HTTPException
        return auditoria
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo auditoría {auditoria_id}: {e}")
        raise HTTPException

"""
""""""