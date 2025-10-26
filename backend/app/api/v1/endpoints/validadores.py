"""
Endpoints para validadores del sistema
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/configuracion-validadores")
def obtener_configuracion_validadores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener configuración de validadores disponibles
    """
    try:
        logger.info(f"Obteniendo configuración de validadores - Usuario: {current_user.email}")
        
        # Configuración de validadores disponibles
        validadores = {
            "cedula": {
                "nombre": "Cédula",
                "descripcion": "Valida y formatea cédulas venezolanas (V/E/J + 7-10 dígitos)",
                "ejemplo": "V12345678",
                "activo": True,
                "pais": "VE",
            },
            "telefono": {
                "nombre": "Teléfono",
                "descripcion": "Valida y formatea teléfonos venezolanos (+58 + 10 dígitos)",
                "ejemplo": "+58 424 1234567",
                "activo": True,
                "pais": "VE",
            },
            "email": {
                "nombre": "Email",
                "descripcion": "Valida y normaliza emails RFC 5322",
                "ejemplo": "usuario@dominio.com",
                "activo": True,
            },
            "fecha": {
                "nombre": "Fecha",
                "descripcion": "Valida fechas con reglas de negocio (DD/MM/YYYY)",
                "ejemplo": "15/03/2024",
                "activo": True,
            },
        }
        
        return {
            "total_validadores": len(validadores),
            "validadores": validadores,
            "paises_soportados": ["VE"],
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo configuración de validadores: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/probar-validador")
def probar_validador(
    tipo: str,
    valor: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Probar un validador específico con un valor de prueba
    """
    try:
        logger.info(f"Probando validador {tipo} - Usuario: {current_user.email}")
        
        # Importar validador correspondiente
        from app.services.validators_service import (
            ValidadorCedula,
            ValidadorTelefono,
        )
        
        resultado = {}
        
        if tipo == "cedula":
            resultado = ValidadorCedula.validar_y_formatear_cedula(valor)
        elif tipo == "telefono":
            resultado = ValidadorTelefono.validar_y_formatear_telefono(valor, "VE")
        elif tipo == "email":
            # Validación simple de email
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            es_valido = re.match(email_pattern, valor)
            resultado = {
                "valido": es_valido is not None,
                "error": "" if es_valido else "Formato de email inválido",
                "valor_original": valor,
                "valor_formateado": valor.lower() if es_valido else None,
                "cambio_realizado": False,
            }
        elif tipo == "fecha":
            # Validación simple de fecha
            try:
                from datetime import datetime
                fecha = datetime.strptime(valor, "%d/%m/%Y")
                resultado = {
                    "valido": True,
                    "error": "",
                    "valor_original": valor,
                    "valor_formateado": valor,
                    "cambio_realizado": False,
                }
            except ValueError:
                resultado = {
                    "valido": False,
                    "error": "Formato de fecha inválido (usar DD/MM/YYYY)",
                    "valor_original": valor,
                    "valor_formateado": None,
                    "cambio_realizado": False,
                }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de validador desconocido: {tipo}"
            )
        
        return {
            "tipo": tipo,
            "valor_original": valor,
            "resultado": resultado,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error probando validador {tipo}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

