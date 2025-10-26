# backend/app/services/validators_service.py
"""Servicio de Validadores y Auto-Formateo

Sistema completo para validar y formatear datos de entrada
"""

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ValidadorTelefono:
    """Validador y formateador de teléfonos"""

    PAISES_CONFIG = {
        "VENEZUELA": {
            "codigo_pais": "+58",
            "operadoras": ["412", "414", "416", "424", "426"],
            "longitud_sin_codigo": 10,  # 809 1234567
            "patron_completo": r"^\+58\s?[0-9]{3}\s?[0-9]{7}$",
            "formato_display": "+58 XXX XXXXXXX",
        },
        "COLOMBIA": {
            "codigo_pais": "+57",
            "operadoras": ["300", "301", "302", "310", "311"],
            "longitud_sin_codigo": 10,
            "patron_completo": r"^\+57\s?[0-9]{3}\s?[0-9]{7}$",
            "formato_display": "+57 XXX XXXXXXX",
        },
    }

    @staticmethod
    def _validar_entrada_telefono(telefono: str) -> Optional[Dict[str, Any]]:
        """Validar entrada básica de teléfono"""
        if not telefono:
            return {
                "valido": False,
                "error": "Teléfono requerido",
                "valor_original": telefono,
                "valor_formateado": None,
            }
        return None

    @staticmethod
    def _validar_pais_soportado(pais: str, telefono: str) -> Optional[Dict[str, Any]]:
        """Validar que el país esté soportado"""
        config = ValidadorTelefono.PAISES_CONFIG.get(pais.upper())
        if not config:
            return {
                "valido": False,
                "error": f"País '{pais}' no soportado",
                "valor_original": telefono,
                "valor_formateado": None,
            }
        return config

    @staticmethod
    def _formatear_telefono_con_codigo(
        telefono_limpio: str, config: Dict[str, Any]
    ) -> str:
        """Formatear teléfono que ya tiene código de país"""
        return (
            config["codigo_pais"]
            + " "
            + telefono_limpio[3:6]
            + " "
            + telefono_limpio[6:]
        )

    @staticmethod
    def _formatear_telefono_con_plus(
        telefono_limpio: str, config: Dict[str, Any]
    ) -> str:
        """Formatear teléfono que ya tiene + y código"""
        numero_sin_plus = telefono_limpio[1:]
        return (
            config["codigo_pais"]
            + " "
            + numero_sin_plus[:2]
            + " "
            + numero_sin_plus[2:5]
            + " "
            + numero_sin_plus[5:]
        )

    @staticmethod
    def _formatear_telefono_local(
        telefono_limpio: str,
        config: Dict[str, Any],
        pais: str,
        telefono_original: str,
    ) -> Dict[str, Any]:
        """Formatear teléfono local sin código de país"""
        operadora = telefono_limpio[:3]

        if operadora in config["operadoras"]:
            numero_formateado = (
                f"{config['codigo_pais']} {operadora} {telefono_limpio[3:]}"
            )
            return {
                "valido": True,
                "numero_formateado": numero_formateado,
            }
        else:
            return {
                "valido": False,
                "error": (
                    f"Operadora '{operadora}' no válida "
                    f"para {pais}. Válidas: {', '.join(config['operadoras'])}"
                ),
                "valor_original": telefono_original,
                "valor_formateado": None,
                "sugerencia": f"Debe comenzar con: {', '.join(config['operadoras'])}",
            }

    @staticmethod
    def _validar_formato_final(
        numero_formateado: str, config: Dict[str, Any], telefono_original: str
    ) -> Dict[str, Any]:
        """Validar formato final del teléfono"""
        if re.match(config["patron_completo"], numero_formateado):
            return {
                "valido": True,
                "valor_original": telefono_original,
                "valor_formateado": numero_formateado,
                "operadora": numero_formateado.split()[1],
                "cambio_realizado": telefono_original != numero_formateado,
            }
        else:
            return {
                "valido": False,
                "error": "Formato final inválido",
                "valor_original": telefono_original,
                "valor_formateado": numero_formateado,
            }

    @staticmethod
    def validar_y_formatear_telefono(
        telefono: str, pais: str = "VENEZUELA"
    ) -> Dict[str, Any]:
        """
        Validar y formatear teléfono según país

        Ejemplos:
        - "584241234567" → "+58 424 1234567"
        - "424 1234567" → "+58 424 1234567"
        - "+58 424 1234567" → "+58 424 1234567" (ya correcto)
        """
        try:
            # 1. Validar entrada básica
            error_entrada = ValidadorTelefono._validar_entrada_telefono(telefono)
            if error_entrada:
                return error_entrada

            # 2. Limpiar entrada
            telefono_limpio = re.sub(r"[^\d+]", "", telefono.strip())

            # 3. Validar país soportado
            config = ValidadorTelefono._validar_pais_soportado(pais, telefono)
            if isinstance(config, dict) and "valido" in config:
                return config

            # 4. Determinar formato y procesar
            numero_formateado = None

            if config and telefono_limpio.startswith(
                config["codigo_pais"].replace("+", "")
            ):
                # Ya tiene código de país: "584241234567"
                numero_formateado = ValidadorTelefono._formatear_telefono_con_codigo(
                    telefono_limpio, config
                )
            elif config and telefono_limpio.startswith(config["codigo_pais"]):
                # Ya tiene + y código: "+584241234567"
                numero_formateado = ValidadorTelefono._formatear_telefono_con_plus(
                    telefono_limpio, config
                )
            elif config and len(telefono_limpio) == config["longitud_sin_codigo"]:
                # Solo número local: "4241234567"
                resultado_local = ValidadorTelefono._formatear_telefono_local(
                    telefono_limpio, config, pais, telefono
                )
                if resultado_local["error"]:
                    return resultado_local["error"]
                numero_formateado = resultado_local["numero_formateado"]
            else:
                return {
                    "valido": False,
                    "error": (
                        f"Longitud incorrecta. Formato esperado: "
                        f"{config['formato_display'] if config else 'N/A'}"
                    ),
                    "valor_original": telefono,
                    "valor_formateado": None,
                    "longitud_actual": len(telefono_limpio),
                    "longitud_esperada": config["longitud_sin_codigo"] if config else 0,
                }

            # 6. Validar formato final
            return ValidadorTelefono._validar_formato_final(
                numero_formateado, config, telefono
            )

        except Exception as e:
            logger.error(f"Error validando teléfono: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": telefono,
                "valor_formateado": None,
            }


class ValidadorCedula:
    """Validador y formateador de cédulas"""

    PAISES_CEDULA = {
        "VENEZUELA": {
            "longitud": [7, 8],
            "patron": r"^[Vv]?\d{7,8}$",
            "formato_display": "V12345678",
            "descripcion": "Cédula venezolana",
        },
        "COLOMBIA": {
            "longitud": [8, 10],
            "patron": r"^\d{8,10}$",
            "formato_display": "12345678",
            "descripcion": "Cédula colombiana",
        },
    }

    @staticmethod
    def validar_y_formatear_cedula(
        cedula: str, pais: str = "VENEZUELA"
    ) -> Dict[str, Any]:
        """
        Validar y formatear cédula según país

        Ejemplos:
        - "12345678" → "V12345678"
        - "v12345678" → "V12345678"
        - "V12345678" → "V12345678" (ya correcto)
        """
        try:
            if not cedula:
                return {
                    "valido": False,
                    "error": "Cédula requerida",
                    "valor_original": cedula,
                    "valor_formateado": None,
                }

            # Limpiar entrada
            cedula_limpia = cedula.strip().upper()

            # Validar país
            config = ValidadorCedula.PAISES_CEDULA.get(pais.upper())
            if not config:
                return {
                    "valido": False,
                    "error": f"País '{pais}' no soportado",
                    "valor_original": cedula,
                    "valor_formateado": None,
                }

            # Validar formato
            if not re.match(config["patron"], cedula_limpia):
                return {
                    "valido": False,
                    "error": f"Formato inválido para {config['descripcion']}",
                    "valor_original": cedula,
                    "valor_formateado": None,
                    "formato_esperado": config["formato_display"],
                }

            # Formatear según país
            if pais.upper() == "VENEZUELA":
                if cedula_limpia.startswith("V"):
                    cedula_formateada = cedula_limpia
                else:
                    cedula_formateada = f"V{cedula_limpia}"
            else:
                cedula_formateada = cedula_limpia

            return {
                "valido": True,
                "valor_original": cedula,
                "valor_formateado": cedula_formateada,
                "pais": pais.upper(),
                "cambio_realizado": cedula != cedula_formateada,
            }

        except Exception as e:
            logger.error(f"Error validando cédula: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": cedula,
                "valor_formateado": None,
            }


class ValidadorMonto:
    """Validador y formateador de montos"""

    @staticmethod
    def validar_y_formatear_monto(monto: Any) -> Dict[str, Any]:
        """
        Validar y formatear monto monetario

        Args:
            monto: Monto a validar (str, int, float, Decimal)

        Returns:
            Dict con resultado de validación y formateo
        """
        try:
            if monto is None:
                return {
                    "valido": False,
                    "error": "Monto requerido",
                    "valor_original": monto,
                    "valor_formateado": None,
                }

            # Convertir a Decimal
            try:
                if isinstance(monto, str):
                    # Limpiar string
                    monto_limpio = re.sub(r"[^\d.,]", "", monto)
                    monto_decimal = Decimal(monto_limpio.replace(",", "."))
                else:
                    monto_decimal = Decimal(str(monto))
            except (InvalidOperation, ValueError):
                return {
                    "valido": False,
                    "error": "Formato de monto inválido",
                    "valor_original": monto,
                    "valor_formateado": None,
                }

            # Validar rango
            if monto_decimal < 0:
                return {
                    "valido": False,
                    "error": "El monto no puede ser negativo",
                    "valor_original": monto,
                    "valor_formateado": None,
                }

            if monto_decimal > Decimal("999999999.99"):
                return {
                    "valido": False,
                    "error": "Monto excede el límite máximo",
                    "valor_original": monto,
                    "valor_formateado": None,
                }

            # Formatear con 2 decimales
            monto_formateado = monto_decimal.quantize(Decimal("0.01"))

            return {
                "valido": True,
                "valor_original": monto,
                "valor_formateado": float(monto_formateado),
                "valor_decimal": monto_formateado,
                "cambio_realizado": str(monto) != str(monto_formateado),
            }

        except Exception as e:
            logger.error(f"Error validando monto: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": monto,
                "valor_formateado": None,
            }


def _validar_campo_cliente(
    campo: str, valor: Any, validador_func, resultados: Dict[str, Any]
) -> None:
    """Validar un campo específico del cliente"""
    resultado = validador_func(valor)
    if resultado["valido"]:
        resultados["datos_formateados"][campo] = resultado["valor_formateado"]
        if resultado["cambio_realizado"]:
            resultados["cambios_realizados"].append(campo)
    else:
        resultados["valido"] = False
        resultados["errores"].append(f"{campo.title()}: {resultado['error']}")


def validar_datos_cliente(cliente_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validar y formatear datos completos de cliente

    Args:
        cliente_data: Diccionario con datos del cliente

    Returns:
        Dict con resultado de validación de todos los campos
    """
    resultados = {
        "valido": True,
        "errores": [],
        "datos_formateados": {},
        "cambios_realizados": [],
    }

    # Validar teléfono
    if "telefono" in cliente_data:
        _validar_campo_cliente(
            "telefono",
            cliente_data["telefono"],
            ValidadorTelefono.validar_y_formatear_telefono,
            resultados,
        )

    # Validar cédula
    if "cedula" in cliente_data:
        _validar_campo_cliente(
            "cedula",
            cliente_data["cedula"],
            ValidadorCedula.validar_y_formatear_cedula,
            resultados,
        )

    # Validar montos
    campos_monto = ["ingreso_mensual", "total_financiamiento"]
    for campo in campos_monto:
        if campo in cliente_data:
            _validar_campo_cliente(
                campo,
                cliente_data[campo],
                ValidadorMonto.validar_y_formatear_monto,
                resultados,
            )

    return resultados
