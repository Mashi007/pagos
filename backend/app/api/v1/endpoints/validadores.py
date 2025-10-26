"""Endpoints para validadores del sistema."""

import logging

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class ValidarCampoRequest(BaseModel):
    """Request para validar campo individual"""
    campo: str
    valor: str
    pais: str = "VENEZUELA"
    moneda: Optional[str] = None


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
                    "debe_empezar_por": "Debe tener prefijo +58 (se agrega automáticamente si falta)",
                    "longitud_total": "12 dígitos (código país + 10 dígitos locales)",
                    "formato": "Cualquier orden de 10 dígitos válidos",
                    "no_puede_empezar_por": "0 - NO se aceptan números que empiecen por 0",
                    "digitos_validos": "10 dígitos (1-9 al inicio, cualquier orden)",
                },
                "patron_regex": r"^\+58\s?[1-9][0-9]{9}$",
                "formato_display": "+58 XXXXXXXXXX (10 dígitos, no empieza por 0)",
                "ejemplos": "+58 1234567890, +58 9876543210, 1234567890",
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
                "descripcion": "Validación de montos (rango 1-20000) con soporte USD y VES - Formato europeo estricto",
                "requisitos": {
                    "formato": "Sistema europeo estricto: coma (,) para decimales, punto (.) para miles",
                    "separador_decimal": "Coma (,) OBLIGATORIA para decimales",
                    "separador_miles": "Punto (.) OBLIGATORIO si el número es mayor a 999 (cada 3 dígitos desde derecha)",
                    "reglas": {
                        "formato_valido": "1.000,12 o 10.500,25",
                        "formato_invalido": "1.500.50 (punto decimal), 1,500.50 (coma miles), 1500,50 (sin miles cuando > 999), 20000 (sin miles)"
                    },
                    "ejemplos": {
                        "validos": "1.000,12 (mil con decimales), 1.500,50 (con miles), 10.500,25 (grandes con miles)",
                        "invalidos": "1500.50 (punto decimal), 1,500.50 (coma miles), 1500,50 (sin miles > 999), 20000 (sin miles > 999)"
                    },
                    "rango_minimo": "USD$1,00 o VES Bs.1,00",
                    "rango_maximo": "USD$20.000,00 o VES Bs.20.000,00",
                    "monedas_soportadas": {
                        "USD": "Dólares Americanos",
                        "VES": "Bolívares Venezolanos",
                    },
                },
            },
            "nombre": {
                "descripcion": "Validación de nombres (1-2 palabras) con primera letra mayúscula",
                "requisitos": {
                    "palabras": "Máximo 2 palabras",
                    "longitud_minima": "2 caracteres por palabra",
                    "longitud_maxima": "40 caracteres por palabra",
                    "formato": "Solo letras, espacios y caracteres especiales permitidos",
                },
                "patron_regex": r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s\-']{2,}$",
            },
            "apellido": {
                "descripcion": "Validación de apellidos (1-2 palabras) con primera letra mayúscula",
                "requisitos": {
                    "palabras": "Máximo 2 palabras",
                    "longitud_minima": "2 caracteres por palabra",
                    "longitud_maxima": "40 caracteres por palabra",
                    "formato": "Solo letras, espacios y caracteres especiales permitidos",
                },
                "patron_regex": r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s\-']{2,}$",
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
        from app.services.validators_service import (
            ValidadorCedula,
            ValidadorEmail,
            ValidadorFecha,
            ValidadorNombre,
            ValidadorTelefono,
        )

        resultado = {}

        if tipo == "cedula":
            resultado = ValidadorCedula.validar_y_formatear_cedula(valor)
        elif tipo == "telefono":
            resultado = ValidadorTelefono.validar_y_formatear_telefono(valor, "VE")
        elif tipo == "nombre" or tipo == "apellido":
            resultado = ValidadorNombre.validar_y_formatear_nombre(valor)
        elif tipo == "email":
            resultado = ValidadorEmail.validar_y_formatear_email(valor)
        elif tipo == "fecha":
            resultado = ValidadorFecha.validar_y_formatear_fecha(valor)
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


@router.post("/validar-campo")
def validar_campo(
    request: ValidarCampoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Validar un campo específico con un valor"""
    try:
        logger.info(f"Validando campo {request.campo} - Usuario: {current_user.email}")

        # Mapear campos del frontend a validadores
        campo_map = {
            "cedula_venezuela": "cedula",
            "telefono_venezuela": "telefono",
            "email": "email",
            "fecha": "fecha",
            "monto": "monto",
            "nombre": "nombre",
            "apellido": "apellido",
        }

        tipo = campo_map.get(request.campo, request.campo)

        # Importar validador correspondiente
        from app.services.validators_service import (
            ValidadorCedula,
            ValidadorEmail,
            ValidadorFecha,
            ValidadorMonto,
            ValidadorNombre,
            ValidadorTelefono,
        )

        resultado = {}

        if tipo == "cedula":
            resultado = ValidadorCedula.validar_y_formatear_cedula(request.valor, request.pais)
        elif tipo == "telefono":
            resultado = ValidadorTelefono.validar_y_formatear_telefono(request.valor, request.pais)
        elif tipo == "nombre" or tipo == "apellido":
            resultado = ValidadorNombre.validar_y_formatear_nombre(request.valor)
        elif tipo == "email":
            resultado = ValidadorEmail.validar_y_formatear_email(request.valor)
        elif tipo == "fecha":
            resultado = ValidadorFecha.validar_y_formatear_fecha(request.valor)
        elif tipo == "monto":
            moneda = request.moneda or "USD"
            resultado = ValidadorMonto.validar_y_formatear_monto(request.valor, moneda)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de validador desconocido: {tipo}",
            )

        # Estructura que espera el frontend
        return {
            "validacion": resultado
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validando campo {request.campo}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )
