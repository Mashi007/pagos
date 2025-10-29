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

        # ✅ Verificar si ya existe un cliente con la misma cédula
        cliente_existente = (
            db.query(Cliente).filter(Cliente.cedula == cliente_data.cedula).first()
        )

        if cliente_existente:
            # Verificar si el usuario confirmó explícitamente el duplicado
            if not cliente_data.confirm_duplicate:
                # Buscar todos los préstamos de este cliente
                prestamos_cliente = (
                    db.query(Prestamo)
                    .filter(Prestamo.cedula == cliente_data.cedula)
                    .all()
                )

                # Preparar información de préstamos con estadísticas de cuotas
                prestamos_info = []
                for prestamo in prestamos_cliente:
                    # Contar cuotas por estado
                    cuotas_pagadas = (
                        db.query(func.count(Cuota.id))
                        .filter(
                            Cuota.prestamo_id == prestamo.id, Cuota.estado == "PAGADO"
                        )
                        .scalar()
                        or 0
                    )

                    cuotas_pendientes = (
                        db.query(func.count(Cuota.id))
                        .filter(
                            Cuota.prestamo_id == prestamo.id,
                            Cuota.estado.in_(["PENDIENTE", "ATRASADO", "PARCIAL"]),
                        )
                        .scalar()
                        or 0
                    )

                    # Determinar estado resumido
                    if cuotas_pendientes == 0:
                        estado_resumen = "AL DÍA"
                    elif cuotas_pagadas > 0 and cuotas_pendientes > 0:
                        estado_resumen = "EN PAGO"
                    else:
                        estado_resumen = prestamo.estado

                    prestamos_info.append(
                        {
                            "id": prestamo.id,
                            "monto_financiamiento": float(
                                prestamo.total_financiamiento
                            ),
                            "estado": estado_resumen,
                            "modalidad_pago": prestamo.modalidad_pago,
                            "fecha_registro": (
                                prestamo.fecha_registro.isoformat()
                                if prestamo.fecha_registro
                                else None
                            ),
                            "cuotas_pagadas": cuotas_pagadas,
                            "cuotas_pendientes": cuotas_pendientes,
                        }
                    )

                # Retornar error 409 con datos del cliente existente Y sus préstamos
                logger.info(
                    f"Cliente duplicado detectado - Cédula: {cliente_data.cedula}, Préstamos: {len(prestamos_info)}"
                )

                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": {
                            "error": "CLIENTE_DUPLICADO",
                            "message": f"Ya existe un cliente con la cédula {cliente_data.cedula}",
                            "cedula": cliente_data.cedula,
                            "cliente_existente": {
                                "id": cliente_existente.id,
                                "cedula": cliente_existente.cedula,
                                "nombres": cliente_existente.nombres,
                                "telefono": cliente_existente.telefono,
                                "email": cliente_existente.email,
                                "fecha_registro": cliente_existente.fecha_registro.isoformat(),
                            },
                            "prestamos": prestamos_info,
                        }
                    },
                )
            else:
                # Usuario confirmó explícitamente - permitir crear duplicado
                logger.info(
                    f"Usuario confirmó cliente duplicado - Cédula: {cliente_data.cedula}"
                )

        # Preparar datos
        cliente_dict = cliente_data.model_dump(exclude={"confirm_duplicate"})

        # Proporcionar valores por defecto para campos opcionales
        cliente_dict["modelo_vehiculo"] = cliente_dict.get("modelo_vehiculo") or "Por Definir"
        cliente_dict["concesionario"] = cliente_dict.get("concesionario") or "Por Definir"
        cliente_dict["analista"] = cliente_dict.get("analista") or "Por Definir"

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
