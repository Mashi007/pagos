# backend/app/api/v1/endpoints/clientes_temp.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.cliente import Cliente
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/test-sin-auth")
def listar_clientes_sin_auth(db: Session = Depends(get_db)):
    """
    Endpoint temporal para probar clientes sin autenticación
    """
    try:
        # Query simple de clientes
        clientes = db.query(Cliente).limit(5).all()
        
        # Serializar manualmente
        clientes_data = []
        for cliente in clientes:
            clientes_data.append({
                "id": cliente.id,
                "cedula": cliente.cedula,
                "nombres": cliente.nombres,
                "apellidos": cliente.apellidos,
                "telefono": cliente.telefono,
                "email": cliente.email,
                "direccion": cliente.direccion,
                "estado": cliente.estado,
                "estado_financiero": cliente.estado_financiero,
                "total_financiamiento": float(cliente.total_financiamiento) if cliente.total_financiamiento else 0.0,
                "fecha_registro": cliente.fecha_registro.isoformat() if cliente.fecha_registro else None,
            })
        
        return {
            "success": True,
            "data": clientes_data,
            "total": len(clientes_data),
            "message": "Clientes obtenidos sin autenticación (test)"
        }
        
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "total": 0,
            "message": f"Error: {str(e)}"
        }


@router.get("/test-con-auth")
def listar_clientes_con_auth(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Endpoint temporal para probar clientes con autenticación
    """
    try:
        # Usuario actual ya obtenido por Depends
        
        # Query simple de clientes
        clientes = db.query(Cliente).limit(5).all()
        
        # Serializar manualmente
        clientes_data = []
        for cliente in clientes:
            clientes_data.append({
                "id": cliente.id,
                "cedula": cliente.cedula,
                "nombres": cliente.nombres,
                "apellidos": cliente.apellidos,
                "telefono": cliente.telefono,
                "email": cliente.email,
                "direccion": cliente.direccion,
                "estado": cliente.estado,
                "estado_financiero": cliente.estado_financiero,
                "total_financiamiento": float(cliente.total_financiamiento) if cliente.total_financiamiento else 0.0,
                "fecha_registro": cliente.fecha_registro.isoformat() if cliente.fecha_registro else None,
            })
        
        return {
            "success": True,
            "data": clientes_data,
            "total": len(clientes_data),
            "user_authenticated": True,
            "user_id": current_user.id,
            "user_role": current_user.rol,
            "message": "Clientes obtenidos con autenticación (test)"
        }
        
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "total": 0,
            "user_authenticated": False,
            "message": f"Error de autenticación: {str(e)}"
        }
