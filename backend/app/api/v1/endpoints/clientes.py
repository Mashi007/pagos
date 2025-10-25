from datetime import date
"""
Endpoints de gestión de clientes - VERSIÓN CON AUDITORÍA AUTOMÁTICA
Sistema completo de gestión de clientes con validaciones y auditoría
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.cliente import Cliente
from app.models.user import User
from app.schemas.cliente import 

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=dict)
@router.get("/", response_model=dict)
def listar_clientes
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=1000, description="Tamaño de página"),
    # Búsqueda de texto
    search: Optional[str] = Query
    ),
    estado: Optional[str] = Query
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    """
    try:
        logger.info(f"Listar clientes - Usuario: {current_user.email}")

        # Query base
        query = db.query(Cliente)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter
                    Cliente.nombres.ilike(search_pattern),
                    Cliente.cedula.ilike(search_pattern),
                    Cliente.telefono.ilike(search_pattern),

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
                cliente_data = 
                clientes_dict.append(cliente_data)
            except Exception as e:
                logger.error(f"Error serializando cliente {cliente.id}: {e}")
                continue

        # Calcular páginas
        total_pages = (total + per_page - 1) // per_page

        return 
            },
    except Exception as e:
        logger.error(f"Error en listar_clientes: {e}")
        raise HTTPException


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente
    cliente_id: int = Path(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    👤 Obtener cliente por ID
    """
    try:
        logger.info
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException
        return ClienteResponse.model_validate(cliente)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en obtener_cliente: {e}")
        raise HTTPException


def crear_cliente
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ➕ Crear nuevo cliente
    """
    try:
        logger.info(f"Crear cliente - Usuario: {current_user.email}")

        # Crear nuevo cliente
        nuevo_cliente = Cliente

        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)

        return ClienteResponse.model_validate(nuevo_cliente)

    except Exception as e:
        logger.error(f"Error en crear_cliente: {e}")
        db.rollback()
        raise HTTPException


@router.put("/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente
    cliente_id: int = Path(..., description="ID del cliente"),
    cliente_data: ClienteUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✏️ Actualizar cliente
    """
    try:
        logger.info

        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException

        update_data = cliente_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(cliente, field):
                setattr(cliente, field, value)

        # Actualizar fecha de actualización automáticamente

        db.commit()
        db.refresh(cliente)

        return ClienteResponse.model_validate(cliente)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en actualizar_cliente: {e}")
        db.rollback()
        raise HTTPException


@router.delete("/{cliente_id}")
def eliminar_cliente
    cliente_id: int = Path(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🗑️ Eliminar cliente (hard delete)
    """
    try:
        logger.info

        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException

        # Hard delete - eliminar físicamente de la BD
        db.delete(cliente)
        db.commit()


    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en eliminar_cliente: {e}")
        db.rollback()
        raise HTTPException
