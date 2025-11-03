import logging
import traceback
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.concesionario import Concesionario
from app.models.user import User
from app.schemas.concesionario import (
    ConcesionarioCreate,
    ConcesionarioListResponse,
    ConcesionarioResponse,
    ConcesionarioUpdate,
)

# Endpoints de gestion de concesionarios


logger = logging.getLogger(__name__)
router = APIRouter()


# ALTERNATIVA: Registrar tanto "/" como "" para compatibilidad
@router.get("", response_model=ConcesionarioListResponse)
@router.get("/", response_model=ConcesionarioListResponse)
def list_concesionarios(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(20, ge=1, le=1000, description="Limite de resultados"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar concesionarios con filtros"""
    logger.info("=" * 80)
    logger.info("🔍 ENDPOINT EJECUTADO: list_concesionarios")
    logger.info(f"👤 Usuario: {current_user.email if current_user else 'N/A'}")
    logger.info(f"📥 Parámetros recibidos: skip={skip}, limit={limit}, search={search}, activo={activo}")
    logger.info("=" * 80)

    try:
        query = db.query(Concesionario)

        if activo is not None:
            query = query.filter(Concesionario.activo == activo)
        if search:
            query = query.filter(Concesionario.nombre.ilike(f"%{search}%"))

        # Ordenar por ID
        query = query.order_by(Concesionario.id)

        # Obtener total
        total = query.count()

        # Aplicar paginacion
        concesionarios = query.offset(skip).limit(limit).all()

        # Calcular paginas
        pages = (total + limit - 1) // limit if limit > 0 else 0
        page = (skip // limit) + 1 if limit > 0 else 1

        logger.info(f"✅ Listando {len(concesionarios)} concesionarios de {total} totales (página {page}/{pages})")

        response = ConcesionarioListResponse(
            items=concesionarios,
            total=total,
            page=page,
            size=limit,
            pages=pages,
        )

        return response
    except Exception as e:
        logger.error(f"Error en list_concesionarios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/activos", response_model=List[ConcesionarioResponse])
def list_concesionarios_activos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Listar solo concesionarios activos (para formularios)."""
    try:
        concesionarios = db.query(Concesionario).filter(Concesionario.activo.is_(True)).all()
        logger.info(f"✅ Listando {len(concesionarios)} concesionarios activos")
        return concesionarios
    except Exception as e:
        logger.error(f"Error listando concesionarios activos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/dropdown")
def get_concesionarios_dropdown(
    db: Session = Depends(get_db),
    # TEMPORALMENTE SIN AUTENTICACION PARA DROPDOWNS
    # current_user: User = Depends(get_current_user)
):
    # Obtener concesionarios activos para dropdown
    try:
        concesionarios = db.query(Concesionario).filter(Concesionario.activo).all()
        return [{"id": c.id, "nombre": c.nombre} for c in concesionarios]
    except Exception as e:
        logger.error(f"Error en get_concesionarios_dropdown: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/{concesionario_id}", response_model=ConcesionarioResponse)
def obtener_concesionario(
    concesionario_id: int = Path(..., description="ID del concesionario"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener un concesionario por ID
    concesionario = db.query(Concesionario).filter(Concesionario.id == concesionario_id).first()
    if not concesionario:
        raise HTTPException(status_code=404, detail="Concesionario no encontrado")
    return ConcesionarioResponse.model_validate(concesionario)


@router.post("/", response_model=ConcesionarioResponse)
def crear_concesionario(
    concesionario_data: ConcesionarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Crear un nuevo concesionario
    try:
        # Crear nuevo concesionario
        concesionario = Concesionario(**concesionario_data.model_dump())

        db.add(concesionario)
        db.commit()
        db.refresh(concesionario)

        logger.info(f"Concesionario creado: ID={concesionario.id}")
        return ConcesionarioResponse.model_validate(concesionario)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando concesionario: {e}")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear concesionario: {str(e)}")


@router.put("/{concesionario_id}", response_model=ConcesionarioResponse)
def actualizar_concesionario(
    concesionario_id: int = Path(..., description="ID del concesionario"),
    concesionario_data: ConcesionarioUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Actualizar un concesionario existente
    try:
        concesionario = db.query(Concesionario).filter(Concesionario.id == concesionario_id).first()
        if not concesionario:
            raise HTTPException(status_code=404, detail="Concesionario no encontrado")

        # Verificar nombre unico si se esta cambiando
        if concesionario_data.nombre and concesionario_data.nombre != concesionario.nombre:
            existing = db.query(Concesionario).filter(Concesionario.nombre == concesionario_data.nombre).first()
            if existing:
                raise HTTPException(status_code=400, detail="El nombre ya existe")

        update_data = concesionario_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(concesionario, field, value)

        # Actualizar timestamp manually
        concesionario.updated_at = datetime.utcnow()  # type: ignore[assignment]

        db.commit()
        db.refresh(concesionario)
        return ConcesionarioResponse.model_validate(concesionario)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar concesionario: {str(e)}",
        )


@router.delete("/{concesionario_id}")
def eliminar_concesionario(
    concesionario_id: int = Path(..., description="ID del concesionario"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eliminar un concesionario (HARD DELETE - borrado completo de BD)
    try:
        concesionario = db.query(Concesionario).filter(Concesionario.id == concesionario_id).first()
        if not concesionario:
            raise HTTPException(status_code=404, detail="Concesionario no encontrado")

        db.delete(concesionario)
        db.commit()

        return {"message": "Concesionario eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar concesionario: {str(e)}",
        )


def _normalizar_valor_activo(activo_val, pd) -> bool:
    """Normaliza el valor de activo desde Excel"""
    if activo_val is None or pd.isna(activo_val):
        return True
    return bool(activo_val)


def _procesar_fila_concesionario(row, db: Session, idx: int) -> tuple[int, int, Optional[str]]:
    """Procesa una fila del Excel para concesionarios"""
    import pandas as pd

    try:
        nombre = str(row.get("nombre", "")).strip()
        if not nombre:
            return (0, 0, None)

        activo_val = _normalizar_valor_activo(row.get("activo"), pd)

        existente = db.query(Concesionario).filter(Concesionario.nombre == nombre).first()
        if existente:
            existente.activo = activo_val
            existente.updated_at = datetime.utcnow()
            return (0, 1, None)

        nuevo = Concesionario(
            nombre=nombre,
            activo=activo_val,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(nuevo)
        return (1, 0, None)
    except Exception as e:
        error_msg = f"Fila {idx + 2}: {str(e)}"
        logger.warning(f"Error procesando fila {idx + 2}: {e}")
        return (0, 0, error_msg)


@router.post("/importar")
def importar_concesionarios(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Carga masiva desde Excel. Columnas requeridas: nombre, activo (opcional, por defecto True)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")

    try:
        import pandas as pd

        if not archivo.filename or not archivo.filename.lower().endswith((".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail="Formato inválido. Use Excel .xlsx/.xls")

        df = pd.read_excel(archivo.file)
        columnas = {c.lower().strip() for c in df.columns}
        if "nombre" not in columnas:
            raise HTTPException(status_code=400, detail="Columna requerida: nombre")

        creados = 0
        actualizados = 0
        errores = []

        for idx, row in df.iterrows():
            c, a, error = _procesar_fila_concesionario(row, db, idx)
            creados += c
            actualizados += a
            if error:
                errores.append(error)

        db.commit()
        logger.info(f"Importación completada: {creados} creados, {actualizados} actualizados")

        return {
            "message": "Importación completada",
            "creados": creados,
            "actualizados": actualizados,
            "errores": errores if errores else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error importando concesionarios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error procesando el archivo")
