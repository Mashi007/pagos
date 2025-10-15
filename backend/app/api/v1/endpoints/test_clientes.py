"""
Endpoint de prueba para diagnosticar problema con clientes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.cliente import Cliente
from app.api.deps import get_current_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/test-simple")
def test_clientes_simple(db: Session = Depends(get_db)):
    """
    🧪 Test simple sin autenticación para verificar conexión
    """
    try:
        # Contar clientes
        count = db.query(Cliente).count()
        
        return {
            "message": "✅ Conexión a base de datos OK",
            "total_clientes": count,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"❌ Error en test simple: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/test-with-auth")
def test_clientes_with_auth(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🧪 Test con autenticación para verificar usuario
    """
    try:
        # Información del usuario
        user_info = {
            "id": current_user.id,
            "email": current_user.email,
            "nombre": current_user.nombre,
            "rol": current_user.rol,
            "active": current_user.is_active
        }
        
        # Contar clientes
        count = db.query(Cliente).count()
        
        return {
            "message": "✅ Autenticación y conexión OK",
            "user": user_info,
            "total_clientes": count,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"❌ Error en test con auth: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/test-list")
def test_listar_clientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🧪 Test de listado de clientes simplificado
    """
    try:
        # Query simple
        clientes = db.query(Cliente).limit(5).all()
        
        # Serialización simple
        clientes_list = []
        for cliente in clientes:
            clientes_list.append({
                "id": cliente.id,
                "cedula": cliente.cedula,
                "nombres": cliente.nombres,
                "apellidos": cliente.apellidos,
                "telefono": cliente.telefono,
                "email": cliente.email,
                "estado": cliente.estado,
                "activo": cliente.activo,
                "fecha_registro": cliente.fecha_registro.isoformat() if cliente.fecha_registro else None
            })
        
        return {
            "message": "✅ Listado de clientes OK",
            "total_encontrados": len(clientes_list),
            "clientes": clientes_list,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"❌ Error en test listado: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/test-relations")
def test_relaciones_clientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🧪 Test de relaciones de clientes
    """
    try:
        # Test de relaciones
        from app.models.asesor import Asesor
        from app.models.concesionario import Concesionario
        from app.models.modelo_vehiculo import ModeloVehiculo
        
        # Contar registros en tablas relacionadas
        asesores_count = db.query(Asesor).count()
        concesionarios_count = db.query(Concesionario).count()
        modelos_count = db.query(ModeloVehiculo).count()
        
        return {
            "message": "✅ Relaciones verificadas",
            "asesores": asesores_count,
            "concesionarios": concesionarios_count,
            "modelos_vehiculos": modelos_count,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"❌ Error en test relaciones: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
