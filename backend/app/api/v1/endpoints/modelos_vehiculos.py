import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.user import User
from app.schemas.modelo_vehiculo import (
    ModeloVehiculoCreate,
    ModeloVehiculoListResponse,
    ModeloVehiculoResponse,
    ModeloVehiculoUpdate,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=ModeloVehiculoListResponse)
def listar_modelos_vehiculos(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(20, ge=1, le=1000, description="Tamaño de página"),
    # Búsqueda
    search: Optional[str] = Query(None, description="Buscar por modelo"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar modelos de vehículos con filtros"""

    query = db.query(ModeloVehiculo)

    # Aplicar filtros
    if search:
        query = query.filter(or_(ModeloVehiculo.modelo.ilike(f"%{search}%")))

    if activo is not None:
        query = query.filter(ModeloVehiculo.activo == activo)

    # Ordenar por ID
    query = query.order_by(ModeloVehiculo.id)

    # Contar total
    total = query.count()

    # Paginar
    modelos = query.offset(skip).limit(limit).all()

    # Calcular páginas
    pages = (total + limit - 1) // limit if limit > 0 else 0
    page = (skip // limit) + 1 if limit > 0 else 1

    logger.info(f"✅ Listando {len(modelos)} modelos de vehículos de {total} totales (página {page}/{pages})")

    response = ModeloVehiculoListResponse(
        items=modelos,
        total=total,
        page=page,
        page_size=limit,
        total_pages=pages,
    )

    return response


@router.get("/activos", response_model=List[ModeloVehiculoResponse])
def listar_modelos_activos(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Listar solo modelos activos (para formularios)."""
    try:
        # Solo modelos activos con precio definido (precio obligatorio para usar modelo)
        modelos = (
            db.query(ModeloVehiculo)
            .filter(ModeloVehiculo.activo.is_(True), ModeloVehiculo.precio.isnot(None))
            .all()
        )
        logger.info(f"✅ Listando {len(modelos)} modelos activos con precio definido")
        return modelos
    except Exception as e:
        logger.error(f"Error listando modelos activos: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/{modelo_id}", response_model=ModeloVehiculoResponse)
def obtener_modelo_vehiculo(
    modelo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener un modelo de vehículo por ID"""

    modelo = db.query(ModeloVehiculo).filter(ModeloVehiculo.id == modelo_id).first()

    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo de vehículo no encontrado")

    return modelo


@router.post("/", response_model=ModeloVehiculoResponse)
def crear_modelo_vehiculo(
    modelo_data: ModeloVehiculoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear un nuevo modelo de vehículo"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    # Verificar si ya existe
    existing = (
        db.query(ModeloVehiculo)
        .filter(ModeloVehiculo.modelo == modelo_data.modelo)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400, detail="Ya existe un modelo con ese nombre"
        )

    modelo = ModeloVehiculo(**modelo_data.dict())
    db.add(modelo)
    db.commit()
    db.refresh(modelo)

    return modelo


@router.put("/{modelo_id}", response_model=ModeloVehiculoResponse)
def actualizar_modelo_vehiculo(
    modelo_id: int,
    modelo_data: ModeloVehiculoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar un modelo de vehículo"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    modelo = db.query(ModeloVehiculo).filter(ModeloVehiculo.id == modelo_id).first()

    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo de vehículo no encontrado")

    # Actualizar campos
    for field, value in modelo_data.dict(exclude_unset=True).items():
        setattr(modelo, field, value)

    # Actualizar timestamp manualmente
    modelo.updated_at = datetime.utcnow()
    modelo.fecha_actualizacion = datetime.utcnow()
    modelo.actualizado_por = (
        current_user.email if getattr(current_user, "email", None) else None
    )

    db.commit()
    db.refresh(modelo)

    return modelo


@router.delete("/{modelo_id}")
def eliminar_modelo_vehiculo(
    modelo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar un modelo de vehículo"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    modelo = db.query(ModeloVehiculo).filter(ModeloVehiculo.id == modelo_id).first()

    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo de vehículo no encontrado")

    db.delete(modelo)
    db.commit()

    return {"message": "Modelo de vehículo eliminado exitosamente"}


@router.post("/importar")
def importar_modelos_vehiculos(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Carga masiva desde Excel. Columnas requeridas: modelo, precio, fecha_actualizacion(opcional)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")

    try:
        import pandas as pd

        if not archivo.filename.lower().endswith((".xlsx", ".xls")):
            raise HTTPException(
                status_code=400, detail="Formato inválido. Use Excel .xlsx/.xls"
            )

        df = pd.read_excel(archivo.file)
        columnas = {c.lower().strip() for c in df.columns}
        if "modelo" not in columnas or "precio" not in columnas:
            raise HTTPException(
                status_code=400, detail="Columnas requeridas: modelo, precio"
            )

        creados = 0
        actualizados = 0
        for _, row in df.iterrows():
            nombre = str(row.get("modelo")).strip()
            try:
                precio_val = float(row.get("precio"))
            except Exception:
                continue
            fecha_act = row.get("fecha_actualizacion")

            existente = (
                db.query(ModeloVehiculo).filter(ModeloVehiculo.modelo == nombre).first()
            )
            if existente:
                existente.precio = precio_val
                existente.fecha_actualizacion = (
                    pd.to_datetime(fecha_act).to_pydatetime()
                    if pd.notna(fecha_act)
                    else datetime.utcnow()
                )
                existente.actualizado_por = (
                    current_user.email if getattr(current_user, "email", None) else None
                )
                actualizados += 1
            else:
                nuevo = ModeloVehiculo(
                    modelo=nombre,
                    activo=True,
                    precio=precio_val,
                    fecha_actualizacion=datetime.utcnow(),
                    actualizado_por=(
                        current_user.email
                        if getattr(current_user, "email", None)
                        else None
                    ),
                )
                db.add(nuevo)
                creados += 1

        db.commit()
        return {
            "message": "Importación completada",
            "creados": creados,
            "actualizados": actualizados,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importando modelos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error procesando el archivo")
