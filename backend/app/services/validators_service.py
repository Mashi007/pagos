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
            }


class ValidadorFecha:
    """Validador y formateador de fechas"""

    @staticmethod
    def _validar_rangos_fecha(dia: int, mes: int, año: int, fecha: str) -> Optional[Dict[str, Any]]:
        """Validar rangos de día, mes y año"""
        if año < 1000 or año > 9999:
            return {
                "valido": False,
                "error": "El año debe tener 4 dígitos (ejemplo: 2025)",
                "valor_original": fecha,
                "valor_formateado": None,
            }
        if mes < 1 or mes > 12:
            return {
                "valido": False,
                "error": "El mes debe estar entre 01 y 12",
                "valor_original": fecha,
                "valor_formateado": None,
            }
        if dia < 1 or dia > 31:
            return {
                "valido": False,
                "error": "El día debe estar entre 01 y 31",
                "valor_original": fecha,
                "valor_formateado": None,
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
                "error": "Fecha inválida (ejemplo: no existe 31 de febrero)",
                "valor_original": fecha,
                "valor_formateado": None,
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
                        "error": "Formato debe ser DD/MM/YYYY",
                        "valor_original": fecha,
                        "valor_formateado": None,
                    }

                dia_str, mes_str, año_str = partes

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
                }

        except Exception as e:
            logger.error(f"Error validando fecha: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": fecha,
                "valor_formateado": None,
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
                }

            email_original = email.strip()

            # Validar que no tenga espacios
            if ' ' in email_original:
                return {
                    "valido": False,
                    "error": "Email no puede contener espacios",
                    "valor_original": email,
                    "valor_formateado": None,
                }

            # Validar que no tenga comas
            if ',' in email_original:
                return {
                    "valido": False,
                    "error": "Email no puede contener comas",
                    "valor_original": email,
                    "valor_formateado": None,
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
                }

            # Validar que solo contenga letras, espacios y algunos caracteres especiales permitidos
            patron_nombre = r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s\-']+$"
            if not re.match(patron_nombre, texto_limpio):
                return {
                    "valido": False,
                    "error": "Nombre solo puede contener letras y espacios",
                    "valor_original": texto,
                    "valor_formateado": None,
                }

            # Validar longitud de palabras (1-2 palabras, cada una de 2-40 caracteres)
            palabras = texto_limpio.split()
            if len(palabras) > 2:
                return {
                    "valido": False,
                    "error": "Nombre debe tener máximo 2 palabras",
                    "valor_original": texto,
                    "valor_formateado": None,
                }

            for palabra in palabras:
                if len(palabra) < 2:
                    return {
                        "valido": False,
                        "error": "Cada palabra debe tener al menos 2 caracteres",
                        "valor_original": texto,
                        "valor_formateado": None,
                    }
                if len(palabra) > 40:
                    return {
                        "valido": False,
                        "error": "Cada palabra no debe exceder 40 caracteres",
                        "valor_original": texto,
                        "valor_formateado": None,
                    }

            # Formatear: Primera letra de cada palabra en mayúscula, resto en minúscula
            palabras_formateadas = [
                palabra.capitalize() for palabra in palabras
            ]
            texto_formateado = " ".join(palabras_formateadas)

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
                }

            # Validar moneda
            config_moneda = ValidadorMonto.MONEDAS_CONFIG.get(moneda.upper())
            if not config_moneda:
                return {
                    "valido": False,
                    "error": f"Moneda '{moneda}' no soportada. Use USD o VES",
                    "valor_original": monto,
                    "valor_formateado": None,
                }

            # Convertir a Decimal
            try:
                if isinstance(monto, str):
                    # Limpiar string: mantener solo dígitos, puntos y comas
                    monto_limpio = re.sub(r"[^\d.,]", "", monto)
                    
                    # Lógica: detectar separador decimal
                    # - Si tiene 1 punto y 1 coma: el último define decimales
                    # - Si tiene solo coma: es decimal (formato venezolano/europeo)
                    # - Si tiene solo punto: es decimal (formato internacional)
                    
                    if "," in monto_limpio and "." in monto_limpio:
                        # Ambos presentes: el último indica decimales
                        if monto_limpio.rindex(",") > monto_limpio.rindex("."):
                            # Ejemplo: 1.234,56 → decimal: ,
                            monto_limpio = monto_limpio.replace(".", "").replace(",", ".")
                        else:
                            # Ejemplo: 1,234.56 → decimal: .
                            monto_limpio = monto_limpio.replace(",", "")
                    elif "," in monto_limpio:
                        # Solo coma: es decimal
                        monto_limpio = monto_limpio.replace(",", ".")
                    # Si solo tiene punto o ninguno, se deja como está
                    
                    monto_decimal = Decimal(monto_limpio)
                else:
                    monto_decimal = Decimal(str(monto))
            except (InvalidOperation, ValueError):
                return {
                    "valido": False,
                    "error": "Formato de monto inválido. Use: 1500.50 o 1.500,50 o 1500,50",
                    "valor_original": monto,
                    "valor_formateado": None,
                }

            # Validar rango mínimo (1.00)
            if monto_decimal < config_moneda["minimo"]:
                return {
                    "valido": False,
                    "error": f"El monto mínimo es {config_moneda['simbolo']}1.00",
                    "valor_original": monto,
                    "valor_formateado": None,
                }

            # Validar rango máximo (20000.00)
            if monto_decimal > config_moneda["maximo"]:
                return {
                    "valido": False,
                    "error": f"El monto máximo es {config_moneda['simbolo']}20,000.00",
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
