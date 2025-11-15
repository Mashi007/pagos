import io
import logging
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import asc, desc, func, text
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


def _determinar_resultado_auditoria(exito_attr) -> str:
    """Determina el resultado de auditoría desde el atributo exito"""
    if isinstance(exito_attr, bool):
        return "EXITOSO" if exito_attr else "FALLIDO"
    return exito_attr or "EXITOSO"


def _convertir_registro_general_listado(registro) -> dict:
    """Convierte un registro de Auditoria general a dict para listado"""
    # Manejar caso donde usuario puede ser None
    usuario_email_val = None
    if hasattr(registro, "usuario") and registro.usuario is not None:
        usuario_email_val = getattr(registro.usuario, "email", None)
    modulo_val = getattr(registro, "entidad", None)
    # Extraer campo de la descripción si está disponible (formato: "ACCION campo: valor")
    descripcion = getattr(registro, "detalles", None) or ""
    campo = None
    if descripcion and ":" in descripcion:
        # Intentar extraer el campo de la descripción
        partes = descripcion.split(":", 1)
        if len(partes) > 0:
            campo_parte = partes[0].strip()
            # Remover la acción si está al inicio
            for accion in ["CREAR", "ACTUALIZAR", "ELIMINAR", "UPDATE", "CREATE", "DELETE"]:
                if campo_parte.startswith(accion):
                    campo_parte = campo_parte[len(accion) :].strip()
                    break
            if campo_parte:
                campo = campo_parte
    return {
        "id": registro.id,
        "usuario_id": registro.usuario_id,
        "usuario_email": usuario_email_val,
        "accion": registro.accion,
        "modulo": modulo_val,
        "tabla": modulo_val,
        "registro_id": getattr(registro, "entidad_id", None),
        "descripcion": descripcion,
        "campo": campo,  # Campo extraído de la descripción
        "ip_address": getattr(registro, "ip_address", None),
        "user_agent": getattr(registro, "user_agent", None),
        "resultado": _determinar_resultado_auditoria(getattr(registro, "exito", None)),
        "mensaje_error": getattr(registro, "mensaje_error", None),
        "fecha": registro.fecha,
    }


def _convertir_registro_prestamos_listado(registro: PrestamoAuditoria) -> dict:
    """Convierte un registro de PrestamoAuditoria a dict para listado"""
    desc = _generar_descripcion_detallada(registro)
    return {
        "id": registro.id,
        "usuario_id": None,
        "usuario_email": registro.usuario,
        "accion": registro.accion,
        "modulo": "PRESTAMOS",
        "tabla": "prestamos",
        "registro_id": registro.prestamo_id,
        "descripcion": desc,
        "campo": registro.campo_modificado,  # Campo modificado explícito
        "ip_address": None,
        "user_agent": None,
        "resultado": "EXITOSO",
        "mensaje_error": None,
        "fecha": registro.fecha_cambio,
    }


def _convertir_registro_pagos_listado(registro: PagoAuditoria) -> dict:
    """Convierte un registro de PagoAuditoria a dict para listado"""
    desc = _generar_descripcion_detallada(registro)
    return {
        "id": registro.id,
        "usuario_id": None,
        "usuario_email": registro.usuario,
        "accion": registro.accion,
        "modulo": "PAGOS",
        "tabla": "pagos",
        "registro_id": registro.pago_id,
        "descripcion": desc,
        "campo": registro.campo_modificado,  # Campo modificado explícito
        "ip_address": None,
        "user_agent": None,
        "resultado": "EXITOSO",
        "mensaje_error": None,
        "fecha": registro.fecha_cambio,
    }


def _unificar_registros_auditoria_listado(
    registros_general: List, registros_prestamos: List[PrestamoAuditoria], registros_pagos: List[PagoAuditoria]
) -> List[dict]:
    """Unifica todos los registros de auditoría para listado"""
    unified = []
    for r in registros_general:
        unified.append(_convertir_registro_general_listado(r))
    for r in registros_prestamos:
        unified.append(_convertir_registro_prestamos_listado(r))
    for r in registros_pagos:
        unified.append(_convertir_registro_pagos_listado(r))
    return unified


def _aplicar_filtros_memoria(
    unified: List[dict],
    usuario_email: Optional[str],
    modulo: Optional[str],
    accion: Optional[str],
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> List[dict]:
    """Aplica filtros en memoria sobre registros unificados"""
    if usuario_email:
        unified = [u for u in unified if u.get("usuario_email") and usuario_email.lower() in u["usuario_email"].lower()]
    if modulo:
        unified = [u for u in unified if u.get("modulo") == modulo]
    if accion:
        unified = [u for u in unified if u.get("accion") == accion]
    if fecha_desde:
        if isinstance(fecha_desde, date) and not isinstance(fecha_desde, datetime):
            fecha_desde = datetime.combine(fecha_desde, datetime.min.time())
        unified = [u for u in unified if u.get("fecha") and u["fecha"] >= fecha_desde]
    if fecha_hasta:
        if isinstance(fecha_hasta, date) and not isinstance(fecha_hasta, datetime):
            fecha_hasta = datetime.combine(fecha_hasta, datetime.max.time())
        unified = [u for u in unified if u.get("fecha") and u["fecha"] <= fecha_hasta]
    return unified


def _aplicar_ordenamiento_memoria(unified: List[dict], ordenar_por: str, orden: str) -> List[dict]:
    """Aplica ordenamiento en memoria sobre registros unificados"""
    reverse = orden != "asc"
    key_map = {
        "usuario_email": lambda x: x.get("usuario_email") or "",
        "modulo": lambda x: x.get("modulo") or "",
        "accion": lambda x: x.get("accion") or "",
        "fecha": lambda x: x.get("fecha") or 0,
    }
    sort_key = key_map.get(ordenar_por, key_map["fecha"])
    unified.sort(key=sort_key, reverse=reverse)
    return unified


def _aplicar_paginacion_listado(unified: List[dict], skip: int, limit: int) -> tuple[List[dict], int, int, int]:
    """Aplica paginación y retorna datos paginados y metadatos"""
    total = len(unified)
    total_pages, current_page = _calcular_paginacion_auditoria(total, limit, skip)
    paged = unified[skip : skip + limit]
    return paged, total, total_pages, current_page


@router.get("/auditoria", response_model=AuditoriaListResponse)
def listar_auditoria(
    usuario_email: Optional[str] = Query(None, description="Filtrar por email de usuario"),
    modulo: Optional[str] = Query(None, description="Filtrar por módulo"),
    accion: Optional[str] = Query(None, description="Filtrar por acción"),
    fecha_desde: Optional[date] = Query(None, description="Filtrar desde fecha"),
    fecha_hasta: Optional[date] = Query(None, description="Filtrar hasta fecha"),
    skip: int = Query(0, ge=0, description="Registros a omitir (paginación)"),
    limit: int = Query(50, ge=1, le=200, description="Registros por página"),
    ordenar_por: str = Query("fecha", description="Campo para ordenar"),
    orden: str = Query("desc", description="Orden: asc o desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar registros de auditoría con filtros y paginación (incluye fuentes detalladas)
    from sqlalchemy import inspect
    from sqlalchemy.exc import ProgrammingError

    try:
        # Verificar si la tabla auditoria existe
        inspector = inspect(db.bind)
        tablas = inspector.get_table_names()
        tabla_auditoria_existe = "auditoria" in tablas
        tabla_prestamos_auditoria_existe = "prestamos_auditoria" in tablas
        tabla_pagos_auditoria_existe = "pagos_auditoria" in tablas

        logger.info(
            f"Tablas de auditoría - auditoria: {tabla_auditoria_existe}, prestamos_auditoria: {tabla_prestamos_auditoria_existe}, pagos_auditoria: {tabla_pagos_auditoria_existe}"
        )

        if not tabla_auditoria_existe and not tabla_prestamos_auditoria_existe and not tabla_pagos_auditoria_existe:
            # ✅ Cambiar a debug para reducir verbosidad - es un comportamiento esperado
            logger.debug("Ninguna tabla de auditoría existe en BD. Retornando lista vacía (comportamiento esperado).")
            return {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": limit,
                "total_pages": 0,
            }

        # Construir query base (auditoría general) - solo si la tabla existe
        registros_general = []
        max_to_load = min(skip + limit + 500, 5000)  # Máximo 5000 registros por tipo

        if tabla_auditoria_existe:
            try:
                query = db.query(Auditoria).options(joinedload(Auditoria.usuario))

                # Aplicar filtros
                query = _aplicar_filtros_auditoria(query, usuario_email, modulo, accion, fecha_desde, fecha_hasta)

                # Aplicar ordenamiento
                query = _aplicar_ordenamiento_auditoria(query, ordenar_por, orden)

                # OPTIMIZACIÓN: Aplicar límite ANTES de cargar para evitar cargar todos los registros
                # Cargar solo lo necesario para la paginación solicitada + un buffer para unificación

                # Ejecutar consultas con límite optimizado
                registros_general = query.limit(max_to_load).all()
                logger.info(f"Registros de auditoría general cargados: {len(registros_general)}")
            except (ProgrammingError, Exception) as e:
                logger.warning(f"Error consultando tabla auditoria: {e}, usando lista vacía")
                try:
                    db.rollback()  # ✅ Rollback para restaurar transacción después de error
                except Exception:
                    pass
                registros_general = []
        else:
            logger.info("Tabla auditoria no existe, omitiendo consulta")

        # Optimizar queries de préstamos y pagos con límite y orden
        # ✅ IMPORTANTE: Hacer rollback explícito antes de continuar si hubo error anterior
        try:
            # Verificar si la transacción está abortada y hacer rollback preventivo
            try:
                db.execute(text("SELECT 1"))
            except Exception as test_error:
                error_str = str(test_error)
                if "aborted" in error_str.lower() or "InFailedSqlTransaction" in error_str:
                    logger.warning("Transacción abortada detectada, haciendo rollback preventivo")
                    try:
                        db.rollback()
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            if tabla_prestamos_auditoria_existe:
                query_prestamos = db.query(PrestamoAuditoria).order_by(PrestamoAuditoria.fecha_cambio.desc())
                if fecha_desde:
                    query_prestamos = query_prestamos.filter(PrestamoAuditoria.fecha_cambio >= fecha_desde)
                if fecha_hasta:
                    query_prestamos = query_prestamos.filter(PrestamoAuditoria.fecha_cambio <= fecha_hasta)
                registros_prestamos = query_prestamos.limit(max_to_load).all()
                logger.info(f"Registros de prestamos_auditoria cargados: {len(registros_prestamos)}")
            else:
                registros_prestamos = []
                logger.info("Tabla prestamos_auditoria no existe, omitiendo")
        except (ProgrammingError, Exception) as e:
            logger.warning(f"Error consultando tabla prestamo_auditoria: {e}, usando lista vacía")
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass
            registros_prestamos = []

        # ✅ IMPORTANTE: Verificar transacción antes de consultar pagos
        try:
            try:
                db.execute(text("SELECT 1"))
            except Exception as test_error:
                error_str = str(test_error)
                if "aborted" in error_str.lower() or "InFailedSqlTransaction" in error_str:
                    logger.warning("Transacción abortada detectada antes de consultar pagos, haciendo rollback preventivo")
                    try:
                        db.rollback()
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            if tabla_pagos_auditoria_existe:
                query_pagos = db.query(PagoAuditoria).order_by(PagoAuditoria.fecha_cambio.desc())
                if fecha_desde:
                    query_pagos = query_pagos.filter(PagoAuditoria.fecha_cambio >= fecha_desde)
                if fecha_hasta:
                    query_pagos = query_pagos.filter(PagoAuditoria.fecha_cambio <= fecha_hasta)
                registros_pagos = query_pagos.limit(max_to_load).all()
                logger.info(f"Registros de pagos_auditoria cargados: {len(registros_pagos)}")
            else:
                registros_pagos = []
                logger.info("Tabla pagos_auditoria no existe, omitiendo")
        except (ProgrammingError, Exception) as e:
            logger.warning(f"Error consultando tabla pago_auditoria: {e}, usando lista vacía")
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass
            registros_pagos = []

        unified = _unificar_registros_auditoria_listado(registros_general, registros_prestamos, registros_pagos)
        logger.info(f"Registros unificados antes de filtros: {len(unified)}")

        unified = _aplicar_filtros_memoria(unified, usuario_email, modulo, accion, fecha_desde, fecha_hasta)
        logger.info(f"Registros unificados después de filtros: {len(unified)}")

        unified = _aplicar_ordenamiento_memoria(unified, ordenar_por, orden)

        paged, total, total_pages, current_page = _aplicar_paginacion_listado(unified, skip, limit)
        logger.info(f"Registros paginados: {len(paged)} de {total} total")

        items = [AuditoriaResponse.model_validate(i) for i in paged]

        return {
            "items": items,
            "total": total,
            "page": current_page,
            "page_size": limit,
            "total_pages": total_pages,
        }

    except Exception as e:
        logger.error(f"Error listando auditoría: {e}", exc_info=True)
        try:
            db.rollback()  # ✅ Rollback para restaurar transacción después de error
        except Exception:
            pass
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


def _generar_detalles_exportacion(usuario_email: Optional[str], modulo: Optional[str], accion: Optional[str]) -> str:
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
        query_prestamos, query_pagos = _aplicar_filtros_detalladas(
            query_prestamos, query_pagos, accion, fecha_desde, fecha_hasta
        )

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
    from sqlalchemy import inspect
    from sqlalchemy.exc import ProgrammingError

    try:
        # Verificar si la tabla auditoria existe
        inspector = inspect(db.bind)
        tablas = inspector.get_table_names()
        tabla_auditoria_existe = "auditoria" in tablas

        if not tabla_auditoria_existe:
            # ✅ Cambiar a debug para reducir verbosidad - es un comportamiento esperado
            logger.debug("Tabla 'auditoria' no existe en BD. Retornando estadísticas vacías (comportamiento esperado).")
            return AuditoriaStatsResponse(
                total_acciones=0,
                acciones_por_modulo={},
                acciones_por_usuario={},
                acciones_hoy=0,
                acciones_esta_semana=0,
                acciones_este_mes=0,
            )

        # Totales (sumando fuentes detalladas)
        try:
            total_auditoria = db.query(func.count(Auditoria.id)).scalar() or 0
        except (ProgrammingError, Exception) as e:
            total_auditoria = 0
            logger.warning(f"Error consultando tabla auditoria: {e}, usando 0")
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        try:
            total_prestamos = db.query(func.count(PrestamoAuditoria.id)).scalar() or 0
        except (ProgrammingError, Exception) as e:
            total_prestamos = 0
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        try:
            total_pagos = db.query(func.count(PagoAuditoria.id)).scalar() or 0
        except (ProgrammingError, Exception) as e:
            total_pagos = 0
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        total_acciones = total_auditoria + total_prestamos + total_pagos
        
        logger.info(f"📊 Totales calculados - Auditoría: {total_auditoria}, Préstamos: {total_prestamos}, Pagos: {total_pagos}, Total: {total_acciones}")

        # Acciones por módulo (entidad)
        acciones_por_modulo: dict[str, int] = {}
        # Calcular acciones por módulo usando GROUP BY (más eficiente)
        try:
            acciones_por_modulo_rows = db.query(Auditoria.entidad, func.count(Auditoria.id)).group_by(Auditoria.entidad).all()
            acciones_por_modulo = {
                (row[0] if row[0] is not None else "DESCONOCIDO"): (row[1] if row[1] is not None else 0)
                for row in acciones_por_modulo_rows
            }
        except (ProgrammingError, Exception) as e:
            logger.warning(f"Error consultando acciones por módulo de auditoria: {e}")
            acciones_por_modulo = {}
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        # Agregar acciones de préstamos y pagos
        try:
            acciones_por_modulo["PRESTAMOS"] = acciones_por_modulo.get("PRESTAMOS", 0) + (
                db.query(func.count(PrestamoAuditoria.id)).scalar() or 0
            )
        except (ProgrammingError, Exception) as e:
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        try:
            acciones_por_modulo["PAGOS"] = acciones_por_modulo.get("PAGOS", 0) + (
                db.query(func.count(PagoAuditoria.id)).scalar() or 0
            )
        except (ProgrammingError, Exception) as e:
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        # Acciones por usuario (email)
        try:
            acciones_por_usuario_rows = (
                db.query(User.email, func.count(Auditoria.id))
                .join(User, User.id == Auditoria.usuario_id)
                .group_by(User.email)
                .all()
            )
            acciones_por_usuario = {
                (row[0] if row[0] is not None else ""): (row[1] if row[1] is not None else 0)
                for row in acciones_por_usuario_rows
            }
        except (ProgrammingError, Exception) as e:
            logger.warning(f"Error consultando acciones por usuario de auditoria: {e}")
            acciones_por_usuario = {}
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        # Hoy / semana / mes
        from datetime import datetime, timedelta
        import pytz

        # Usar zona horaria de Venezuela (America/Caracas) para cálculos
        tz_caracas = pytz.timezone('America/Caracas')
        now_caracas = datetime.now(tz_caracas)
        
        # Crear fechas de inicio en la zona horaria local
        inicio_hoy_caracas = datetime(now_caracas.year, now_caracas.month, now_caracas.day, tzinfo=tz_caracas)
        inicio_semana_caracas = inicio_hoy_caracas - timedelta(days=6)
        inicio_mes_caracas = datetime(now_caracas.year, now_caracas.month, 1, tzinfo=tz_caracas)
        
        # Convertir a UTC para comparar con fechas de la BD (que probablemente están en UTC)
        # Las fechas en PostgreSQL con timezone=True se almacenan en UTC
        inicio_hoy = inicio_hoy_caracas.astimezone(pytz.UTC).replace(tzinfo=None)
        inicio_semana = inicio_semana_caracas.astimezone(pytz.UTC).replace(tzinfo=None)
        inicio_mes = inicio_mes_caracas.astimezone(pytz.UTC).replace(tzinfo=None)
        
        logger.info(f"📅 Calculando estadísticas - Hoy (UTC): {inicio_hoy}, Semana (UTC): {inicio_semana}, Mes (UTC): {inicio_mes}")

        # Calcular acciones por período de forma segura
        try:
            acciones_hoy_aud = db.query(func.count(Auditoria.id)).filter(Auditoria.fecha >= inicio_hoy).scalar() or 0
        except (ProgrammingError, Exception) as e:
            acciones_hoy_aud = 0
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        try:
            acciones_hoy_prest = (
                db.query(func.count(PrestamoAuditoria.id)).filter(PrestamoAuditoria.fecha_cambio >= inicio_hoy).scalar() or 0
            )
        except (ProgrammingError, Exception) as e:
            acciones_hoy_prest = 0
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        try:
            acciones_hoy_pagos = (
                db.query(func.count(PagoAuditoria.id)).filter(PagoAuditoria.fecha_cambio >= inicio_hoy).scalar() or 0
            )
        except (ProgrammingError, Exception) as e:
            acciones_hoy_pagos = 0
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        acciones_hoy = acciones_hoy_aud + acciones_hoy_prest + acciones_hoy_pagos

        try:
            acciones_semana_aud = db.query(func.count(Auditoria.id)).filter(Auditoria.fecha >= inicio_semana).scalar() or 0
        except (ProgrammingError, Exception) as e:
            acciones_semana_aud = 0
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        try:
            acciones_semana_prest = (
                db.query(func.count(PrestamoAuditoria.id)).filter(PrestamoAuditoria.fecha_cambio >= inicio_semana).scalar()
                or 0
            )
        except (ProgrammingError, Exception) as e:
            acciones_semana_prest = 0
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        try:
            acciones_semana_pagos = (
                db.query(func.count(PagoAuditoria.id)).filter(PagoAuditoria.fecha_cambio >= inicio_semana).scalar() or 0
            )
        except (ProgrammingError, Exception) as e:
            acciones_semana_pagos = 0
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        acciones_esta_semana = acciones_semana_aud + acciones_semana_prest + acciones_semana_pagos

        try:
            acciones_mes_aud = db.query(func.count(Auditoria.id)).filter(Auditoria.fecha >= inicio_mes).scalar() or 0
        except (ProgrammingError, Exception) as e:
            acciones_mes_aud = 0
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        try:
            acciones_mes_prest = (
                db.query(func.count(PrestamoAuditoria.id)).filter(PrestamoAuditoria.fecha_cambio >= inicio_mes).scalar() or 0
            )
        except (ProgrammingError, Exception) as e:
            acciones_mes_prest = 0
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        try:
            acciones_mes_pagos = (
                db.query(func.count(PagoAuditoria.id)).filter(PagoAuditoria.fecha_cambio >= inicio_mes).scalar() or 0
            )
        except (ProgrammingError, Exception) as e:
            acciones_mes_pagos = 0
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass

        acciones_este_mes = acciones_mes_aud + acciones_mes_prest + acciones_mes_pagos
        
        logger.info(f"📈 Estadísticas por período - Hoy: {acciones_hoy}, Semana: {acciones_esta_semana}, Mes: {acciones_este_mes}")

        stats_response = AuditoriaStatsResponse(
            total_acciones=total_acciones,
            acciones_por_modulo=acciones_por_modulo,
            acciones_por_usuario=acciones_por_usuario,
            acciones_hoy=acciones_hoy,
            acciones_esta_semana=acciones_esta_semana,
            acciones_este_mes=acciones_este_mes,
        )
        
        logger.info(f"✅ Estadísticas generadas exitosamente: {stats_response.model_dump()}")
        return stats_response
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de auditoría: {e}", exc_info=True)
        try:
            db.rollback()  # ✅ Rollback para restaurar transacción después de error
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


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
