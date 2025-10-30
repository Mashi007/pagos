import io
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models.auditoria import Auditoria
from app.models.user import User
from app.schemas.auditoria import (
    AuditoriaResponse,
    AuditoriaListResponse,
    AuditoriaStatsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _aplicar_filtros_auditoria(
    query, usuario_email, modulo, accion, fecha_desde, fecha_hasta
):
    # Aplicar filtros a la query de auditoría
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
    return query


def _aplicar_ordenamiento_auditoria(query, ordenar_por, orden):
    # Aplicar ordenamiento a la query de auditoría
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
    # Calcular información de paginación
    total_pages = (total + limit - 1) // limit
    current_page = (skip // limit) + 1
    return total_pages, current_page


@router.get("/auditoria", response_model=AuditoriaListResponse)
def listar_auditoria(
    usuario_email: Optional[str] = Query(
        None, description="Filtrar por email de usuario"
    ),
    modulo: Optional[str] = Query(None, description="Filtrar por módulo"),
    accion: Optional[str] = Query(None, description="Filtrar por acción"),
    skip: int = Query(0, ge=0, description="Registros a omitir (paginación)"),
    limit: int = Query(50, ge=1, le=200, description="Registros por página"),
    ordenar_por: str = Query("fecha", description="Campo para ordenar"),
    orden: str = Query("desc", description="Orden: asc o desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar registros de auditoría con filtros y paginación
    try:
        # Construir query base
        query = db.query(Auditoria).options(joinedload(Auditoria.usuario))

        # Aplicar filtros
        query = _aplicar_filtros_auditoria(
            query, usuario_email, modulo, accion, None, None
        )

        # Aplicar ordenamiento
        query = _aplicar_ordenamiento_auditoria(query, ordenar_por, orden)

        # Obtener total para paginación
        total = query.count()

        # Aplicar paginación
        query = query.offset(skip).limit(limit)

        # Ejecutar query
        registros = query.all()

        # Adaptar a respuesta esperada por el frontend
        items = []
        for r in registros:
            # Mapear campos del modelo existente a los esperados por el esquema/respuesta del frontend
            usuario_email_val = getattr(r.usuario, "email", None)
            modulo_val = getattr(r, "entidad", None)
            descripcion_val = getattr(r, "detalles", None)
            resultado_val = "EXITOSO" if getattr(r, "exito", True) else "FALLIDO"

            item = {
                "id": r.id,
                "usuario_id": r.usuario_id,
                "usuario_email": usuario_email_val,
                "accion": r.accion,
                "modulo": modulo_val,
                "tabla": modulo_val,  # fallback
                "registro_id": getattr(r, "entidad_id", None),
                "descripcion": descripcion_val,
                "ip_address": getattr(r, "ip_address", None),
                "user_agent": getattr(r, "user_agent", None),
                "resultado": resultado_val,
                "mensaje_error": getattr(r, "mensaje_error", None),
                "fecha": r.fecha,
            }
            items.append(AuditoriaResponse.model_validate(item))

        total_pages, current_page = _calcular_paginacion_auditoria(total, limit, skip)

        return {
            "items": items,
            "total": total,
            "page": current_page,
            "page_size": limit,
            "total_pages": total_pages,
        }

    except Exception as e:
        logger.error(f"Error listando auditoría: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/auditoria/exportar")
def exportar_auditoria(
    usuario_email: Optional[str] = Query(None),
    modulo: Optional[str] = Query(None),
    accion: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Exportar auditoría a Excel
    try:
        # Construir query
        query = db.query(Auditoria)
        query = _aplicar_filtros_auditoria(
            query, usuario_email, modulo, accion, fecha_desde, fecha_hasta
        )
        query = query.order_by(desc(Auditoria.fecha))

        # Obtener datos
        registros = query.all()

        # Crear archivo Excel
        output = _crear_excel_auditoria(registros)

        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=auditoria.xlsx"},
        )

    except Exception as e:
        logger.error(f"Error exportando auditoría: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


def _crear_excel_auditoria(registros):
    # Crear archivo Excel en memoria
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Auditoría"

    # Encabezados
    headers = ["Fecha", "Usuario", "Módulo", "Acción", "Detalles", "IP"]
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)

    # Datos
    for row, registro in enumerate(registros, 2):
        ws.cell(row=row, column=1, value=registro.fecha)
        ws.cell(row=row, column=2, value=registro.usuario_email)
        # El modelo base no tiene 'modulo', usamos 'entidad' y mapeamos resultado
        ws.cell(row=row, column=3, value=getattr(registro, "entidad", None))
        ws.cell(row=row, column=4, value=registro.accion)
        ws.cell(row=row, column=5, value=getattr(registro, "detalles", None))
        ws.cell(row=row, column=6, value=registro.ip_address)

    # Guardar en memoria
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return output


@router.get("/auditoria/stats", response_model=AuditoriaStatsResponse)
def estadisticas_auditoria(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Totales
        total_acciones = db.query(func.count(Auditoria.id)).scalar() or 0

        # Acciones por módulo (entidad)
        acciones_por_modulo_rows = (
            db.query(
                getattr(Auditoria, "entidad").label("modulo"), func.count(Auditoria.id)
            )
            .group_by(getattr(Auditoria, "entidad"))
            .all()
        )
        acciones_por_modulo = {
            row.modulo or "DESCONOCIDO": row[1] for row in acciones_por_modulo_rows
        }

        # Acciones por usuario (email)
        acciones_por_usuario_rows = (
            db.query(User.email, func.count(Auditoria.id))
            .join(User, User.id == Auditoria.usuario_id)
            .group_by(User.email)
            .all()
        )
        acciones_por_usuario = {row[0]: row[1] for row in acciones_por_usuario_rows}

        # Hoy / semana / mes
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        inicio_hoy = datetime(now.year, now.month, now.day)
        inicio_semana = inicio_hoy - timedelta(days=6)
        inicio_mes = datetime(now.year, now.month, 1)

        acciones_hoy = (
            db.query(func.count(Auditoria.id))
            .filter(Auditoria.fecha >= inicio_hoy)
            .scalar()
            or 0
        )
        acciones_esta_semana = (
            db.query(func.count(Auditoria.id))
            .filter(Auditoria.fecha >= inicio_semana)
            .scalar()
            or 0
        )
        acciones_este_mes = (
            db.query(func.count(Auditoria.id))
            .filter(Auditoria.fecha >= inicio_mes)
            .scalar()
            or 0
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
        logger.error(f"Error obteniendo estadísticas de auditoría: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
