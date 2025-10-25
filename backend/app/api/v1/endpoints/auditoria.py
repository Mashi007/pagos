"""
Endpoints de auditoría del sistema
Registro y consulta de acciones de usuarios
"""

import io
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.auditoria import Auditoria
from app.models.user import User
from app.schemas.auditoria import (
    AuditoriaListResponse,
    AuditoriaResponse,
    AuditoriaStatsResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# ============================================
# CRUD DE AUDITORÍA
# ============================================


@router.get("/", response_model=AuditoriaListResponse, summary="Listar auditoría")
def listar_auditoria(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(50, ge=1, le=1000, description="Número de registros a retornar"),
    usuario_email: Optional[str] = Query(
        None, description="Filtrar por email de usuario"
    ),
    modulo: Optional[str] = Query(None, description="Filtrar por módulo"),
    accion: Optional[str] = Query(None, description="Filtrar por acción"),
    fecha_desde: Optional[datetime] = Query(None, description="Fecha desde"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha hasta"),
    ordenar_por: str = Query("fecha", description="Campo para ordenar"),
    orden: str = Query("desc", description="Orden: asc o desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📋 Listar registros de auditoría con filtros y paginación

    Todos los usuarios pueden ver auditoría
    """
    try:
        # Construir query base
        query = db.query(Auditoria)

        # Aplicar filtros
        if usuario_email:
            query = query.filter(Auditoria.usuario_email.ilike(f"%{usuario_email}%"))

        if modulo:
            query = query.filter(Auditoria.modulo == modulo)

        if accion:
            query = query.filter(Auditoria.accion == accion)

        if fecha_desde:
            query = query.filter(Auditoria.fecha >= fecha_desde)

        if fecha_hasta:
            query = query.filter(Auditoria.fecha <= fecha_hasta)

        # Contar total
        total = query.count()

        # Aplicar ordenamiento
        if ordenar_por == "usuario_email":
            order_field = Auditoria.usuario_email
        elif ordenar_por == "modulo":
            order_field = Auditoria.modulo
        elif ordenar_por == "accion":
            order_field = Auditoria.accion
        else:
            order_field = Auditoria.fecha

        if orden == "asc":
            query = query.order_by(asc(order_field))
        else:
            query = query.order_by(desc(order_field))

        # Aplicar paginación
        auditorias = query.offset(skip).limit(limit).all()

        # Calcular páginas
        total_pages = (total + limit - 1) // limit
        current_page = (skip // limit) + 1

        return AuditoriaListResponse(
            items=auditorias,
            total=total,
            page=current_page,
            page_size=limit,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error(f"Error listando auditoría: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get(
    "/stats", response_model=AuditoriaStatsResponse, summary="Estadísticas de auditoría"
)
def obtener_estadisticas_auditoria(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    📊 Obtener estadísticas de auditoría

    Todos los usuarios pueden ver estadísticas
    """
    try:
        # Total de acciones
        total_acciones = db.query(Auditoria).count()

        # Acciones por módulo
        acciones_por_modulo = {}
        modulos = (
            db.query(Auditoria.modulo, func.count(Auditoria.id))
            .group_by(Auditoria.modulo)
            .all()
        )
        for modulo, count in modulos:
            acciones_por_modulo[modulo] = count

        # Acciones por usuario (top 10)
        acciones_por_usuario = {}
        usuarios = (
            db.query(Auditoria.usuario_email, func.count(Auditoria.id))
            .group_by(Auditoria.usuario_email)
            .order_by(func.count(Auditoria.id).desc())
            .limit(10)
            .all()
        )
        for email, count in usuarios:
            if email:  # Solo si tiene email
                acciones_por_usuario[email] = count

        # Acciones por período
        hoy = datetime.now().date()
        esta_semana = hoy - timedelta(days=7)
        este_mes = hoy - timedelta(days=30)

        acciones_hoy = (
            db.query(Auditoria).filter(func.date(Auditoria.fecha) == hoy).count()
        )
        acciones_esta_semana = (
            db.query(Auditoria)
            .filter(func.date(Auditoria.fecha) >= esta_semana)
            .count()
        )
        acciones_este_mes = (
            db.query(Auditoria).filter(func.date(Auditoria.fecha) >= este_mes).count()
        )

        return AuditoriaStatsResponse(
            total_acciones=total_acciones,
            acciones_por_modulo=acciones_por_modulo,
            acciones_por_usuario=acciones_por_usuario,
            acciones_hoy=acciones_hoy,
            acciones_esta_semana=acciones_esta_semana,
            acciones_este_mes=acciones_este_mes,
        )

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/export/excel", summary="Exportar auditoría a Excel")
def exportar_auditoria_excel(
    usuario_email: Optional[str] = Query(
        None, description="Filtrar por email de usuario"
    ),
    modulo: Optional[str] = Query(None, description="Filtrar por módulo"),
    accion: Optional[str] = Query(None, description="Filtrar por acción"),
    fecha_desde: Optional[datetime] = Query(None, description="Fecha desde"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha hasta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📊 Exportar auditoría a Excel (SOLO ADMIN)

    Solo los administradores pueden exportar auditoría
    """
    try:
        # Verificar permisos - solo ADMIN puede exportar
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Solo los administradores pueden exportar auditoría",
            )

        # Construir query base
        query = db.query(Auditoria)

        # Aplicar filtros
        if usuario_email:
            query = query.filter(Auditoria.usuario_email.ilike(f"%{usuario_email}%"))

        if modulo:
            query = query.filter(Auditoria.modulo == modulo)

        if accion:
            query = query.filter(Auditoria.accion == accion)

        if fecha_desde:
            query = query.filter(Auditoria.fecha >= fecha_desde)

        if fecha_hasta:
            query = query.filter(Auditoria.fecha <= fecha_hasta)

        # Obtener todos los registros (sin paginación para export)
        auditorias = query.order_by(desc(Auditoria.fecha)).all()

        # Crear DataFrame
        data = []
        for auditoria in auditorias:
            data.append(
                {
                    "ID": auditoria.id,
                    "Email Usuario": auditoria.usuario_email or "N/A",
                    "Acción": auditoria.accion,
                    "Módulo": auditoria.modulo,
                    "Tabla": auditoria.tabla,
                    "ID Registro": auditoria.registro_id or "N/A",
                    "Descripción": auditoria.descripcion or "N/A",
                    "IP Address": auditoria.ip_address or "N/A",
                    "Resultado": auditoria.resultado,
                    "Fecha": auditoria.fecha.strftime("%Y-%m-%d %H:%M:%S"),
                    "Mensaje Error": auditoria.mensaje_error or "N/A",
                }
            )

        df = pd.DataFrame(data)

        # Crear archivo Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Auditoría", index=False)

        output.seek(0)

        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"auditoria_{timestamp}.xlsx"

        # Registrar la exportación
        logger.info(f"Usuario {current_user.email} exportó auditoría: {filename}")

        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando auditoría: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get(
    "/{auditoria_id}", response_model=AuditoriaResponse, summary="Obtener auditoría"
)
def obtener_auditoria(
    auditoria_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔍 Obtener un registro de auditoría por ID

    Todos los usuarios pueden ver detalles de auditoría
    """
    try:
        auditoria = db.query(Auditoria).filter(Auditoria.id == auditoria_id).first()

        if not auditoria:
            raise HTTPException(
                status_code=404, detail="Registro de auditoría no encontrado"
            )

        return auditoria

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo auditoría {auditoria_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
