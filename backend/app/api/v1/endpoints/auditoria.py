import io
import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models.auditoria import Auditoria
from app.models.pago_auditoria import PagoAuditoria
from app.models.prestamo_auditoria import PrestamoAuditoria
from app.models.user import User
from app.schemas.auditoria import (
    AuditoriaCreate,
    AuditoriaListResponse,
    AuditoriaResponse,
    AuditoriaStatsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _aplicar_filtros_auditoria(query, usuario_email, modulo, accion, fecha_desde, fecha_hasta):
    # Aplicar filtros a la query de auditoría (usando columnas seguras)
    if usuario_email:
        query = query.join(User, User.id == Auditoria.usuario_id).filter(User.email.ilike(f"%{usuario_email}%"))
    if modulo:
        query = query.filter(Auditoria.entidad == modulo)
    if accion:
        query = query.filter(Auditoria.accion == accion)
    if fecha_desde:
        query = query.filter(Auditoria.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Auditoria.fecha <= fecha_hasta)
    return query


def _aplicar_ordenamiento_auditoria(query, ordenar_por, orden):
    # Ordenar en SQL solo por fecha; el resto se ordena luego en memoria
    order_field = Auditoria.fecha
    return query.order_by(asc(order_field) if orden == "asc" else desc(order_field))


def _calcular_paginacion_auditoria(total, limit, skip):
    # Calcular información de paginación
    total_pages = (total + limit - 1) // limit
    current_page = (skip // limit) + 1
    return total_pages, current_page


@router.get("/auditoria", response_model=AuditoriaListResponse)
def listar_auditoria(
    usuario_email: Optional[str] = Query(None, description="Filtrar por email de usuario"),
    modulo: Optional[str] = Query(None, description="Filtrar por módulo"),
    accion: Optional[str] = Query(None, description="Filtrar por acción"),
    skip: int = Query(0, ge=0, description="Registros a omitir (paginación)"),
    limit: int = Query(50, ge=1, le=200, description="Registros por página"),
    ordenar_por: str = Query("fecha", description="Campo para ordenar"),
    orden: str = Query("desc", description="Orden: asc o desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar registros de auditoría con filtros y paginación (incluye fuentes detalladas)
    try:
        # Construir query base (auditoría general)
        query = db.query(Auditoria).options(joinedload(Auditoria.usuario))

        # Aplicar filtros
        query = _aplicar_filtros_auditoria(query, usuario_email, modulo, accion, None, None)

        # Aplicar ordenamiento
        query = _aplicar_ordenamiento_auditoria(query, ordenar_por, orden)

        # Ejecutar consultas y unificar (general + préstamos + pagos)
        registros_general = query.all()
        registros_prestamos = db.query(PrestamoAuditoria).order_by(PrestamoAuditoria.fecha_cambio.desc()).all()
        registros_pagos = db.query(PagoAuditoria).order_by(PagoAuditoria.fecha_cambio.desc()).all()

        unified = []

        # General
        for r in registros_general:
            usuario_email_val = getattr(r.usuario, "email", None)
            modulo_val = getattr(r, "entidad", None)
            descripcion_val = getattr(r, "detalles", None)
            exito_attr = getattr(r, "exito", None)
            if isinstance(exito_attr, bool):
                resultado_val = "EXITOSO" if exito_attr else "FALLIDO"
            else:
                resultado_val = exito_attr or "EXITOSO"
            unified.append(
                {
                    "id": r.id,
                    "usuario_id": r.usuario_id,
                    "usuario_email": usuario_email_val,
                    "accion": r.accion,
                    "modulo": modulo_val,
                    "tabla": modulo_val,
                    "registro_id": getattr(r, "entidad_id", None),
                    "descripcion": descripcion_val,
                    "ip_address": getattr(r, "ip_address", None),
                    "user_agent": getattr(r, "user_agent", None),
                    "resultado": resultado_val,
                    "mensaje_error": getattr(r, "mensaje_error", None),
                    "fecha": r.fecha,
                }
            )

        # Prestamos detallada
        for r in registros_prestamos:
            desc = f"{r.accion} {r.campo_modificado}: "
            if r.valor_anterior is not None:
                desc += f"{r.valor_anterior} -> "
            desc += f"{r.valor_nuevo}"
            if r.observaciones:
                desc += f" ({r.observaciones})"

            unified.append(
                {
                    "id": r.id,
                    "usuario_id": None,
                    "usuario_email": r.usuario,
                    "accion": r.accion,
                    "modulo": "PRESTAMOS",
                    "tabla": "prestamos",
                    "registro_id": r.prestamo_id,
                    "descripcion": desc,
                    "ip_address": None,
                    "user_agent": None,
                    "resultado": "EXITOSO",
                    "mensaje_error": None,
                    "fecha": r.fecha_cambio,
                }
            )

        # Pagos detallada
        for r in registros_pagos:
            desc = f"{r.accion} {r.campo_modificado}: "
            if r.valor_anterior is not None:
                desc += f"{r.valor_anterior} -> "
            desc += f"{r.valor_nuevo}"
            if getattr(r, "observaciones", None):
                desc += f" ({r.observaciones})"

            unified.append(
                {
                    "id": r.id,
                    "usuario_id": None,
                    "usuario_email": r.usuario,
                    "accion": r.accion,
                    "modulo": "PAGOS",
                    "tabla": "pagos",
                    "registro_id": r.pago_id,
                    "descripcion": desc,
                    "ip_address": None,
                    "user_agent": None,
                    "resultado": "EXITOSO",
                    "mensaje_error": None,
                    "fecha": r.fecha_cambio,
                }
            )

        # Aplicar filtros en memoria para unificado
        if usuario_email:
            unified = [u for u in unified if u.get("usuario_email") and usuario_email.lower() in u["usuario_email"].lower()]
        if modulo:
            unified = [u for u in unified if u.get("modulo") == modulo]
        if accion:
            unified = [u for u in unified if u.get("accion") == accion]

        # Orden y paginación
        reverse = orden != "asc"
        key_map = {
            "usuario_email": lambda x: x.get("usuario_email") or "",
            "modulo": lambda x: x.get("modulo") or "",
            "accion": lambda x: x.get("accion") or "",
            "fecha": lambda x: x.get("fecha") or 0,
        }
        sort_key = key_map.get(ordenar_por, key_map["fecha"])
        unified.sort(key=sort_key, reverse=reverse)

        total = len(unified)
        total_pages, current_page = _calcular_paginacion_auditoria(total, limit, skip)
        paged = unified[skip : skip + limit]

        items = [AuditoriaResponse.model_validate(i) for i in paged]

        return {
            "items": items,
            "total": total,
            "page": current_page,
            "page_size": limit,
            "total_pages": total_pages,
        }

    except Exception as e:
        logger.error(f"Error listando auditoría: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


def _aplicar_filtros_detalladas(
    query_prestamos, query_pagos, accion: Optional[str], fecha_desde: Optional[date], fecha_hasta: Optional[date]
):
    """Aplica filtros a las queries de auditoría detallada"""
    if accion:
        query_prestamos = query_prestamos.filter(PrestamoAuditoria.accion == accion)
        query_pagos = query_pagos.filter(PagoAuditoria.accion == accion)
    if fecha_desde:
        query_prestamos = query_prestamos.filter(PrestamoAuditoria.fecha_cambio >= fecha_desde)
        query_pagos = query_pagos.filter(PagoAuditoria.fecha_cambio >= fecha_desde)
    if fecha_hasta:
        query_prestamos = query_prestamos.filter(PrestamoAuditoria.fecha_cambio <= fecha_hasta)
        query_pagos = query_pagos.filter(PagoAuditoria.fecha_cambio <= fecha_hasta)
    return query_prestamos, query_pagos


def _convertir_registro_general_a_dict(registro) -> dict:
    """Convierte un registro de Auditoria general a dict unificado"""
    return {
        "fecha": registro.fecha,
        "usuario_email": registro.usuario_email,
        "modulo": getattr(registro, "entidad", None),
        "accion": registro.accion,
        "descripcion": getattr(registro, "detalles", None),
        "ip_address": getattr(registro, "ip_address", None),
    }


def _generar_descripcion_detallada(registro) -> str:
    """Genera descripción textual para registro detallado de auditoría"""
    desc_text = f"{registro.accion} {registro.campo_modificado}: "
    if registro.valor_anterior is not None:
        desc_text += f"{registro.valor_anterior} -> "
    desc_text += f"{registro.valor_nuevo}"
    observaciones = getattr(registro, "observaciones", None)
    if observaciones:
        desc_text += f" ({observaciones})"
    return desc_text


def _convertir_registro_prestamos_a_dict(registro: PrestamoAuditoria) -> dict:
    """Convierte un registro de PrestamoAuditoria a dict unificado"""
    return {
        "fecha": registro.fecha_cambio,
        "usuario_email": registro.usuario,
        "modulo": "PRESTAMOS",
        "accion": registro.accion,
        "descripcion": _generar_descripcion_detallada(registro),
        "ip_address": None,
    }


def _convertir_registro_pagos_a_dict(registro: PagoAuditoria) -> dict:
    """Convierte un registro de PagoAuditoria a dict unificado"""
    return {
        "fecha": registro.fecha_cambio,
        "usuario_email": registro.usuario,
        "modulo": "PAGOS",
        "accion": registro.accion,
        "descripcion": _generar_descripcion_detallada(registro),
        "ip_address": None,
    }


def _unificar_registros_auditoria(
    registros_general: List, registros_prestamos: List[PrestamoAuditoria], registros_pagos: List[PagoAuditoria]
) -> List[dict]:
    """Unifica todos los registros de auditoría en una lista de dicts"""
    unified = []
    for r in registros_general:
        unified.append(_convertir_registro_general_a_dict(r))
    for r in registros_prestamos:
        unified.append(_convertir_registro_prestamos_a_dict(r))
    for r in registros_pagos:
        unified.append(_convertir_registro_pagos_a_dict(r))
    unified.sort(key=lambda x: x.get("fecha") or 0, reverse=True)
    return unified


def _generar_detalles_exportacion(
    usuario_email: Optional[str], modulo: Optional[str], accion: Optional[str]
) -> str:
    """Genera el texto de detalles para la auditoría de exportación"""
    detalles = "Exportó auditoría unificada"
    if usuario_email:
        detalles += f" (usuario_email={usuario_email})"
    if modulo:
        detalles += f" (modulo={modulo})"
    if accion:
        detalles += f" (accion={accion})"
    return detalles


def _registrar_auditoria_exportacion(
    db: Session, current_user: User, usuario_email: Optional[str], modulo: Optional[str], accion: Optional[str]
):
    """Registra la auditoría de la exportación"""
    try:
        detalles = _generar_detalles_exportacion(usuario_email, modulo, accion)
        audit = Auditoria(
            usuario_id=current_user.id,
            accion="EXPORT",
            entidad="AUDITORIA",
            entidad_id=None,
            detalles=detalles,
            exito=True,
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.warning(f"No se pudo registrar auditoría exportación de auditoría: {e}")


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
    """Exportar auditoría a Excel"""
    try:
        if not getattr(current_user, "is_admin", False):
            raise HTTPException(status_code=403, detail="No autorizado")

        query_general = db.query(Auditoria)
        query_general = _aplicar_filtros_auditoria(
            query_general, usuario_email, modulo, accion, fecha_desde, fecha_hasta
        ).order_by(desc(Auditoria.fecha))
        registros_general = query_general.all()

        query_prestamos = db.query(PrestamoAuditoria).order_by(desc(PrestamoAuditoria.fecha_cambio))
        query_pagos = db.query(PagoAuditoria).order_by(desc(PagoAuditoria.fecha_cambio))
        query_prestamos, query_pagos = _aplicar_filtros_detalladas(query_prestamos, query_pagos, accion, fecha_desde, fecha_hasta)

        registros_prestamos: List[PrestamoAuditoria] = query_prestamos.all()
        registros_pagos: List[PagoAuditoria] = query_pagos.all()

        unified = _unificar_registros_auditoria(registros_general, registros_prestamos, registros_pagos)
        output = _crear_excel_auditoria_unificado(unified)

        _registrar_auditoria_exportacion(db, current_user, usuario_email, modulo, accion)

        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=auditoria.xlsx"},
        )

    except Exception as e:
        logger.error(f"Error exportando auditoría: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


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
        ws.cell(row=row, column=1, value=getattr(registro, "fecha", None))
        # Intentar email directo o desde relación usuario
        usuario_email = getattr(registro, "usuario_email", None)
        if not usuario_email and getattr(registro, "usuario", None) is not None:
            usuario_email = getattr(registro.usuario, "email", None)
        ws.cell(row=row, column=2, value=usuario_email)
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


def _crear_excel_auditoria_unificado(registros):
    # Crear archivo Excel en memoria a partir de lista de dicts unificada
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Auditoría"

    headers = ["Fecha", "Usuario", "Módulo", "Acción", "Detalles", "IP"]
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)

    for row, registro in enumerate(registros, 2):
        ws.cell(row=row, column=1, value=registro.get("fecha"))
        ws.cell(row=row, column=2, value=registro.get("usuario_email"))
        ws.cell(row=row, column=3, value=registro.get("modulo"))
        ws.cell(row=row, column=4, value=registro.get("accion"))
        ws.cell(row=row, column=5, value=registro.get("descripcion"))
        ws.cell(row=row, column=6, value=registro.get("ip_address"))

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
        # Totales (sumando fuentes detalladas)
        total_acciones = (
            (db.query(func.count(Auditoria.id)).scalar() or 0)
            + (db.query(func.count(PrestamoAuditoria.id)).scalar() or 0)
            + (db.query(func.count(PagoAuditoria.id)).scalar() or 0)
        )

        # Acciones por módulo (entidad)
        acciones_por_modulo: dict[str, int] = {}
        # Calcular acciones por módulo de forma segura
        for r in db.query(Auditoria.entidad).all():
            key = getattr(r, "entidad", None) or "DESCONOCIDO"
            acciones_por_modulo[key] = acciones_por_modulo.get(key, 0) + 1
        acciones_por_modulo["PRESTAMOS"] = acciones_por_modulo.get("PRESTAMOS", 0) + (
            db.query(func.count(PrestamoAuditoria.id)).scalar() or 0
        )
        acciones_por_modulo["PAGOS"] = acciones_por_modulo.get("PAGOS", 0) + (
            db.query(func.count(PagoAuditoria.id)).scalar() or 0
        )

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
            (db.query(func.count(Auditoria.id)).filter(Auditoria.fecha >= inicio_hoy).scalar() or 0)
            + (db.query(func.count(PrestamoAuditoria.id)).filter(PrestamoAuditoria.fecha_cambio >= inicio_hoy).scalar() or 0)
            + (db.query(func.count(PagoAuditoria.id)).filter(PagoAuditoria.fecha_cambio >= inicio_hoy).scalar() or 0)
        )
        acciones_esta_semana = (
            (db.query(func.count(Auditoria.id)).filter(Auditoria.fecha >= inicio_semana).scalar() or 0)
            + (
                db.query(func.count(PrestamoAuditoria.id)).filter(PrestamoAuditoria.fecha_cambio >= inicio_semana).scalar()
                or 0
            )
            + (db.query(func.count(PagoAuditoria.id)).filter(PagoAuditoria.fecha_cambio >= inicio_semana).scalar() or 0)
        )
        acciones_este_mes = (
            (db.query(func.count(Auditoria.id)).filter(Auditoria.fecha >= inicio_mes).scalar() or 0)
            + (db.query(func.count(PrestamoAuditoria.id)).filter(PrestamoAuditoria.fecha_cambio >= inicio_mes).scalar() or 0)
            + (db.query(func.count(PagoAuditoria.id)).filter(PagoAuditoria.fecha_cambio >= inicio_mes).scalar() or 0)
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


@router.post("/auditoria/registrar", response_model=AuditoriaResponse)
def registrar_evento_auditoria(
    data: AuditoriaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Registrar un evento genérico de auditoría (ej.: confirmación de advertencia)

    Campos esperados en body: modulo, accion, descripcion, registro_id (opcional)
    """
    try:
        audit = Auditoria(
            usuario_id=current_user.id,
            accion=data.accion,
            entidad=data.modulo,
            entidad_id=data.registro_id,
            detalles=data.descripcion,
            ip_address=None,
            user_agent=None,
            exito=True,
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)

        item = {
            "id": audit.id,
            "usuario_id": audit.usuario_id,
            "usuario_email": getattr(audit.usuario, "email", None),
            "accion": audit.accion,
            "modulo": getattr(audit, "entidad", None),
            "tabla": getattr(audit, "entidad", None),
            "registro_id": getattr(audit, "entidad_id", None),
            "descripcion": getattr(audit, "detalles", None),
            "ip_address": getattr(audit, "ip_address", None),
            "user_agent": getattr(audit, "user_agent", None),
            "resultado": getattr(audit, "exito", None) or "EXITOSO",
            "mensaje_error": getattr(audit, "mensaje_error", None),
            "fecha": getattr(audit, "fecha", None),
        }
        return AuditoriaResponse.model_validate(item)
    except Exception as e:
        logger.error(f"Error registrando auditoría: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
