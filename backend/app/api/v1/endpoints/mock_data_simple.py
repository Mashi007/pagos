# ============================================================
# ENDPOINT SIMPLE DE PRUEBA PARA MOCK DATA
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/test")
def test_mock_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Test simple del endpoint de mock data
    """
    try:
        logger.info(f"Usuario {current_user.email} accediendo al test endpoint")
        
        return {
            "success": True,
            "message": "Endpoint de mock data funcionando",
            "user": current_user.email,
            "timestamp": "2025-10-16T10:20:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error en test endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en test: {str(e)}"
        )

@router.get("/check-tables")
def check_tables_simple(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verificar tablas de forma simple
    """
    try:
        from app.models.cliente import Cliente
        from app.models.prestamo import Prestamo
        from app.models.pago import Pago
        from app.models.asesor import Asesor
        from app.models.concesionario import Concesionario
        from app.models.modelo_vehiculo import ModeloVehiculo
        
        # Contar registros de forma simple
        counts = {}
        
        try:
            counts["usuarios"] = db.query(User).count()
        except Exception as e:
            counts["usuarios"] = f"Error: {str(e)}"
            
        try:
            counts["clientes"] = db.query(Cliente).count()
        except Exception as e:
            counts["clientes"] = f"Error: {str(e)}"
            
        try:
            counts["prestamos"] = db.query(Prestamo).count()
        except Exception as e:
            counts["prestamos"] = f"Error: {str(e)}"
            
        try:
            counts["pagos"] = db.query(Pago).count()
        except Exception as e:
            counts["pagos"] = f"Error: {str(e)}"
            
        try:
            counts["asesores"] = db.query(Asesor).count()
        except Exception as e:
            counts["asesores"] = f"Error: {str(e)}"
            
        try:
            counts["concesionarios"] = db.query(Concesionario).count()
        except Exception as e:
            counts["concesionarios"] = f"Error: {str(e)}"
            
        try:
            counts["modelos_vehiculos"] = db.query(ModeloVehiculo).count()
        except Exception as e:
            counts["modelos_vehiculos"] = f"Error: {str(e)}"
        
        return {
            "success": True,
            "message": "Verificación de tablas completada",
            "counts": counts
        }
        
    except Exception as e:
        logger.error(f"Error verificando tablas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error verificando tablas: {str(e)}"
        )

@router.post("/create-simple-data")
def create_simple_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crear datos simples para probar
    """
    try:
        logger.info(f"Usuario {current_user.email} creando datos simples")
        
        from app.models.asesor import Asesor
        from app.models.concesionario import Concesionario
        from app.models.modelo_vehiculo import ModeloVehiculo
        
        # Crear un asesor simple
        asesor = Asesor(
            nombre="Test Asesor",
            apellido="Sistema",
            email="test@rapicreditca.com",
            telefono="555-0001",
            especialidad="Testing",
            activo=True
        )
        db.add(asesor)
        db.flush()
        
        # Crear un concesionario simple
        concesionario = Concesionario(
            nombre="Test Concesionario",
            direccion="Test Address",
            telefono="555-0002",
            email="test@concesionario.com",
            responsable="Test Responsable",
            activo=True
        )
        db.add(concesionario)
        db.flush()
        
        # Crear un modelo simple
        modelo = ModeloVehiculo(
            modelo="Test Modelo 2023",
            activo=True
        )
        db.add(modelo)
        db.flush()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Datos simples creados exitosamente",
            "details": {
                "asesor_id": asesor.id,
                "concesionario_id": concesionario.id,
                "modelo_id": modelo.id
            }
        }
        
    except Exception as e:
        logger.error(f"Error creando datos simples: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creando datos simples: {str(e)}"
        )
