from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from app.db.session import get_db
from app.models.user import User
from app.models.pago import Pago
from app.api.deps import get_current_user
from app.schemas.pago import (
    PagoCreate, PagoUpdate, PagoResponse, PagoListResponse,
    ConciliacionCreate, ConciliacionResponse, KPIsPagos, ResumenCliente
)
from typing import List, Optional
import logging
from datetime import datetime, timedelta
import os
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()

# CONFIGURACIÓN DE ARCHIVOS
UPLOAD_DIR = Path("uploads/pagos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.pdf'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@router.post("/crear", response_model=PagoResponse, status_code=status.HTTP_201_CREATED)
async def crear_pago(
    pago_data: PagoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear un nuevo pago"""
    try:
        logger.info(f"Usuario {current_user.email} creando pago para cédula {pago_data.cedula_cliente}")
        
        # Crear el pago
        nuevo_pago = Pago(
            cedula_cliente=pago_data.cedula_cliente,
            fecha_pago=pago_data.fecha_pago,
            monto_pagado=pago_data.monto_pagado,
            numero_documento=pago_data.numero_documento,
            documento_nombre=pago_data.documento_nombre,
            documento_tipo=pago_data.documento_tipo,
            documento_tamaño=pago_data.documento_tamaño,
            documento_ruta=pago_data.documento_ruta,
            notas=pago_data.notas,
            conciliado=False  # Por defecto no conciliado
        )
        
        db.add(nuevo_pago)
        db.commit()
        db.refresh(nuevo_pago)
        
        logger.info(f"Pago creado exitosamente con ID {nuevo_pago.id}")
        return nuevo_pago
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando pago: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.post("/subir-documento", status_code=status.HTTP_200_OK)
async def subir_documento(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Subir documento de pago"""
    try:
        # Validar tipo de archivo
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de archivo no permitido. Solo PNG, JPG, JPEG, PDF"
            )
        
        # Validar tamaño
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archivo demasiado grande. Máximo 5MB"
            )
        
        # Generar nombre único
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Guardar archivo
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        logger.info(f"Documento subido: {unique_filename}")
        
        return {
            "success": True,
            "filename": unique_filename,
            "original_name": file.filename,
            "size": len(file_content),
            "type": file_extension[1:].upper(),
            "path": str(file_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subiendo documento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/listar", response_model=PagoListResponse)
async def listar_pagos(
    pagina: int = Query(1, ge=1, description="Número de página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Elementos por página"),
    cedula: Optional[str] = Query(None, description="Filtrar por cédula"),
    conciliado: Optional[bool] = Query(None, description="Filtrar por estado de conciliación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Listar pagos con filtros"""
    try:
        query = db.query(Pago).filter(Pago.activo == True)
        
        # Aplicar filtros
        if cedula:
            query = query.filter(Pago.cedula_cliente.ilike(f"%{cedula}%"))
        if conciliado is not None:
            query = query.filter(Pago.conciliado == conciliado)
        
        # Contar total
        total = query.count()
        
        # Paginación
        offset = (pagina - 1) * por_pagina
        pagos = query.order_by(desc(Pago.fecha_registro)).offset(offset).limit(por_pagina).all()
        
        total_paginas = (total + por_pagina - 1) // por_pagina
        
        return PagoListResponse(
            pagos=pagos,
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            total_paginas=total_paginas
        )
        
    except Exception as e:
        logger.error(f"Error listando pagos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/kpis", response_model=KPIsPagos)
async def obtener_kpis_pagos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener KPIs de pagos"""
    try:
        # KPIs básicos
        total_pagos = db.query(Pago).filter(Pago.activo == True).count()
        total_dolares = db.query(func.sum(Pago.monto_pagado)).filter(Pago.activo == True).scalar() or 0
        numero_pagos = total_pagos  # Mismo valor para consistencia
        
        # KPIs de conciliación
        cantidad_conciliada = db.query(Pago).filter(
            and_(Pago.activo == True, Pago.conciliado == True)
        ).count()
        cantidad_no_conciliada = total_pagos - cantidad_conciliada
        
        return KPIsPagos(
            total_pagos=total_pagos,
            total_dolares=float(total_dolares),
            numero_pagos=numero_pagos,
            cantidad_conciliada=cantidad_conciliada,
            cantidad_no_conciliada=cantidad_no_conciliada,
            fecha_actualizacion=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo KPIs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/resumen-cliente/{cedula}", response_model=ResumenCliente)
async def obtener_resumen_cliente(
    cedula: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener resumen de pagos por cliente"""
    try:
        # Filtrar pagos del cliente
        pagos_cliente = db.query(Pago).filter(
            and_(Pago.activo == True, Pago.cedula_cliente == cedula.upper())
        ).all()
        
        if not pagos_cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontraron pagos para la cédula {cedula}"
            )
        
        # Calcular resumen
        total_pagado = sum(pago.monto_pagado for pago in pagos_cliente)
        total_conciliado = sum(pago.monto_pagado for pago in pagos_cliente if pago.conciliado)
        total_pendiente = total_pagado - total_conciliado
        numero_pagos = len(pagos_cliente)
        
        # Último pago
        ultimo_pago = max(pagos_cliente, key=lambda p: p.fecha_pago).fecha_pago
        
        # Estado de conciliación
        if total_conciliado == total_pagado:
            estado_conciliacion = "CONCILIADO"
        elif total_conciliado > 0:
            estado_conciliacion = "PARCIAL"
        else:
            estado_conciliacion = "PENDIENTE"
        
        return ResumenCliente(
            cedula_cliente=cedula.upper(),
            total_pagado=total_pagado,
            total_conciliado=total_conciliado,
            total_pendiente=total_pendiente,
            numero_pagos=numero_pagos,
            ultimo_pago=ultimo_pago,
            estado_conciliacion=estado_conciliacion
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo resumen del cliente {cedula}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/descargar-documento/{filename}")
async def descargar_documento(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """Descargar documento de pago"""
    try:
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo no encontrado"
            )
        
        # Determinar tipo de contenido
        file_extension = file_path.suffix.lower()
        content_type_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.pdf': 'application/pdf'
        }
        
        content_type = content_type_map.get(file_extension, 'application/octet-stream')
        
        return {
            "success": True,
            "filename": filename,
            "content_type": content_type,
            "download_url": f"/api/v1/pagos/descargar-documento/{filename}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error descargando documento {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )