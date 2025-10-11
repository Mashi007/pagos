# backend/app/api/v1/endpoints/clientes.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse

router = APIRouter()


@router.post("/", response_model=ClienteResponse, status_code=201)
def crear_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    """Crear un nuevo cliente"""
    
    # Verificar si ya existe la cédula
    existing = db.query(Cliente).filter(Cliente.cedula == cliente.cedula).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cédula ya registrada")
    
    # ✅ CORRECCIÓN: usar model_dump() en lugar de dict()
    db_cliente = Cliente(**cliente.model_dump())
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    
    return db_cliente


@router.get("/", response_model=List[ClienteResponse])
def listar_clientes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    activo: bool = Query(None),
    db: Session = Depends(get_db)
):
    """Listar clientes con paginación"""
    query = db.query(Cliente)
    
    if activo is not None:
        query = query.filter(Cliente.activo == activo)
    
    clientes = query.offset(skip).limit(limit).all()
    return clientes


@router.get("/cedula/{cedula}", response_model=ClienteResponse)
def buscar_por_cedula(cedula: str, db: Session = Depends(get_db)):
    """Buscar cliente por cédula"""
    cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtener un cliente por ID"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.put("/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: int,
    cliente_data: ClienteUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar datos de un cliente"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # ✅ CORRECCIÓN: usar model_dump() en lugar de dict()
    for field, value in cliente_data.model_dump(exclude_unset=True).items():
        setattr(cliente, field, value)
    
    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=204)
def eliminar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Desactivar un cliente (soft delete)"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente.activo = False
    cliente.estado = "INACTIVO"
    db.commit()
    return None
