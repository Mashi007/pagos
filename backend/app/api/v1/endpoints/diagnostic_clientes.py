"""
Endpoint de diagnóstico para verificar el estado del endpoint de clientes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.user import User
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/test-db-connection")
def test_db_connection(db: Session = Depends(get_db)):
    """
    Probar conexión a base de datos
    """
    try:
        # Contar clientes
        total_clientes = db.query(Cliente).count()
        
        # Contar usuarios
        total_usuarios = db.query(User).count()
        
        # Probar query simple
        clientes_sample = db.query(Cliente).limit(3).all()
        
        return {
            "status": "success",
            "database_connection": "ok",
            "total_clientes": total_clientes,
            "total_usuarios": total_usuarios,
            "sample_clientes": [
                {
                    "id": c.id,
                    "cedula": c.cedula,
                    "nombres": c.nombres
                } for c in clientes_sample
            ],
            "message": "Conexión a base de datos funcionando correctamente"
        }
        
    except Exception as e:
        logger.error(f"Error en test_db_connection: {e}")
        return {
            "status": "error",
            "database_connection": "failed",
            "error": str(e),
            "message": "Error en conexión a base de datos"
        }

@router.get("/test-clientes-query")
def test_clientes_query(db: Session = Depends(get_db)):
    """
    Probar query de clientes sin autenticación
    """
    try:
        # Query simple sin relaciones
        clientes = db.query(Cliente).limit(5).all()
        
        clientes_data = []
        for cliente in clientes:
            try:
                cliente_data = {
                    "id": cliente.id,
                    "cedula": cliente.cedula or "",
                    "nombres": cliente.nombres or "",
                    "apellidos": cliente.apellidos or "",
                    "telefono": cliente.telefono or "",
                    "email": cliente.email or "",
                    "estado": cliente.estado or "ACTIVO",
                    "activo": cliente.activo if cliente.activo is not None else True
                }
                clientes_data.append(cliente_data)
            except Exception as serialization_error:
                logger.error(f"Error serializando cliente {cliente.id}: {serialization_error}")
                clientes_data.append({
                    "id": cliente.id,
                    "error": f"Error serializando: {str(serialization_error)}"
                })
        
        return {
            "status": "success",
            "total_clientes": len(clientes_data),
            "clientes": clientes_data,
            "message": "Query de clientes exitosa"
        }
        
    except Exception as e:
        logger.error(f"Error en test_clientes_query: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Error en query de clientes"
        }

@router.get("/test-user-roles")
def test_user_roles(db: Session = Depends(get_db)):
    """
    Verificar roles de usuarios en la base de datos
    """
    try:
        # Obtener todos los usuarios
        usuarios = db.query(User).all()
        
        usuarios_data = []
        for usuario in usuarios:
            usuarios_data.append({
                "id": usuario.id,
                "email": usuario.email,
                "rol": usuario.rol,
                "is_active": usuario.is_active,
                "nombre": usuario.nombre
            })
        
        return {
            "status": "success",
            "total_usuarios": len(usuarios_data),
            "usuarios": usuarios_data,
            "message": "Usuarios obtenidos correctamente"
        }
        
    except Exception as e:
        logger.error(f"Error en test_user_roles: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Error obteniendo usuarios"
        }
