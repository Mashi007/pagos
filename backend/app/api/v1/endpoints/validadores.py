"""Endpoints para validadores del sistema."""

import logging
from datetime import datetime

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

        # Estructura completa que espera el frontend
        return {
            "titulo": "Configuración de Validadores",
            "consultado_por": current_user.email,
            "fecha_consulta": datetime.now().isoformat(),
            "validadores_disponibles": {
                "telefono": {
                    "descripcion": "Validación y formateo de números telefónicos",
                    "auto_formateo": True,
                    "validacion_tiempo_real": True,
                    "paises_soportados": {
                        "venezuela": {
                            "codigo": "+58",
                            "formato": "+58 XXX XXX XXXX",
                            "requisitos": {
                                "debe_empezar_por": "4 o 2",
                                "longitud_total": "10 dígitos",
                                "primer_digito": "4 o 2",
                                "digitos_validos": "0-9",
                            },
                            "ejemplos_validos": ["+58 412 1234567", "+58 212 7654321"],
                            "ejemplos_invalidos": ["412 1234567", "1234567"],
                        },
                    },
                },
                "cedula": {
                    "descripcion": "Validación de cédulas por país",
                    "auto_formateo": True,
                    "validacion_tiempo_real": True,
                    "paises_soportados": {
                        "venezuela": {
                            "prefijos_validos": ["V", "E", "J"],
                            "longitud": "7-10 dígitos",
                            "requisitos": {
                                "prefijos": "V, E o J",
                                "dígitos": "7-10",
                                "longitud": "7 a 10 dígitos",
                            },
                            "ejemplos_validos": ["V12345678", "E87654321", "J1234567"],
                            "ejemplos_invalidos": ["12345678", "A1234567", "V123"],
                        },
                    },
                },
                "fecha": {
                    "descripcion": "Validación estricta de fechas",
                    "formato_requerido": "DD/MM/YYYY",
                    "auto_formateo": False,
                    "validacion_tiempo_real": True,
                    "requisitos": {
                        "dia": "01-31",
                        "mes": "01-12",
                        "año": "YYYY",
                        "separador": "/",
                    },
                    "ejemplos_validos": ["15/03/2024", "01/01/2024", "31/12/2023"],
                    "ejemplos_invalidos": ["32/01/2024", "15/13/2024", "15-03-2024"],
                    "requiere_calendario": True,
                },
                "email": {
                    "descripcion": "Validación y normalización de emails",
                    "auto_formateo": True,
                    "validacion_tiempo_real": True,
                    "caracteristicas": {
                        "normalizacion": "Minúsculas",
                        "limpieza": "Espacios y caracteres especiales",
                        "validacion": "RFC 5322",
                        "dominios_bloqueados": ["temp.com", "test.com", "example.com"],
                    },
                    "ejemplos_validos": ["usuario@dominio.com", "nombre.apellido@empresa.com"],
                    "ejemplos_invalidos": ["usuario@", "@dominio.com", "sinarroba"],
                },
            },
            "reglas_negocio": {
                "validacion_obligatoria": "Todos los campos deben validarse antes de guardar",
                "formateo_automatico": "Los datos se formatean automáticamente según reglas",
                "validacion_tiempo_real": "La validación ocurre mientras el usuario escribe",
            },
            "configuracion_frontend": {
                "version": "1.0",
                "ambiente": "production",
            },
            "endpoints_validacion": {
                "telefono": "/api/v1/validadores/validar-campo",
                "cedula": "/api/v1/validadores/validar-campo",
                "email": "/api/v1/validadores/validar-campo",
                "fecha": "/api/v1/validadores/validar-campo",
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
