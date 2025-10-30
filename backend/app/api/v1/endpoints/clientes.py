import logging
from datetime import datetime
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


@router.get("/", response_model=dict)
def listar_clientes(
    page: int = Query(1, ge=1, description="Numero de pagina"),
    per_page: int = Query(20, ge=1, le=1000, description="Tamano de pagina"),
    # Busqueda de texto
    search: Optional[str] = Query(
        None, description="Buscar por nombre, cedula o telefono"
    ),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar clientes con paginacion y filtros
    try:
        logger.info(f"Listar clientes - Usuario: {current_user.email}")

        # Query base
        query = db.query(Cliente)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Cliente.nombres.ilike(search_pattern),
                    Cliente.cedula.ilike(search_pattern),
                    Cliente.telefono.ilike(search_pattern),
                )
            )

        if estado:
            query = query.filter(Cliente.estado == estado)

        # Ordenamiento por fecha de registro descendente (más recientes primero)
        query = query.order_by(Cliente.fecha_registro.desc())

        # Contar total
        total = query.count()

        # Paginacion
        offset = (page - 1) * per_page
        clientes = query.offset(offset).limit(per_page).all()

        # Serializacion segura
        clientes_dict = []
        for cliente in clientes:
            try:
                cliente_data = ClienteResponse.model_validate(cliente).model_dump()
                clientes_dict.append(cliente_data)
            except Exception as e:
                logger.error(f"Error serializando cliente {cliente.id}: {e}")
                continue

        # Calcular paginas
        total_pages = (total + per_page - 1) // per_page

        return {
            "clientes": clientes_dict,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.error(f"Error en listar_clientes: {e}")
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


@router.post("/", response_model=None)
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
        existente_cedula = (
            db.query(Cliente).filter(Cliente.cedula == cliente_data.cedula).first()
        )
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
            existente_nombre = (
                db.query(Cliente)
                .filter(func.lower(Cliente.nombres) == nombres_normalizados)
                .first()
            )
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

        # Sincronizar estado y activo (crear siempre con ACTIVO=True)
        cliente_dict["estado"] = "ACTIVO"
        cliente_dict["activo"] = True
        cliente_dict["usuario_registro"] = current_user.email

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
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
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

        # ✅ Validar: NO permitir actualizar si queda con cédula O nombre duplicados de OTRO cliente
        # Solo validar si se está actualizando cédula o nombres
        if "cedula" in update_data or "nombres" in update_data:
            nueva_cedula = update_data.get("cedula", cliente.cedula)
            nuevos_nombres = update_data.get("nombres", cliente.nombres)

            # 1) Bloquear por cédula duplicada en otro cliente
            otro_con_misma_cedula = (
                db.query(Cliente)
                .filter(Cliente.cedula == nueva_cedula, Cliente.id != cliente_id)
                .first()
            )
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

            # 2) Bloquear por nombre completo duplicado en otro cliente (case-insensitive)
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
