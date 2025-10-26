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
            "patron_completo": r"^\+58\s?[1-9][0-9]{9}$",
            "formato_display": "+58 XXXXXXXXXX (10 dígitos, no empieza por 0)",
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
        """Formatear teléfono que ya tiene + y código (ejemplo: +581234567890)"""
        # Eliminar el + y el código de país (58)
        # telefono_limpio = "+581234567890"
        # Quitar "+58" (3 caracteres, no 4!)
        numero_sin_codigo = telefono_limpio[len(config["codigo_pais"]):]  # noqa: E203
        # numero_sin_codigo = "1234567890"

        # Retornar con formato: +58 + 10 dígitos
        return f"{config['codigo_pais']} {numero_sin_codigo}"

    @staticmethod
    def _formatear_telefono_local(
        telefono_limpio: str,
        config: Dict[str, Any],
        pais: str,
        telefono_original: str,
    ) -> Dict[str, Any]:
        """Formatear teléfono local sin código de país"""
        # Validar que no empiece por 0
        if telefono_limpio.startswith("0"):
            return {
                "valido": False,
                "error": "El número NO puede empezar por 0",
                "valor_original": telefono_original,
                "valor_formateado": None,
                "formato_esperado": "10 dígitos (1-9 al inicio)",
                "sugerencia": "Use un número que empiece por 1-9. Ejemplo: '4121234567'",
            }

        # Validar longitud exacta (10 dígitos)
        if len(telefono_limpio) != config["longitud_sin_codigo"]:
            return {
                "valido": False,
                "error": f"El número debe tener exactamente {config['longitud_sin_codigo']} dígitos",
                "valor_original": telefono_original,
                "valor_formateado": None,
                "formato_esperado": f"{config['longitud_sin_codigo']} dígitos",
                "sugerencia": (
                    f"El número debe tener exactamente {config['longitud_sin_codigo']} dígitos. "
                    f"Usted ingresó {len(telefono_limpio)}. Ejemplo: '1234567890'"
                ),
            }

        # Formatear: +58 + 10 dígitos
        numero_formateado = f"{config['codigo_pais']} {telefono_limpio}"
        return {
            "valido": True,
            "numero_formateado": numero_formateado,
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
                "formato_esperado": "+58 XXXXXXXXXX (10 dígitos)",
                "sugerencia": (
                    "El número debe tener exactamente 10 dígitos después de +58. "
                    "Ejemplos: '+58 1234567890', '+58 9876543210'"
                ),
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

            # 3. Validar que NO empiece por 0
            # Extraer solo dígitos para validar
            solo_digitos = re.sub(r"[^\d]", "", telefono_limpio)
            if solo_digitos and solo_digitos[0] == "0":
                return {
                    "valido": False,
                    "error": "El número de teléfono NO puede empezar por 0",
                    "valor_original": telefono,
                    "valor_formateado": None,
                    "formato_esperado": "10 dígitos (1-9 al inicio)",
                    "sugerencia": "Use un número que empiece por 1-9. Ejemplo: '1234567890'",
                }

            # 4. Validar país soportado
            config = ValidadorTelefono._validar_pais_soportado(pais, telefono)
            if isinstance(config, dict) and "valido" in config:
                return config

            # 5. Agregar +58 automáticamente si no tiene
            if not telefono_limpio.startswith("+") and not telefono_limpio.startswith(
                config["codigo_pais"].replace("+", "")
            ):
                # No tiene +58 ni 58, agregar +58
                telefono_limpio = config["codigo_pais"].replace("+", "") + telefono_limpio

            # 6. Determinar formato y procesar
            numero_formateado = None

            if config and telefono_limpio.startswith(
                config["codigo_pais"].replace("+", "")
            ):
                # Ya tiene código de país: "584241234567"
                # Agregar + al inicio si no lo tiene
                if not telefono_limpio.startswith("+"):
                    telefono_limpio = "+" + telefono_limpio
                numero_formateado = ValidadorTelefono._formatear_telefono_con_plus(
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
                    "error": f"Formato inválido. Longitud: {len(telefono_limpio)}",
                    "valor_original": telefono,
                    "valor_formateado": None,
                    "formato_esperado": config["formato_display"] if config else "N/A",
                    "sugerencia": f"Ingrese 10 dígitos (sin espacios). Ejemplo: '4241234567' o '{config['formato_display']}'",
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
                "formato_esperado": "+58 XXXXXXXXXX (10 dígitos)",
                "sugerencia": "Verifique que el número tenga formato válido. Ejemplo: '+58 1234567890'",
            }


class ValidadorCedula:
    """Validador y formateador de cédulas"""

    PAISES_CEDULA = {
        "VENEZUELA": {
            "longitud": [7, 8, 9, 10],
            "patron": r"^[VvEeJj]?\d{7,10}$",
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
                    "formato_esperado": "V, E o J + 7-10 dígitos",
                    "sugerencia": "Ingrese una cédula. Ejemplo: 'V12345678'",
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
                    "formato_esperado": "V, E o J + 7-10 dígitos (Venezuela)",
                    "sugerencia": "País no soportado. Use 'Venezuela'. Ejemplo: 'V12345678'",
                }

            # Validar formato
            if not re.match(config["patron"], cedula_limpia):
                if pais.upper() == "VENEZUELA":
                    return {
                        "valido": False,
                        "error": f"Formato inválido para {config['descripcion']}",
                        "valor_original": cedula,
                        "valor_formateado": None,
                        "formato_esperado": "V, E o J + 7-10 dígitos",
                        "sugerencia": (
                            "Use prefijo V (venezolano), E (extranjero) o J (jurídico) "
                            "seguido de 7-10 dígitos. Ejemplos: 'V12345678', 'E87654321', 'J9876543'"
                        ),
                    }
                else:
                return {
                    "valido": False,
                    "error": f"Formato inválido para {config['descripcion']}",
                    "valor_original": cedula,
                    "valor_formateado": None,
                    "formato_esperado": config["formato_display"],
                }

            # Formatear según país
            if pais.upper() == "VENEZUELA":
                # Detectar prefijo V, E o J
                if cedula_limpia.startswith(("V", "E", "J")):
                    cedula_formateada = cedula_limpia
                else:
                    # Por defecto usar V
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
                "formato_esperado": "V, E o J + 7-10 dígitos",
                "sugerencia": "Verifique el formato de la cédula. Ejemplo: 'V12345678'",
            }


class ValidadorFecha:
    """Validador y formateador de fechas"""

    @staticmethod
    def _validar_rangos_fecha(dia: int, mes: int, año: int, fecha: str) -> Optional[Dict[str, Any]]:
        """Validar rangos de día, mes y año"""
        if año < 1000 or año > 9999:
            return {
                "valido": False,
                "error": "El año debe tener 4 dígitos",
                "valor_original": fecha,
                "valor_formateado": None,
                "formato_esperado": "DD/MM/YYYY",
                "sugerencia": f"El año '{año}' debe tener 4 dígitos. Use año completo como: 2025",
            }
        if mes < 1 or mes > 12:
            return {
                "valido": False,
                "error": f"El mes {mes} es inválido",
                "valor_original": fecha,
                "valor_formateado": None,
                "formato_esperado": "DD/MM/YYYY",
                "sugerencia": "Los meses van del 01 al 12. Ejemplos: 15/01/2025, 20/12/2025",
            }
        if dia < 1 or dia > 31:
            return {
                "valido": False,
                "error": f"El día {dia} es inválido",
                "valor_original": fecha,
                "valor_formateado": None,
                "formato_esperado": "DD/MM/YYYY",
                "sugerencia": "Los días van del 01 al 31. Ejemplos: 01/05/2025, 31/12/2025",
            }
        return None

    @staticmethod
    def _validar_fecha_real(dia: int, mes: int, año: int, fecha: str) -> Optional[Dict[str, Any]]:
        """Validar que la fecha sea real (ej. no existe 31 de febrero)"""
        from datetime import datetime
        try:
            datetime.strptime(f"{dia:02d}/{mes:02d}/{año}", "%d/%m/%Y")
            return None
        except ValueError:
            return {
                "valido": False,
                "error": "Fecha inválida",
                "valor_original": fecha,
                "valor_formateado": None,
                "formato_esperado": "DD/MM/YYYY",
                "sugerencia": f"La fecha {dia}/{mes}/{año} no existe. Use una fecha válida (no existe 31 de febrero).",
            }

    @staticmethod
    def validar_y_formatear_fecha(fecha: Any) -> Dict[str, Any]:
        """
        Validar y formatear fecha en formato DD/MM/YYYY

        Args:
            fecha: Fecha a validar (formato DD/MM/YYYY)

        Returns:
            Dict con resultado de validación y formateo
        """
        try:
            if not fecha or not isinstance(fecha, str):
                return {
                    "valido": False,
                    "error": "Fecha requerida",
                    "valor_original": fecha,
                    "valor_formateado": None,
                    "formato_esperado": "DD/MM/YYYY",
                    "sugerencia": "Ingrese una fecha. Ejemplo: '01/12/2025'",
                }

            fecha_original = fecha.strip()

            # Intentar parsear la fecha en formato DD/MM/YYYY
            # Pero primero aceptar variaciones como D/M/YYYY o DD/M/YYYY
            try:
                # Intentar con formato completo DD/MM/YYYY
                partes = fecha_original.split('/')
                if len(partes) != 3:
                    return {
                        "valido": False,
                        "error": "Formato inválido, debe usar barras /",
                        "valor_original": fecha,
                        "valor_formateado": None,
                        "formato_esperado": "DD/MM/YYYY",
                        "sugerencia": "Use formato día/mes/año. Ejemplo: '15/03/2024' o '1/3/2024'",
                    }

                dia_str, mes_str, año_str = partes

                # Validar formato estricto DD/MM/YYYY (día y mes con 2 dígitos)
                if len(dia_str) != 2 or len(mes_str) != 2:
                    return {
                        "valido": False,
                        "error": "Día y mes deben tener 2 dígitos",
                        "valor_original": fecha,
                        "valor_formateado": None,
                        "formato_esperado": "DD/MM/YYYY",
                        "sugerencia": "Use 2 dígitos para día y mes. Ejemplo: '01/12/2025' en lugar de '1/12/2025'",
                    }

                # Convertir a enteros para validar
                dia = int(dia_str)
                mes = int(mes_str)
                año = int(año_str)

                # Validar rangos de día, mes y año
                error_rangos = ValidadorFecha._validar_rangos_fecha(dia, mes, año, fecha)
                if error_rangos:
                    return error_rangos

                # Validar que la fecha sea real
                error_fecha_real = ValidadorFecha._validar_fecha_real(dia, mes, año, fecha)
                if error_fecha_real:
                    return error_fecha_real

                # Formatear: día y mes siempre 2 dígitos, año siempre 4 dígitos
                fecha_formateada = f"{dia:02d}/{mes:02d}/{año}"

                return {
                    "valido": True,
                    "valor_original": fecha,
                    "valor_formateado": fecha_formateada,
                    "cambio_realizado": fecha_formateada != fecha_original,
                }

            except ValueError as e:
                return {
                    "valido": False,
                    "error": f"Valores de fecha inválidos: {str(e)}",
                    "valor_original": fecha,
                    "valor_formateado": None,
                    "formato_esperado": "DD/MM/YYYY",
                    "sugerencia": "Use formato día/mes/año con números. Ejemplos: '15/03/2024', '1/3/2025'",
                }

        except Exception as e:
            logger.error(f"Error validando fecha: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": fecha,
                "valor_formateado": None,
                "formato_esperado": "DD/MM/YYYY",
                "sugerencia": "Verifique el formato de la fecha. Ejemplo: '01/12/2025'",
            }


class ValidadorEmail:
    """Validador y formateador de emails"""

    @staticmethod
    def validar_y_formatear_email(email: Any) -> Dict[str, Any]:
        """
        Validar y formatear email según RFC 5322

        Args:
            email: Email a validar

        Returns:
            Dict con resultado de validación y formateo
        """
        try:
            if not email or not isinstance(email, str):
                return {
                    "valido": False,
                    "error": "Email requerido",
                    "valor_original": email,
                    "valor_formateado": None,
                    "formato_esperado": "usuario@dominio.com",
                    "sugerencia": "Ingrese un email. Ejemplo: 'usuario@ejemplo.com'",
                }

            email_original = email.strip()

            # Validar que no tenga espacios
            if ' ' in email_original:
                return {
                    "valido": False,
                    "error": "Email no puede contener espacios",
                    "valor_original": email,
                    "valor_formateado": None,
                    "formato_esperado": "usuario@dominio.com",
                    "sugerencia": "Quite los espacios. Ejemplo: 'usuario@ejemplo.com'",
                }

            # Validar que no tenga comas
            if ',' in email_original:
                return {
                    "valido": False,
                    "error": "Email no puede contener comas",
                    "valor_original": email,
                    "valor_formateado": None,
                    "formato_esperado": "usuario@dominio.com",
                    "sugerencia": "Quite las comas. Ejemplo: 'usuario@ejemplo.com'",
                }

            # Patrón RFC 5322 estricto
            # Caracteres permitidos antes del @: a-z, A-Z, 0-9, ., _, %, +, -
            # Caracteres permitidos en dominio: a-z, A-Z, 0-9, ., -
            # TLD: mínimo 2 caracteres alfabéticos
            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

            if not re.match(email_pattern, email_original):
                return {
                    "valido": False,
                    "error": "Formato de email inválido según RFC 5322",
                    "valor_original": email,
                    "valor_formateado": None,
                    "formato_esperado": "usuario@dominio.com",
                    "sugerencia": "Use formato: nombre@dominio.com. Ejemplos: 'juan@ejemplo.com', 'maria.perez@empresa.net'",
                }

            # Formatear: todo a minúsculas
            email_formateado = email_original.lower()

            return {
                "valido": True,
                "valor_original": email,
                "valor_formateado": email_formateado,
                "cambio_realizado": email_formateado != email_original,
            }

        except Exception as e:
            logger.error(f"Error validando email: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": email,
                "valor_formateado": None,
                "formato_esperado": "usuario@dominio.com",
                "sugerencia": "Verifique el formato del email. Ejemplo: 'usuario@ejemplo.com'",
            }


class ValidadorNombre:
    """Validador y formateador de nombres y apellidos"""

    @staticmethod
    def validar_y_formatear_nombre(texto: Any) -> Dict[str, Any]:
        """
        Validar y formatear nombre/apellido con primera letra en mayúscula

        Args:
            texto: Nombre o apellido a validar (acepta 1-2 palabras)

        Returns:
            Dict con resultado de validación y formateo
        """
        try:
            if not texto or not isinstance(texto, str):
                return {
                    "valido": False,
                    "error": "Nombre requerido",
                    "valor_original": texto,
                    "valor_formateado": None,
                    "formato_esperado": "Juan Carlos o Maria",
                    "sugerencia": "Ingrese un nombre. Ejemplo: 'Juan' o 'Maria Elena'",
                }

            # Limpiar espacios extra
            texto_limpio = " ".join(texto.split())

            # Validar que no esté vacío después de limpiar
            if not texto_limpio:
                return {
                    "valido": False,
                    "error": "Nombre no puede estar vacío",
                    "valor_original": texto,
                    "valor_formateado": None,
                    "formato_esperado": "Juan Carlos o Maria",
                    "sugerencia": "El nombre no puede estar vacío. Ejemplo: 'Juan'",
                }

            # Validar que solo contenga letras, espacios y algunos caracteres especiales permitidos
            patron_nombre = r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s\-']+$"
            if not re.match(patron_nombre, texto_limpio):
                return {
                    "valido": False,
                    "error": "Nombre solo puede contener letras y espacios",
                    "valor_original": texto,
                    "valor_formateado": None,
                    "formato_esperado": "Juan Carlos o Maria",
                    "sugerencia": "Use solo letras (sin números o símbolos). Ejemplos: 'Juan', 'Maria Elena', 'Carlos'",
                }

            # Validar longitud de palabras (1-2 palabras, cada una de 2-40 caracteres)
            palabras = texto_limpio.split()
            if len(palabras) > 2:
                return {
                    "valido": False,
                    "error": f"Nombre debe tener máximo 2 palabras (tiene {len(palabras)})",
                    "valor_original": texto,
                    "valor_formateado": None,
                    "formato_esperado": "Juan Carlos (1-2 palabras)",
                    "sugerencia": f"Use máximo 2 palabras. Ejemplo: {' '.join(palabras[:2])}",
                }

            for palabra in palabras:
                if len(palabra) < 2:
                    return {
                        "valido": False,
                        "error": f"La palabra '{palabra}' debe tener al menos 2 caracteres",
                        "valor_original": texto,
                        "valor_formateado": None,
                        "formato_esperado": "Cada palabra debe tener 2-40 caracteres",
                        "sugerencia": f"Use palabras con al menos 2 letras. La palabra '{palabra}' es muy corta.",
                    }
                if len(palabra) > 40:
                    return {
                        "valido": False,
                        "error": (
                            f"La palabra '{palabra[:20]}...' excede 40 caracteres "
                            f"({len(palabra)} caracteres)"
                        ),
                        "valor_original": texto,
                        "valor_formateado": None,
                        "formato_esperado": "Cada palabra máximo 40 caracteres",
                        "sugerencia": (
                            f"Use palabras más cortas. La palabra '{palabra}' tiene "
                            f"{len(palabra)} caracteres, máximo permitido: 40"
                        ),
                    }

            # Formatear: Solo la primera letra del texto en mayúscula, resto en minúscula
            texto_formateado = texto_limpio.lower().capitalize()

            return {
                "valido": True,
                "valor_original": texto,
                "valor_formateado": texto_formateado,
                "cambio_realizado": texto_limpio != texto_formateado,
            }

        except Exception as e:
            logger.error(f"Error validando nombre: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": texto,
                "valor_formateado": None,
                "formato_esperado": "Juan Carlos o Maria",
                "sugerencia": "Verifique el formato del nombre. Ejemplo: 'Juan' o 'Maria Elena'",
            }


class ValidadorMonto:
    """Validador y formateador de montos"""

    MONEDAS_CONFIG = {
        "USD": {
            "simbolo": "$",
            "descripcion": "Dólares Americanos",
            "minimo": Decimal("1.00"),
            "maximo": Decimal("20000.00"),
        },
        "VES": {
            "simbolo": "Bs.",
            "descripcion": "Bolívares Venezolanos",
            "minimo": Decimal("1.00"),
            "maximo": Decimal("20000.00"),
        },
    }

    @staticmethod
    def validar_y_formatear_monto(
        monto: Any, moneda: str = "USD"
    ) -> Dict[str, Any]:
        """
        Validar y formatear monto monetario (rango 1-20000)

        Args:
            monto: Monto a validar (str, int, float, Decimal)
            moneda: Tipo de moneda (USD o VES), por defecto USD

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
                    "formato_esperado": "Número decimal (1-20000)",
                    "sugerencia": "Ingrese un monto. Ejemplo: '1500.50'",
                }

            # Validar moneda
            config_moneda = ValidadorMonto.MONEDAS_CONFIG.get(moneda.upper())
            if not config_moneda:
                return {
                    "valido": False,
                    "error": f"Moneda '{moneda}' no soportada. Use USD o VES",
                    "valor_original": monto,
                    "valor_formateado": None,
                    "formato_esperado": "USD o VES",
                    "sugerencia": "Use moneda USD (dólares) o VES (bolívares). Ejemplo: '1500.50'",
                }

            # Convertir a Decimal
            try:
                if isinstance(monto, str):
                    # Limpiar string: mantener solo dígitos, puntos y comas
                    monto_limpio = re.sub(r"[^\d.,]", "", monto)

                    # SISTEMA EUROPEO ÚNICAMENTE
                    # Formatos válidos:
                    # 1. Entero: "10000" o "10"
                    # 2. Decimal con coma: "10000,50" o "10,5"
                    # 3. Miles con punto y decimal con coma: "1.500,50"

                    if "," in monto_limpio and "." in monto_limpio:
                        # Ambos presentes: verificar formato correcto
                        # El separador de miles debe estar cada 3 dígitos
                        # El último separador indica decimales
                        
                        # Encontrar posición del último separador
                        ultimo_coma = monto_limpio.rindex(",")
                        ultimo_punto = monto_limpio.rindex(".")
                        
                        if ultimo_coma > ultimo_punto:
                            # Formato europeo: "1.234,56"
                            # Validar que antes de la coma solo haya un punto cada 3 dígitos
                            antes_coma = monto_limpio[:ultimo_coma]
                            despues_coma = monto_limpio[ultimo_coma+1:]
                            
                            # Después de coma debe haber 1-2 dígitos
                            if not (1 <= len(despues_coma) <= 2):
                                return {
                                    "valido": False,
                                    "error": "Formato de monto inválido (decimales)",
                                    "valor_original": monto,
                                    "valor_formateado": None,
                                    "formato_esperado": "Número decimal (1-20000)",
                                    "sugerencia": (
                                        "Los decimales deben ser 1-2 dígitos. "
                                        "Ejemplo: '10.500,50' o '10500,50'"
                                    ),
                                }
                            
                            # Validar miles con punto cada 3 dígitos
                            antes_coma_sin_puntos = antes_coma.replace(".", "")
                            if not antes_coma_sin_puntos.isdigit():
                                return {
                                    "valido": False,
                                    "error": "Formato de monto inválido",
                                    "valor_original": monto,
                                    "valor_formateado": None,
                                    "formato_esperado": "Número decimal (1-20000)",
                                    "sugerencia": (
                                        "Use formato válido. Ejemplo: '10.500,50' "
                                        "o '10500,50'"
                                    ),
                                }
                            
                            # Validar que los puntos estén cada 3 dígitos
                            partes_miles = antes_coma.split(".")
                            for i, parte in enumerate(partes_miles):
                                if i == 0:
                                    # Primera parte puede tener 1-3 dígitos
                                    if len(parte) > 3 or len(parte) == 0:
                                        return {
                                            "valido": False,
                                            "error": "Formato de miles inválido",
                                            "valor_original": monto,
                                            "valor_formateado": None,
                                            "formato_esperado": "Punto cada 3 dígitos para miles",
                                            "sugerencia": (
                                                "Use punto cada 3 dígitos. "
                                                "Ejemplos: '10.500' o '1.234' (NO '123.45' o '1.23')"
                                            ),
                                        }
                                else:
                                    # Las siguientes partes deben tener exactamente 3 dígitos
                                    if len(parte) != 3:
                                        return {
                                            "valido": False,
                                            "error": "Formato de miles inválido",
                                            "valor_original": monto,
                                            "valor_formateado": None,
                                            "formato_esperado": "Punto cada 3 dígitos para miles",
                                            "sugerencia": (
                                                "Cada punto debe separar exactamente 3 dígitos. "
                                                "Ejemplo: '10.500,50' (NO '1.50,50' o '10.5,50')"
                                            ),
                                        }
                            
                            monto_limpio = antes_coma_sin_puntos + "." + despues_coma
                        else:
                            # FORMATO AMERICANO NO SOPORTADO
                            # Si el punto está después de la coma, es formato americano (rechazar)
                            return {
                                "valido": False,
                                "error": "Solo se acepta formato europeo",
                                "valor_original": monto,
                                "valor_formateado": None,
                                "formato_esperado": "Número decimal (1-20000)",
                                "sugerencia": (
                                    "Use formato europeo. Ejemplos: '1500,50' o '1.500,50'. "
                                    "NO use coma para miles (p.ej: 1,500.50)"
                                ),
                            }
                    elif "," in monto_limpio:
                        # Solo coma: debe ser un número con coma decimal
                        # Validar que después de coma haya 1-2 dígitos
                        partes_coma = monto_limpio.split(",")
                        if len(partes_coma) != 2:
                            return {
                                "valido": False,
                                "error": "Formato de monto inválido (múltiples comas)",
                                "valor_original": monto,
                                "valor_formateado": None,
                                "formato_esperado": "Número decimal (1-20000)",
                                "sugerencia": (
                                    "Use una sola coma para decimales. "
                                    "Ejemplo: '1500,50'"
                                ),
                            }
                        
                        antes_coma = partes_coma[0]
                        despues_coma = partes_coma[1]
                        
                        # Después de coma debe haber 1-2 dígitos
                        if not (1 <= len(despues_coma) <= 2):
                            return {
                                "valido": False,
                                "error": "Formato de monto inválido (decimales)",
                                "valor_original": monto,
                                "valor_formateado": None,
                                "formato_esperado": "Número decimal (1-20000)",
                                "sugerencia": (
                                    "Los decimales deben ser 1-2 dígitos. "
                                    "Ejemplo: '1500,50'"
                                ),
                            }
                        
                        # Antes de coma debe ser número válido
                        if not antes_coma.isdigit():
                            return {
                                "valido": False,
                                "error": "Formato de monto inválido",
                                "valor_original": monto,
                                "valor_formateado": None,
                                "formato_esperado": "Número decimal (1-20000)",
                                "sugerencia": "Use formato válido. Ejemplo: '1500,50'",
                            }
                        
                        monto_limpio = antes_coma + "." + despues_coma
                    elif "." in monto_limpio:
                        # Solo punto: NO se acepta formato americano, rechazar
                        return {
                            "valido": False,
                            "error": "Solo se acepta formato europeo",
                            "valor_original": monto,
                            "valor_formateado": None,
                            "formato_esperado": "Número decimal (1-20000)",
                            "sugerencia": (
                                "Use formato europeo con coma para decimales. "
                                "Ejemplos: '1500,50' o '1.500,50'. NO use punto para decimales"
                            ),
                        }
                    else:
                        # Sin separador: debe ser solo dígitos
                        if not monto_limpio.isdigit():
                            return {
                                "valido": False,
                                "error": "Formato de monto inválido",
                                "valor_original": monto,
                                "valor_formateado": None,
                                "formato_esperado": "Número decimal (1-20000)",
                                "sugerencia": "Use solo dígitos. Ejemplo: '1500'",
                            }

                    monto_decimal = Decimal(monto_limpio)
                else:
                    monto_decimal = Decimal(str(monto))
            except (InvalidOperation, ValueError):
                return {
                    "valido": False,
                    "error": "Formato de monto inválido",
                    "valor_original": monto,
                    "valor_formateado": None,
                    "formato_esperado": "Número decimal formato europeo (1-20000)",
                    "sugerencia": (
                        "Use formato europeo. Ejemplos: '1500,50', '1.500,50', "
                        "'20000'. Use coma (,) para decimales y punto (.) para miles"
                    ),
                }

            # Validar rango mínimo (1.00)
            if monto_decimal < config_moneda["minimo"]:
                return {
                    "valido": False,
                    "error": f"El monto mínimo es {config_moneda['simbolo']}1.00",
                    "valor_original": monto,
                    "valor_formateado": None,
                    "formato_esperado": (
                        f"Rango: {config_moneda['simbolo']}1.00 - "
                        f"{config_moneda['simbolo']}20,000.00"
                    ),
                    "sugerencia": (
                        f"Use un monto mínimo de {config_moneda['simbolo']}1.00. "
                        f"Ejemplo: '{config_moneda['simbolo']}1.00' o "
                        f"'{config_moneda['simbolo']}100.00'"
                    ),
                }

            # Validar rango máximo (20000.00)
            if monto_decimal > config_moneda["maximo"]:
                return {
                    "valido": False,
                    "error": f"El monto máximo es {config_moneda['simbolo']}20,000.00",
                    "valor_original": monto,
                    "valor_formateado": None,
                    "formato_esperado": (
                        f"Rango: {config_moneda['simbolo']}1.00 - "
                        f"{config_moneda['simbolo']}20,000.00"
                    ),
                    "sugerencia": (
                        f"Use un monto máximo de {config_moneda['simbolo']}20,000.00. "
                        f"Ejemplo: '{config_moneda['simbolo']}20000' o "
                        f"'{config_moneda['simbolo']}15000.50'"
                    ),
                }

            # Formatear con 2 decimales
            monto_formateado = monto_decimal.quantize(Decimal("0.01"))

            return {
                "valido": True,
                "valor_original": monto,
                "valor_formateado": float(monto_formateado),
                "valor_decimal": monto_formateado,
                "moneda": moneda.upper(),
                "simbolo_moneda": config_moneda["simbolo"],
                "cambio_realizado": str(monto) != str(monto_formateado),
            }

        except Exception as e:
            logger.error(f"Error validando monto: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": monto,
                "valor_formateado": None,
                "formato_esperado": "Número decimal (1-20000)",
                "sugerencia": "Verifique el formato del monto. Ejemplo: '1500.50'",
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

    # Validar nombres
    if "nombre" in cliente_data:
        _validar_campo_cliente(
            "nombre",
            cliente_data["nombre"],
            ValidadorNombre.validar_y_formatear_nombre,
            resultados,
        )

    if "apellido" in cliente_data:
        _validar_campo_cliente(
            "apellido",
            cliente_data["apellido"],
            ValidadorNombre.validar_y_formatear_nombre,
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
