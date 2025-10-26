import io
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.auditoria import Auditoria
from app.models.user import User
from app.schemas.auditoria import AuditoriaResponse

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


@router.get("/auditoria")
def listar_auditoria(
    usuario_email: Optional[str] = Query(
        None, description="Filtrar por email de usuario"
    ),
    modulo: Optional[str] = Query(None, description="Filtrar por módulo"),
    accion: Optional[str] = Query(None, description="Filtrar por acción"),
    ordenar_por: str = Query("fecha", description="Campo para ordenar"),
    orden: str = Query("desc", description="Orden: asc o desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar registros de auditoría con filtros y paginación
    try:
        # Construir query base
        query = db.query(Auditoria)

        # Aplicar filtros
        query = _aplicar_filtros_auditoria(
            query, usuario_email, modulo, accion, None, None
        )

        # Aplicar ordenamiento
        query = _aplicar_ordenamiento_auditoria(query, ordenar_por, orden)

        # Obtener total para paginación
        total = query.count()

        # Aplicar paginación
        limit = 50
        skip = 0
        query = query.offset(skip).limit(limit)

        # Ejecutar query
        registros = query.all()

        # Calcular paginación
        total_pages, current_page = _calcular_paginacion_auditoria(total, limit, skip)

        return {
            "data": [AuditoriaResponse.model_validate(r) for r in registros],
            "pagination": {
                "total": total,
                "limit": limit,
                "skip": skip,
                "total_pages": total_pages,
                "current_page": current_page,
                "has_next": skip + limit < total,
                "has_prev": skip > 0,
            },
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
        ws.cell(row=row, column=3, value=registro.modulo)
        ws.cell(row=row, column=4, value=registro.accion)
        ws.cell(row=row, column=5, value=registro.detalles)
        ws.cell(row=row, column=6, value=registro.ip_address)

    # Guardar en memoria
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return output
