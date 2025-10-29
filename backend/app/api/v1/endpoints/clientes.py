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

        # ✅ Validar: NO permitir misma cédula + mismo nombre+apellido (nombres unificados)
        # Normalizar nombres para comparación (trim y case-insensitive)
        nombres_normalizados = cliente_data.nombres.strip()

        # Buscar cliente existente con misma cédula
        cliente_misma_cedula = (
            db.query(Cliente).filter(Cliente.cedula == cliente_data.cedula).all()
        )

        # Verificar si alguno de los clientes con la misma cédula tiene el mismo nombre
        for cliente_existente in cliente_misma_cedula:
            nombres_existentes_normalizados = (
                cliente_existente.nombres.strip() if cliente_existente.nombres else ""
            )

            # Comparación case-insensitive y normalizada
            if nombres_existentes_normalizados.lower() == nombres_normalizados.lower():
                # NO PERMITIR: misma cédula + mismo nombre+apellido
                logger.warning(
                    f"❌ Intento de crear cliente duplicado - Cédula: {cliente_data.cedula}, "
                    f"Nombres: {cliente_data.nombres} (ya existe ID: {cliente_existente.id})"
                )
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"No se puede crear un cliente con la misma cédula ({cliente_data.cedula}) "
                        f"y el mismo nombre ({cliente_data.nombres}). "
                        f"Ya existe un cliente (ID: {cliente_existente.id}) con estos datos."
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

        # ✅ Validar: NO permitir actualizar a misma cédula + mismo nombre+apellido de OTRO cliente
        # Solo validar si se está actualizando cédula o nombres
        if "cedula" in update_data or "nombres" in update_data:
            nueva_cedula = update_data.get("cedula", cliente.cedula)
            nuevos_nombres = update_data.get("nombres", cliente.nombres)

            if nuevos_nombres:
                nuevos_nombres_normalizados = nuevos_nombres.strip()

                # Buscar otros clientes con la misma cédula (excluyendo el actual)
                otros_clientes_misma_cedula = (
                    db.query(Cliente)
                    .filter(
                        Cliente.cedula == nueva_cedula,
                        Cliente.id != cliente_id,  # Excluir el cliente actual
                    )
                    .all()
                )

                # Verificar si algún otro cliente con la misma cédula tiene el mismo nombre
                for otro_cliente in otros_clientes_misma_cedula:
                    nombres_existentes_normalizados = (
                        otro_cliente.nombres.strip() if otro_cliente.nombres else ""
                    )

                    # Comparación case-insensitive y normalizada
                    if (
                        nombres_existentes_normalizados.lower()
                        == nuevos_nombres_normalizados.lower()
                    ):
                        # NO PERMITIR: misma cédula + mismo nombre+apellido en otro cliente
                        logger.warning(
                            f"❌ Intento de actualizar cliente {cliente_id} a duplicado - "
                            f"Cédula: {nueva_cedula}, Nombres: {nuevos_nombres} "
                            f"(ya existe ID: {otro_cliente.id})"
                        )
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"No se puede actualizar el cliente a tener la misma cédula ({nueva_cedula}) "
                                f"y el mismo nombre ({nuevos_nombres}) que otro cliente existente (ID: {otro_cliente.id})."
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
