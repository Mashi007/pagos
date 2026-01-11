import logging
import re
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.user import User
from app.schemas.cliente import ClienteCreate, ClienteResponse, ClienteUpdate

# Endpoints de gestion de clientes - VERSION CON AUDITORIA AUTOMATICA
# Sistema completo de gestion de clientes con validaciones y auditoria
# Datos del dashboard ahora son calculados desde la base de datos en tiempo real


router = APIRouter()
logger = logging.getLogger(__name__)


def _aplicar_filtro_busqueda(query, search: Optional[str]):
    """Aplica filtro de búsqueda general"""
    if not search:
        return query
    search_pattern = f"%{search}%"
    return query.filter(
        or_(
            Cliente.nombres.ilike(search_pattern),
            Cliente.cedula.ilike(search_pattern),
            Cliente.telefono.ilike(search_pattern),
        )
    )


def _aplicar_filtros_especificos(
    query,
    estado: Optional[str],
    cedula: Optional[str],
    email: Optional[str],
    telefono: Optional[str],
    ocupacion: Optional[str],
    usuario_registro: Optional[str],
):
    """Aplica filtros específicos a la query"""
    if estado:
        query = query.filter(Cliente.estado == estado)
    if cedula:
        query = query.filter(Cliente.cedula.ilike(f"%{cedula}%"))
    if email:
        query = query.filter(Cliente.email.ilike(f"%{email}%"))
    if telefono:
        query = query.filter(Cliente.telefono.ilike(f"%{telefono}%"))
    if ocupacion:
        query = query.filter(Cliente.ocupacion.ilike(f"%{ocupacion}%"))
    if usuario_registro:
        query = query.filter(Cliente.usuario_registro.ilike(f"%{usuario_registro}%"))
    return query


def _aplicar_filtros_fecha(query, fecha_desde: Optional[str], fecha_hasta: Optional[str]):
    """Aplica filtros de fecha de registro"""
    if fecha_desde:
        try:
            fecha_desde_obj = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
            query = query.filter(func.date(Cliente.fecha_registro) >= fecha_desde_obj)
        except ValueError:
            logger.warning(f"Fecha desde inválida: {fecha_desde}")
    if fecha_hasta:
        try:
            fecha_hasta_obj = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
            fecha_hasta_obj = fecha_hasta_obj + timedelta(days=1)
            query = query.filter(func.date(Cliente.fecha_registro) < fecha_hasta_obj)
        except ValueError:
            logger.warning(f"Fecha hasta inválida: {fecha_hasta}")
    return query


def _serializar_clientes(clientes):
    """Serializa una lista de clientes de forma segura"""
    clientes_dict = []
    for cliente in clientes:
        try:
            cliente_data = ClienteResponse.model_validate(cliente).model_dump()
            clientes_dict.append(cliente_data)
        except Exception as e:
            logger.error(f"Error serializando cliente {cliente.id}: {e}")
            continue
    return clientes_dict


@router.get("", response_model=dict)
def listar_clientes(
    page: int = Query(1, ge=1, description="Numero de pagina"),
    per_page: int = Query(20, ge=1, le=5000, description="Tamano de pagina"),
    # Busqueda de texto
    search: Optional[str] = Query(None, description="Buscar por nombre, cedula o telefono"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    cedula: Optional[str] = Query(None, description="Filtrar por cédula exacta"),
    email: Optional[str] = Query(None, description="Filtrar por email"),
    telefono: Optional[str] = Query(None, description="Filtrar por teléfono"),
    ocupacion: Optional[str] = Query(None, description="Filtrar por ocupación"),
    usuario_registro: Optional[str] = Query(None, description="Filtrar por usuario que registró"),
    fecha_desde: Optional[str] = Query(None, description="Fecha de registro desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha de registro hasta (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar clientes con paginacion y filtros
    import time

    start_time = time.time()
    try:
        logger.info(f"Listar clientes - Usuario: {current_user.email}, page={page}, per_page={per_page}")

        # Query base
        query = db.query(Cliente)

        # Aplicar filtros
        query = _aplicar_filtro_busqueda(query, search)
        query = _aplicar_filtros_especificos(query, estado, cedula, email, telefono, ocupacion, usuario_registro)
        query = _aplicar_filtros_fecha(query, fecha_desde, fecha_hasta)

        # Ordenamiento por fecha de registro descendente (más recientes primero)
        query = query.order_by(Cliente.fecha_registro.desc())

        # ✅ OPTIMIZACIÓN: Solo contar si realmente se necesita (primera página o cuando hay pocos resultados)
        # Para páginas grandes (per_page > 500), usar estimación rápida
        if per_page > 500:
            # Para páginas muy grandes, hacer count solo si es página 1
            if page == 1:
                start_count = time.time()
                total = query.count()
                count_time = int((time.time() - start_count) * 1000)
                logger.info(f"📊 [clientes] Count completado en {count_time}ms: {total} total")
            else:
                # Para páginas > 1, estimar total basado en resultados previos
                # Esto evita hacer count() en cada página
                total = None  # No calculamos total para páginas grandes
        else:
            # Para páginas normales, hacer count siempre
            start_count = time.time()
            total = query.count()
            count_time = int((time.time() - start_count) * 1000)
            logger.info(f"📊 [clientes] Count completado en {count_time}ms: {total} total")

        # Paginacion
        offset = (page - 1) * per_page
        start_query = time.time()
        clientes = query.offset(offset).limit(per_page).all()
        query_time = int((time.time() - start_query) * 1000)
        logger.info(f"📊 [clientes] Query completada en {query_time}ms: {len(clientes)} registros")

        # Serializacion segura
        start_serialize = time.time()
        clientes_dict = _serializar_clientes(clientes)
        serialize_time = int((time.time() - start_serialize) * 1000)
        logger.info(f"📊 [clientes] Serialización completada en {serialize_time}ms")

        # Calcular paginas
        if total is not None:
            total_pages = (total + per_page - 1) // per_page
        else:
            # Si no tenemos total, estimar basado en si hay más resultados
            total_pages = page + 1 if len(clientes) == per_page else page

        total_time = int((time.time() - start_time) * 1000)
        count_time_str = f"{count_time}ms" if total is not None else "N/A"
        logger.info(
            f"⏱️ [clientes] Tiempo total: {total_time}ms (count: {count_time_str}, query: {query_time}ms, serialize: {serialize_time}ms)"
        )

        return {
            "clientes": clientes_dict,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.error(f"Error en listar_clientes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/stats")
def obtener_estadisticas_clientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener estadísticas de clientes directamente desde la BD
    try:
        logger.info(f"Obteniendo estadísticas de clientes - Usuario: {current_user.email}")

        # Contar total de clientes
        total = db.query(Cliente).count()

        # Contar por estado
        activos = db.query(Cliente).filter(Cliente.estado == "ACTIVO").count()

        inactivos = db.query(Cliente).filter(Cliente.estado == "INACTIVO").count()

        finalizados = db.query(Cliente).filter(Cliente.estado == "FINALIZADO").count()

        return {
            "total": total,
            "activos": activos,
            "inactivos": inactivos,
            "finalizados": finalizados,
        }

    except Exception as e:
        logger.error(f"Error en obtener_estadisticas_clientes: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/embudo/estadisticas")
def obtener_estadisticas_embudo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener estadísticas del embudo de clientes basadas en estados de préstamos"""
    try:
        logger.info(f"Obteniendo estadísticas del embudo - Usuario: {current_user.email}")

        # Total de clientes
        total = db.query(Cliente).count()

        # Clientes con préstamos RECHAZADOS
        clientes_rechazados = (
            db.query(func.count(func.distinct(Prestamo.cliente_id))).filter(Prestamo.estado == "RECHAZADO").scalar() or 0
        )

        # Clientes con préstamos APROBADOS
        clientes_aprobados = (
            db.query(func.count(func.distinct(Prestamo.cliente_id))).filter(Prestamo.estado == "APROBADO").scalar() or 0
        )

        # Clientes con préstamos en evaluación (EN_REVISION o DRAFT)
        clientes_evaluacion = (
            db.query(func.count(func.distinct(Prestamo.cliente_id)))
            .filter(Prestamo.estado.in_(["EN_REVISION", "DRAFT"]))
            .scalar()
            or 0
        )

        # Prospectos: todos los clientes que no están en los otros estados
        # Es decir, clientes que no tienen préstamos o tienen préstamos en otros estados
        clientes_con_prestamos = (
            db.query(func.count(func.distinct(Prestamo.cliente_id)))
            .filter(Prestamo.estado.in_(["RECHAZADO", "APROBADO", "EN_REVISION", "DRAFT"]))
            .scalar()
            or 0
        )
        prospectos = total - clientes_con_prestamos

        return {
            "total": total,
            "prospectos": max(0, prospectos),  # Asegurar que no sea negativo
            "evaluacion": clientes_evaluacion,
            "aprobados": clientes_aprobados,
            "rechazados": clientes_rechazados,
        }

    except Exception as e:
        logger.error(f"Error en obtener_estadisticas_embudo: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener cliente por ID
    try:
        logger.info(f"Obteniendo cliente {cliente_id}")
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return ClienteResponse.model_validate(cliente)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en obtener_cliente: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("", response_model=None)
def crear_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Crear nuevo cliente
    try:
        logger.info(f"Crear cliente - Usuario: {current_user.email}")

        # ✅ Validar: NO permitir crear si existe misma cédula O mismo nombre+apellido
        # Normalizar nombres para comparación (trim y case-insensitive)
        nombres_normalizados = (cliente_data.nombres or "").strip().lower()

        # 1) Bloquear por cédula duplicada
        existente_cedula = db.query(Cliente).filter(Cliente.cedula == cliente_data.cedula).first()
        if existente_cedula:
            logger.warning(
                f"❌ Intento de crear cliente con cédula ya registrada: {cliente_data.cedula} "
                f"(ID existente: {existente_cedula.id})"
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No se puede crear un cliente con la misma cédula ({cliente_data.cedula}). "
                    f"Ya existe un cliente (ID: {existente_cedula.id}) con esa cédula."
                ),
            )

        # 2) Bloquear por nombre completo duplicado (case-insensitive)
        if nombres_normalizados:
            existente_nombre = db.query(Cliente).filter(func.lower(Cliente.nombres) == nombres_normalizados).first()
            if existente_nombre:
                logger.warning(
                    f"❌ Intento de crear cliente con nombre ya registrado: {cliente_data.nombres} "
                    f"(ID existente: {existente_nombre.id})"
                )
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"No se puede crear un cliente con el mismo nombre completo "
                        f"({cliente_data.nombres}). Ya existe un cliente (ID: {existente_nombre.id}) "
                        f"con ese nombre."
                    ),
                )

        # Preparar datos
        cliente_dict = cliente_data.model_dump()

        # Sincronizar estado y activo (crear siempre con ACTIVO=True si no se proporciona)
        if not cliente_dict.get("estado"):
            cliente_dict["estado"] = "ACTIVO"
        cliente_dict["activo"] = cliente_dict.get("activo", True)

        # Usuario que registra el cliente
        cliente_dict["usuario_registro"] = current_user.email

        # Asegurar normalización (aunque el trigger de BD también lo hará)
        if "email" in cliente_dict and cliente_dict["email"]:
            cliente_dict["email"] = cliente_dict["email"].lower().strip()
        if "cedula" in cliente_dict and cliente_dict["cedula"]:
            cliente_dict["cedula"] = re.sub(r"[-\s]", "", cliente_dict["cedula"].strip())

        # Crear nuevo cliente
        nuevo_cliente = Cliente(**cliente_dict)

        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)

        return ClienteResponse.model_validate(nuevo_cliente)

    except Exception as e:
        import traceback

        error_detail = f"{str(e)}: {traceback.format_exc()}"
        logger.error(f"Error en crear_cliente: {error_detail}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


def _validar_duplicados_actualizacion(db: Session, cliente_id: int, update_data: dict, cliente: Cliente):
    """Valida que no haya duplicados al actualizar cédula o nombres"""
    if "cedula" not in update_data and "nombres" not in update_data:
        return

    nueva_cedula = update_data.get("cedula", cliente.cedula)
    nuevos_nombres = update_data.get("nombres", cliente.nombres)

    # Validar cédula duplicada
    otro_con_misma_cedula = db.query(Cliente).filter(Cliente.cedula == nueva_cedula, Cliente.id != cliente_id).first()
    if otro_con_misma_cedula:
        logger.warning(
            f"❌ Intento de actualizar cliente {cliente_id} a cédula duplicada: {nueva_cedula} "
            f"(ya existe ID: {otro_con_misma_cedula.id})"
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se puede actualizar el cliente para tener la misma cédula "
                f"({nueva_cedula}) que otro cliente existente (ID: {otro_con_misma_cedula.id})."
            ),
        )

    # Validar nombre duplicado
    if nuevos_nombres:
        nuevos_nombres_normalizados = nuevos_nombres.strip().lower()
        otro_con_mismo_nombre = (
            db.query(Cliente)
            .filter(
                func.lower(Cliente.nombres) == nuevos_nombres_normalizados,
                Cliente.id != cliente_id,
            )
            .first()
        )
        if otro_con_mismo_nombre:
            logger.warning(
                f"❌ Intento de actualizar cliente {cliente_id} a nombre duplicado: {nuevos_nombres} "
                f"(ya existe ID: {otro_con_mismo_nombre.id})"
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No se puede actualizar el cliente para tener el mismo nombre completo "
                    f"({nuevos_nombres}) que otro cliente existente (ID: {otro_con_mismo_nombre.id})."
                ),
            )


@router.put("/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    cliente_data: ClienteUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Actualizar cliente
    try:
        logger.info(f"Actualizando cliente {cliente_id}")

        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        update_data = cliente_data.model_dump(exclude_unset=True)

        # Validar duplicados
        _validar_duplicados_actualizacion(db, cliente_id, update_data, cliente)

        # Sincronizar estado y activo SI se actualiza el estado
        if "estado" in update_data:
            nuevo_estado = update_data["estado"]
            if nuevo_estado == "ACTIVO":
                update_data["activo"] = True
            elif nuevo_estado in ["INACTIVO", "FINALIZADO"]:
                update_data["activo"] = False

        # Aplicar actualizaciones
        for field, value in update_data.items():
            if hasattr(cliente, field):
                setattr(cliente, field, value)

        # Actualizar fecha_actualizacion manualmente
        cliente.fecha_actualizacion = datetime.utcnow()

        db.commit()
        db.refresh(cliente)

        return ClienteResponse.model_validate(cliente)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en actualizar_cliente: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.delete("/{cliente_id}")
def eliminar_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eliminar cliente (hard delete)
    try:
        logger.info(f"Eliminando cliente {cliente_id}")

        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Hard delete - eliminar fisicamente de la BD
        db.delete(cliente)
        db.commit()

        return {"message": "Cliente eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en eliminar_cliente: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# =====================================================
# ENDPOINTS PARA VALORES POR DEFECTO
# =====================================================


@router.get("/valores-por-defecto", response_model=dict)
def listar_clientes_valores_por_defecto(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista clientes que tienen valores por defecto que necesitan ser corregidos.

    Valores por defecto detectados:
    - Email con 'noemail' o '@noemail'
    - Teléfono con '999999999'
    - Dirección con 'Actualizar'
    - Ocupación con 'Actualizar'
    - Notas con 'NA' o 'No hay observacion'
    """
    try:
        # Buscar clientes con valores por defecto
        query = db.query(Cliente).filter(
            or_(
                Cliente.email.ilike("%noemail%"),
                Cliente.email.ilike("%@noemail%"),
                Cliente.telefono.ilike("%999999999%"),
                Cliente.direccion.ilike("%Actualizar%"),
                Cliente.ocupacion.ilike("%Actualizar%"),
                Cliente.notas.in_(["NA", "No hay observacion", "No existe observaciones"]),
            )
        )

        total = query.count()

        # Paginación
        offset = (page - 1) * per_page
        clientes = query.order_by(Cliente.fecha_registro.desc()).offset(offset).limit(per_page).all()

        # Serializar clientes
        clientes_dict = _serializar_clientes(clientes)

        # Calcular total de páginas
        total_pages = (total + per_page - 1) // per_page

        return {
            "items": clientes_dict,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    except Exception as e:
        logger.error(f"Error en listar_clientes_valores_por_defecto: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/valores-por-defecto/exportar")
def exportar_clientes_valores_por_defecto(
    formato: str = Query("csv", pattern="^(csv|excel)$", description="Formato de exportación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exporta clientes con valores por defecto en formato CSV o Excel.
    """
    try:
        import csv
        import io
        from datetime import datetime

        # Buscar todos los clientes con valores por defecto
        clientes = (
            db.query(Cliente)
            .filter(
                or_(
                    Cliente.email.ilike("%noemail%"),
                    Cliente.email.ilike("%@noemail%"),
                    Cliente.telefono.ilike("%999999999%"),
                    Cliente.direccion.ilike("%Actualizar%"),
                    Cliente.ocupacion.ilike("%Actualizar%"),
                    Cliente.notas.in_(["NA", "No hay observacion", "No existe observaciones"]),
                )
            )
            .order_by(Cliente.fecha_registro.desc())
            .all()
        )

        if formato == "csv":
            # Generar CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # Encabezados
            writer.writerow(
                ["ID", "Cédula", "Nombres", "Teléfono", "Email", "Dirección", "Ocupación", "Estado", "Fecha Registro", "Notas"]
            )

            # Datos
            for cliente in clientes:
                writer.writerow(
                    [
                        cliente.id,
                        cliente.cedula,
                        cliente.nombres,
                        cliente.telefono,
                        cliente.email,
                        cliente.direccion,
                        cliente.ocupacion,
                        cliente.estado,
                        cliente.fecha_registro.strftime("%Y-%m-%d %H:%M:%S") if cliente.fecha_registro else "",
                        cliente.notas,
                    ]
                )

            from fastapi.responses import Response

            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=clientes_valores_por_defecto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                },
            )

        elif formato == "excel":
            # Generar Excel
            import pandas as pd

            data = []
            for cliente in clientes:
                data.append(
                    {
                        "ID": cliente.id,
                        "Cédula": cliente.cedula,
                        "Nombres": cliente.nombres,
                        "Teléfono": cliente.telefono,
                        "Email": cliente.email,
                        "Dirección": cliente.direccion,
                        "Ocupación": cliente.ocupacion,
                        "Estado": cliente.estado,
                        "Fecha Registro": (
                            cliente.fecha_registro.strftime("%Y-%m-%d %H:%M:%S") if cliente.fecha_registro else ""
                        ),
                        "Notas": cliente.notas,
                    }
                )

            df = pd.DataFrame(data)
            output = io.BytesIO()
            df.to_excel(output, index=False, engine="openpyxl")
            output.seek(0)

            from fastapi.responses import Response

            return Response(
                content=output.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=clientes_valores_por_defecto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                },
            )

    except Exception as e:
        logger.error(f"Error en exportar_clientes_valores_por_defecto: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/actualizar-lote", response_model=dict)
def actualizar_clientes_lote(
    actualizaciones: list,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Actualiza múltiples clientes en lote.

    Formato esperado:
    [
        {"id": 1, "email": "nuevo@email.com", "telefono": "+581234567890"},
        {"id": 2, "direccion": "Nueva dirección", "ocupacion": "Nueva ocupación"},
    ]
    """
    try:
        actualizados = 0
        errores = []

        for actualizacion in actualizaciones:
            cliente_id = actualizacion.get("id")
            if not cliente_id:
                errores.append({"id": None, "error": "ID de cliente requerido"})
                continue

            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if not cliente:
                errores.append({"id": cliente_id, "error": "Cliente no encontrado"})
                continue

            try:
                # Actualizar campos permitidos
                campos_permitidos = ["email", "telefono", "direccion", "ocupacion", "notas", "estado", "activo"]
                for campo, valor in actualizacion.items():
                    if campo != "id" and campo in campos_permitidos and valor is not None:
                        setattr(cliente, campo, valor)

                # Normalizar email y cédula (el trigger de BD también lo hará, pero lo hacemos aquí también)
                if hasattr(cliente, "email") and cliente.email:
                    cliente.email = cliente.email.lower().strip()

                db.commit()
                actualizados += 1

            except Exception as e:
                db.rollback()
                errores.append({"id": cliente_id, "error": str(e)})

        return {
            "actualizados": actualizados,
            "errores": errores,
            "total_procesados": len(actualizaciones),
        }

    except Exception as e:
        logger.error(f"Error en actualizar_clientes_lote: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
