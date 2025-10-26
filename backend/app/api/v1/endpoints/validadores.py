"""Endpoints para validadores del sistema."""

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
    """Obtener configuración de validadores disponibles."""
    try:
        logger.info(
            f"Obteniendo configuración de validadores - Usuario: {current_user.email}"
        )

        # Estructura que espera el frontend
        return {
            "cedula_venezuela": {
                "descripcion": "Validación de cédulas venezolanas con prefijos V, E o J",
                "requisitos": {
                    "debe_empezar_por": "V, E o J (prefijo)",
                    "longitud_digitos": "7 a 10 dígitos después del prefijo",
                    "sin_caracteres_especiales": "Solo letras y números",
                },
                "patron_regex": "^(V|E|J)[0-9]{7,10}$",
                "formato_display": "V12345678, E87654321, J1234567",
                "tipos": {
                    "V": "Venezolano",
                    "E": "Extranjero",
                    "J": "Jurídico",
                },
            },
            "telefono_venezuela": {
                "descripcion": "Validación y formateo de teléfonos venezolanos con código +58",
                "requisitos": {
                    "debe_empezar_por": "4 o 2",
                    "longitud_total": 10,
                    "primer_digito": "4 o 2",
                },
                "patron_regex": r"^\+58\s?[4-9]\d{2}\s?\d{7}$",
                "formato_display": "+58 XXX XXX XXXX",
            },
            "email": {
                "descripcion": "Validación de emails según RFC 5322 con normalización",
                "requisitos": {
                    "formato": "usuario@dominio.com",
                    "normalizacion": "Minúsculas automáticas",
                },
                "patron_regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            },
            "fecha": {
                "descripcion": "Validación de fechas en formato DD/MM/YYYY",
                "requisitos": {
                    "formato": "DD/MM/YYYY",
                    "dia": "01-31",
                    "mes": "01-12",
                    "año": "YYYY",
                },
                "patron_regex": r"^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/\d{4}$",
            },
            "monto": {
                "descripcion": "Validación de montos con decimales y formato monetario",
                "requisitos": {
                    "formato": "Decimal con 2 posiciones",
                    "decimales": "Siempre mostrar .00",
                    "separador_miles": "Coma (,)",
                    "simbolo_moneda": "Bs.",
                },
            },
        }

    except Exception as e:
        logger.error(f"Error obteniendo configuración de validadores: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )


@router.post("/probar-validador")
def probar_validador(
    tipo: str,
    valor: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Probar un validador específico con un valor de prueba."""
    try:
        logger.info(f"Probando validador {tipo} - Usuario: {current_user.email}")

        # Importar validador correspondiente
        from app.services.validators_service import ValidadorCedula, ValidadorTelefono

        resultado = {}

        if tipo == "cedula":
            resultado = ValidadorCedula.validar_y_formatear_cedula(valor)
        elif tipo == "telefono":
            resultado = ValidadorTelefono.validar_y_formatear_telefono(valor, "VE")
        elif tipo == "email":
            # Validación simple de email
            import re

            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
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

                datetime.strptime(valor, "%d/%m/%Y")  # Solo validar, no asignar
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
                detail=f"Tipo de validador desconocido: {tipo}",
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
            detail=f"Error interno del servidor: {str(e)}",
        )
