# ============================================================
# ENDPOINT PARA EJECUTAR MOCK DATA
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/create-mock-data")
def create_mock_data_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crear datos de prueba para el sistema
    """
    try:
        logger.info(f"Usuario {current_user.email} solicitando creación de mock data")
        
        # Importar y ejecutar el script de mock data
        from app.scripts.create_mock_data import create_mock_data
        
        # Ejecutar creación de datos
        create_mock_data()
        
        return {
            "success": True,
            "message": "Mock data creado exitosamente",
            "details": {
                "asesores": 3,
                "concesionarios": 3,
                "modelos_vehiculos": 5,
                "clientes": 3,
                "prestamos": 3,
                "pagos": 26
            }
        }
        
    except Exception as e:
        logger.error(f"Error creando mock data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creando mock data: {str(e)}"
        )

@router.get("/check-data-status")
def check_data_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verificar estado de datos en el sistema
    """
    try:
        from app.models.cliente import Cliente
        from app.models.prestamo import Prestamo
        from app.models.pago import Pago
        from app.models.asesor import Asesor
        from app.models.concesionario import Concesionario
        from app.models.modelo_vehiculo import ModeloVehiculo
        
        # Contar registros en cada tabla
        counts = {
            "usuarios": db.query(User).count(),
            "clientes": db.query(Cliente).count(),
            "prestamos": db.query(Prestamo).count(),
            "pagos": db.query(Pago).count(),
            "asesores": db.query(Asesor).count(),
            "concesionarios": db.query(Concesionario).count(),
            "modelos_vehiculos": db.query(ModeloVehiculo).count()
        }
        
        # Determinar estado
        total_tables = len(counts)
        tables_with_data = sum(1 for count in counts.values() if count > 0)
        
        status = "COMPLETO" if tables_with_data == total_tables else "INCOMPLETO"
        
        return {
            "status": status,
            "tables_with_data": tables_with_data,
            "total_tables": total_tables,
            "completion_percentage": round((tables_with_data / total_tables) * 100, 2),
            "counts": counts
        }
        
    except Exception as e:
        logger.error(f"Error verificando estado de datos: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error verificando datos: {str(e)}"
        )
