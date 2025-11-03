import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.analista import Analista
from app.models.user import User
from app.schemas.analista import (
    AnalistaCreate,
    AnalistaListResponse,
    AnalistaResponse,
    AnalistaUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ALTERNATIVA: Registrar tanto "/" como "" para compatibilidad
@router.get("", response_model=AnalistaListResponse)
@router.get("/", response_model=AnalistaListResponse)
def listar_analistas(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de resultados"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar analistas con filtros"""
    logger.info("=" * 80)
    logger.info("🔍 ENDPOINT EJECUTADO: listar_analistas")
    logger.info(f"👤 Usuario: {current_user.email if current_user else 'N/A'}")
    logger.info(f"📥 Parámetros recibidos: skip={skip}, limit={limit}, search={search}, activo={activo}")
    logger.info("=" * 80)

    try:
        query = db.query(Analista)

        if activo is not None:
            query = query.filter(Analista.activo == activo)

        # Ordenar por ID
        query = query.order_by(Analista.id)

        # Aplicar búsqueda si existe
        if search:
            query = query.filter(Analista.nombre.ilike(f"%{search}%"))

        # Contar total
        total = query.count()

        # Paginar
        analistas = query.offset(skip).limit(limit).all()

        # Calcular páginas
        pages = (total + limit - 1) // limit if limit > 0 else 0
        page = (skip // limit) + 1 if limit > 0 else 1

        logger.info(f"✅ Listando {len(analistas)} analistas de {total} totales (página {page}/{pages})")

        response = AnalistaListResponse(
            items=analistas,
            total=total,
            page=page,
            size=limit,
            pages=pages,
        )

        return response

    except Exception as e:
        logger.error(f"Error listando analistas: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/activos", response_model=List[AnalistaResponse])
def listar_analistas_activos(
    limit: int = Query(500, ge=1, le=1000, description="Límite de resultados (máx 1000)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar solo analistas activos.
    Limitado a 1000 resultados por defecto para evitar cargas excesivas.
    """
    try:
        analistas = (
            db.query(Analista)
            .filter(Analista.activo.is_(True))
            .order_by(Analista.nombre)
            .limit(limit)
            .all()
        )
        logger.info(f"✅ Listando {len(analistas)} analistas activos (límite: {limit})")
        return analistas
    except Exception as e:
        logger.error(f"Error listando analistas activos: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/{analista_id}", response_model=AnalistaResponse)
def obtener_analista(
    analista_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener analista específico
    try:
        analista = db.query(Analista).filter(Analista.id == analista_id).first()

        if not analista:
            raise HTTPException(status_code=404, detail="Analista no encontrado")

        return analista

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo analista: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/", response_model=AnalistaResponse, status_code=status.HTTP_201_CREATED)
def crear_analista(
    analista_data: AnalistaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Crear nuevo analista
    try:
        nuevo_analista = Analista(**analista_data.model_dump())

        db.add(nuevo_analista)
        db.commit()
        db.refresh(nuevo_analista)

        return nuevo_analista

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando analista: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.put("/{analista_id}", response_model=AnalistaResponse)
def actualizar_analista(
    analista_id: int,
    analista_data: AnalistaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Actualizar analista
    try:
        analista = db.query(Analista).filter(Analista.id == analista_id).first()

        if not analista:
            raise HTTPException(status_code=404, detail="Analista no encontrado")

        # Actualizar campos
        for field, value in analista_data.model_dump(exclude_unset=True).items():
            setattr(analista, field, value)

        # Actualizar timestamp manually
        analista.updated_at = datetime.utcnow()  # type: ignore[assignment]

        db.commit()
        db.refresh(analista)

        return analista

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando analista: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.delete("/{analista_id}")
def eliminar_analista(
    analista_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eliminar analista
    try:
        asesor = db.query(Analista).filter(Analista.id == analista_id).first()

        if not asesor:
            raise HTTPException(status_code=404, detail="Analista no encontrado")

        db.delete(asesor)
        db.commit()
        return {"message": "Analista eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar analista: {str(e)}")


def _normalizar_valor_activo(activo_val, pd) -> bool:
    """Normaliza el valor de activo desde Excel"""
    if activo_val is None or pd.isna(activo_val):
        return True
    return bool(activo_val)


def _procesar_fila_analista(row, db: Session, idx: int) -> tuple[int, int, Optional[str]]:
    """Procesa una fila del Excel para analistas"""
    import pandas as pd

    try:
        nombre = str(row.get("nombre", "")).strip()
        if not nombre:
            return (0, 0, None)

        activo_val = _normalizar_valor_activo(row.get("activo"), pd)

        existente = db.query(Analista).filter(Analista.nombre == nombre).first()
        if existente:
            existente.activo = activo_val
            existente.updated_at = datetime.utcnow()
            return (0, 1, None)

        nuevo = Analista(
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
def importar_analistas(
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
            c, a, error = _procesar_fila_analista(row, db, idx)
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
        logger.error(f"Error importando analistas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error procesando el archivo")
