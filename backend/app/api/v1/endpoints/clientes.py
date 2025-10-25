"""
Endpoints de gestión de clientes - VERSIÓN CON AUDITORÍA AUTOMÁTICA
Sistema completo de gestión de clientes con validaciones y auditoría
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.cliente import Cliente
from app.models.user import User
from app.schemas.cliente import (
    ClienteCreate,
    ClienteCreateWithConfirmation,
    ClienteResponse,
    ClienteUpdate,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=dict)
@router.get("/", response_model=dict)
def listar_clientes(
    # Paginación
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=1000, description="Tamaño de página"),
    # Búsqueda de texto
    search: Optional[str] = Query(
        None, description="Buscar en nombre, cédula o móvil"
    ),
    # Filtros específicos
    estado: Optional[str] = Query(
        None, description="ACTIVO, INACTIVO, FINALIZADO"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📋 Listar clientes con paginación y filtros
    """
    try:
        logger.info(f"Listar clientes - Usuario: {current_user.email}")

        # Query base
        query = db.query(Cliente)

        # Aplicar filtros
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Cliente.nombres.ilike(search_pattern),
                    Cliente.apellidos.ilike(search_pattern),
                    Cliente.cedula.ilike(search_pattern),
                    Cliente.telefono.ilike(search_pattern),
                )
            )

        if estado:
            query = query.filter(Cliente.estado == estado)

        # Ordenamiento
        query = query.order_by(Cliente.id.desc())

        # Contar total
        total = query.count()

        # Paginación
        offset = (page - 1) * per_page
        clientes = query.offset(offset).limit(per_page).all()

        # Serialización segura
        clientes_dict = []
        for cliente in clientes:
            try:
                cliente_data = {
                    "id": cliente.id,
                    "cedula": cliente.cedula,
                    "nombres": cliente.nombres,
                    "apellidos": cliente.apellidos,
                    "telefono": cliente.telefono,
                    "email": cliente.email,
                    "direccion": cliente.direccion,
                    "fecha_nacimiento": (
                        cliente.fecha_nacimiento.isoformat()
                        if cliente.fecha_nacimiento
                        else None
                    ),
                    "ocupacion": cliente.ocupacion,
                    "modelo_vehiculo": cliente.modelo_vehiculo,
                    "concesionario": cliente.concesionario,
                    "analista": cliente.analista,
                    "estado": cliente.estado,
                    "activo": cliente.activo,
                    "fecha_registro": (
                        cliente.fecha_registro.isoformat()
                        if cliente.fecha_registro
                        else None
                    ),
                    "fecha_actualizacion": (
                        cliente.fecha_actualizacion.isoformat()
                        if cliente.fecha_actualizacion
                        else None
                    ),
                    "usuario_registro": cliente.usuario_registro,
                    "notas": cliente.notas,
                }
                clientes_dict.append(cliente_data)
            except Exception as e:
                logger.error(f"Error serializando cliente {cliente.id}: {e}")
                continue

        # Calcular páginas
        total_pages = (total + per_page - 1) // per_page

        return {
            "clientes": clientes_dict,
            "paginacion": {
                "total": total,
                "pagina_actual": page,
                "por_pagina": per_page,
                "total_paginas": total_pages,
                "tiene_siguiente": page < total_pages,
                "tiene_anterior": page > 1,
            },
        }
    except Exception as e:
        logger.error(f"Error en listar_clientes: {e}")
        raise HTTPException(
            status_code=500, detail="Error interno del servidor"
        )


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    👤 Obtener cliente por ID
    """
    try:
        logger.info(
            f"Obtener cliente {cliente_id} - Usuario: {current_user.email}"
        )
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=404, detail="Cliente no encontrado"
            )
        return ClienteResponse.model_validate(cliente)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en obtener_cliente: {e}")
        raise HTTPException(
            status_code=500, detail="Error interno del servidor"
        )


@router.post("", response_model=ClienteResponse, status_code=201)
@router.post("/", response_model=ClienteResponse, status_code=201)
def crear_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ➕ Crear nuevo cliente
    """
    try:
        logger.info(f"Crear cliente - Usuario: {current_user.email}")

        # Crear nuevo cliente
        nuevo_cliente = Cliente(
            cedula=cliente_data.cedula,
            nombres=cliente_data.nombres,
            apellidos=cliente_data.apellidos,
            telefono=cliente_data.telefono,
            email=cliente_data.email,
            direccion=cliente_data.direccion,
            fecha_nacimiento=cliente_data.fecha_nacimiento,
            ocupacion=cliente_data.ocupacion,
            modelo_vehiculo=cliente_data.modelo_vehiculo,
            concesionario=cliente_data.concesionario,
            analista=cliente_data.analista,
            estado=cliente_data.estado,
            notas=cliente_data.notas or "NA",
            usuario_registro=current_user.email,
            fecha_registro=datetime.now(),
            fecha_actualizacion=datetime.now(),
        )

        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)

        logger.info(f"Cliente creado exitosamente: {nuevo_cliente.id}")
        return ClienteResponse.model_validate(nuevo_cliente)

    except Exception as e:
        logger.error(f"Error en crear_cliente: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Error interno del servidor"
        )


@router.put("/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    cliente_data: ClienteUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✏️ Actualizar cliente
    """
    try:
        logger.info(
            f"Actualizar cliente {cliente_id} - Usuario: {current_user.email}"
        )

        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=404, detail="Cliente no encontrado"
            )

        # Actualizar campos
        update_data = cliente_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(cliente, field):
                setattr(cliente, field, value)

        # Actualizar fecha de actualización automáticamente
        cliente.fecha_actualizacion = datetime.now()

        db.commit()
        db.refresh(cliente)

        logger.info(f"Cliente actualizado exitosamente: {cliente_id}")
        return ClienteResponse.model_validate(cliente)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en actualizar_cliente: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Error interno del servidor"
        )


@router.delete("/{cliente_id}")
def eliminar_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🗑️ Eliminar cliente (hard delete)
    """
    try:
        logger.info(
            f"Eliminar cliente {cliente_id} - Usuario: {current_user.email}"
        )

        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=404, detail="Cliente no encontrado"
            )

        # Hard delete - eliminar físicamente de la BD
        db.delete(cliente)
        db.commit()

        logger.info(f"Cliente eliminado exitosamente: {cliente_id}")
        return {"message": "Cliente eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en eliminar_cliente: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Error interno del servidor"
        )
