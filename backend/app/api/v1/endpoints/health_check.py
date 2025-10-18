# backend/app/api/v1/endpoints/health_check.py
"""
Endpoint simple para verificar que el backend esté funcionando
"""
from fastapi import APIRouter
from datetime import datetime
import logging

router = APIRouter()

@router.get("/ping")
def ping():
    """
    Endpoint simple para verificar que el backend esté funcionando
    """
    timestamp = datetime.utcnow().isoformat()
    
    # Probar logging
    logging.info(f"🏓 PING endpoint llamado - {timestamp}")
    print(f"🏓 PING endpoint llamado - {timestamp}")
    
    return {
        "status": "ok",
        "message": "Backend funcionando correctamente",
        "timestamp": timestamp,
        "service": "RapiCredit API",
        "version": "1.0.0"
    }

@router.get("/test-logs")
def test_logs():
    """
    Probar que los logs estén funcionando
    """
    timestamp = datetime.utcnow().isoformat()
    
    # Probar diferentes niveles de logging
    logging.debug(f"🔍 DEBUG: Test log - {timestamp}")
    logging.info(f"ℹ️ INFO: Test log - {timestamp}")
    logging.warning(f"⚠️ WARNING: Test log - {timestamp}")
    logging.error(f"❌ ERROR: Test log - {timestamp}")
    
    # También usar print como fallback
    print(f"🖨️ PRINT: Test log - {timestamp}")
    
    return {
        "status": "success",
        "message": "Logs de prueba enviados",
        "timestamp": timestamp,
        "note": "Revisar los logs del servidor para ver los mensajes de prueba"
    }
