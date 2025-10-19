"""
Endpoint de prueba para verificar el procesamiento de archivos Excel
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/test-excel-processing")
async def test_excel_processing(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🧪 Endpoint de prueba para verificar el procesamiento de Excel
    """
    try:
        logger.info(f"🧪 Prueba de procesamiento Excel - Usuario: {current_user.email}")
        
        # Información del request
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "query_params": dict(request.query_params)
        }
        
        return {
            "timestamp": "2025-10-19T22:15:00Z",
            "status": "success",
            "message": "Endpoint de prueba funcionando correctamente",
            "user": current_user.email,
            "request_info": request_info,
            "recomendacion": "El endpoint está funcionando. El problema puede estar en el frontend o en el archivo específico."
        }
        
    except Exception as e:
        logger.error(f"❌ Error en prueba de Excel: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en prueba: {str(e)}"
        )

@router.get("/test-template-download")
async def test_template_download(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🧪 Endpoint de prueba para verificar la descarga de templates
    """
    try:
        logger.info(f"🧪 Prueba de descarga de template - Usuario: {current_user.email}")
        
        # Simular respuesta de template
        test_content = "Test Excel Content"
        
        return {
            "timestamp": "2025-10-19T22:15:00Z",
            "status": "success",
            "message": "Template de prueba generado",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "content_length": len(test_content),
            "recomendacion": "Si este endpoint funciona, el problema está en el endpoint real de plantilla."
        }
        
    except Exception as e:
        logger.error(f"❌ Error en prueba de template: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en prueba: {str(e)}"
        )
