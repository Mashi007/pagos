# backend/app/api/v1/endpoints/log_test.py
"""
Endpoint que SIEMPRE genera logs para verificar que el backend funciona
"""
from fastapi import APIRouter
from datetime import datetime
import logging
import sys

router = APIRouter()

@router.get("/force-logs")
def force_logs():
    """
    Endpoint que SIEMPRE genera logs para verificar funcionamiento
    """
    timestamp = datetime.utcnow().isoformat()
    
    # Generar logs SIEMPRE
    logging.info(f"🔍 FORCE LOGS - {timestamp} - Endpoint llamado")
    print(f"🔍 FORCE LOGS - {timestamp} - Endpoint llamado")
    
    logging.warning(f"⚠️ FORCE LOGS - {timestamp} - Warning de prueba")
    print(f"⚠️ FORCE LOGS - {timestamp} - Warning de prueba")
    
    logging.error(f"❌ FORCE LOGS - {timestamp} - Error de prueba")
    print(f"❌ FORCE LOGS - {timestamp} - Error de prueba")
    
    # También escribir a stderr
    print(f"🖨️ FORCE LOGS - {timestamp} - Print a stdout", file=sys.stdout)
    print(f"🖨️ FORCE LOGS - {timestamp} - Print a stderr", file=sys.stderr)
    
    return {
        "status": "success",
        "message": "Logs forzados generados",
        "timestamp": timestamp,
        "note": "Revisar logs del servidor backend para ver estos mensajes"
    }

@router.get("/check-backend-status")
def check_backend_status():
    """
    Verificar estado del backend
    """
    timestamp = datetime.utcnow().isoformat()
    
    logging.info(f"📊 BACKEND STATUS CHECK - {timestamp}")
    print(f"📊 BACKEND STATUS CHECK - {timestamp}")
    
    return {
        "status": "running",
        "backend": "pagos-f2qf.onrender.com",
        "timestamp": timestamp,
        "message": "Backend funcionando correctamente",
        "logs_generated": True
    }
