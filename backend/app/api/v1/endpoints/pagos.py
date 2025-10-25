"""
"""

import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import 
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.pago import Pago
from app.models.user import User
from app.schemas.pago import 

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

logger = logging.getLogger(__name__)
router = APIRouter()


    "/crear", response_model=PagoResponse, status_code=status.HTTP_201_CREATED


async def crear_pago
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear un nuevo pago"""
    try:
        logger.info

        # Crear el pago
        nuevo_pago = Pago

        db.add(nuevo_pago)
        db.commit()
        db.refresh(nuevo_pago)

        return nuevo_pago

    except Exception as e:
        db.rollback()
        logger.error(f"Error creando pago: {e}")
        raise HTTPException
            detail=f"Error interno del servidor: {str(e)}",


async def subir_documento
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Subir documento de pago"""
    try:
        # Validar tipo de archivo
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException

        # Validar tamaño
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException

        # Generar nombre único
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename

        # Guardar archivo
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)

        logger.info(f"Documento subido: {unique_filename}")
        return 

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subiendo documento: {e}")
        raise HTTPException
            detail=f"Error interno del servidor: {str(e)}",


@router.get("/listar", response_model=PagoListResponse)
    pagina: int = Query(1, ge=1, description="Número de página"),
    por_pagina: int = Query
    ),
    cedula: Optional[str] = Query(None, description="Filtrar por cédula"),
    conciliado: Optional[bool] = Query
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = db.query(Pago).filter(Pago.activo)

        if cedula:
            query = query.filter(Pago.cedula_cliente.ilike(f"%{cedula}%"))
        if conciliado is not None:
            query = query.filter(Pago.conciliado == conciliado)

        # Contar total
        total = query.count()

        # Paginación
        offset = (pagina - 1) * por_pagina
            query.order_by(desc(Pago.fecha_registro))
            .offset(offset)
            .limit(por_pagina)
            .all()

        total_paginas = (total + por_pagina - 1) // por_pagina

        return PagoListResponse

    except Exception as e:
        raise HTTPException
            detail=f"Error interno del servidor: {str(e)}",


    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        total_dolares = 
            db.query(func.sum(Pago.monto_pagado)).filter(Pago.activo).scalar()
            or 0

        # KPIs de conciliación
        cantidad_conciliada = 
            db.query(Pago).filter(and_(Pago.activo, Pago.conciliado)).count()

            total_dolares=float(total_dolares),
            cantidad_conciliada=cantidad_conciliada,
            cantidad_no_conciliada=cantidad_no_conciliada,

    except Exception as e:
        logger.error(f"Error obteniendo KPIs: {e}")
        raise HTTPException
            detail=f"Error interno del servidor: {str(e)}",


@router.get("/resumen-cliente/{cedula}", response_model=ResumenCliente)
async def obtener_resumen_cliente
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
            db.query(Pago)
            .filter(and_(Pago.activo, Pago.cedula_cliente == cedula.upper()))
            .all()

            raise HTTPException

        # Calcular resumen
        total_conciliado = sum
        total_pendiente = total_pagado - total_conciliado

        # Último pago

        # Estado de conciliación
        if total_conciliado == total_pagado:
            estado_conciliacion = "CONCILIADO"
        elif total_conciliado > 0:
            estado_conciliacion = "PARCIAL"
        else:
            estado_conciliacion = "PENDIENTE"

        return ResumenCliente
            cedula_cliente=cedula.upper(),
            total_pagado=total_pagado,
            total_conciliado=total_conciliado,
            total_pendiente=total_pendiente,
            ultimo_pago=ultimo_pago,
            estado_conciliacion=estado_conciliacion,

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo resumen del cliente {cedula}: {e}")
        raise HTTPException
            detail=f"Error interno del servidor: {str(e)}",


@router.get("/descargar-documento/{filename}")
async def descargar_documento
    filename: str, current_user: User = Depends(get_current_user)
):
    """Descargar documento de pago"""
    try:
        file_path = UPLOAD_DIR / filename

        if not file_path.exists():
            raise HTTPException

        # Determinar tipo de contenido
        file_extension = file_path.suffix.lower()
        content_type_map = 
        content_type = content_type_map.get

        return 

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error descargando documento {filename}: {e}")
        raise HTTPException
            detail=f"Error interno del servidor: {str(e)}",

"""
"""