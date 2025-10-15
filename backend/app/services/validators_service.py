# backend/app/services/validators_service.py
"""
🔍 Servicio de Validadores y Auto-Formateo
Sistema completo para validar y corregir formatos incorrectos de datos
"""
import re
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class ValidadorTelefono:
    """
    📱 Validador y formateador de números de teléfono
    Soporta múltiples países y auto-formateo
    """
    
    # Configuración por país
    PAISES_CONFIG = {
        "VENEZUELA": {
            "codigo_pais": "+58",
            "operadoras": ["424", "414", "416", "426", "412", "425"],
            "longitud_sin_codigo": 10,  # 10 dígitos total
            "patron_completo": r"^\+58[1-9][0-9]{9}$",  # +58 + 10 dígitos (primer dígito no puede ser 0)
            "formato_display": "+58 XXXXXXXXXX",
            "requisitos": {
                "debe_empezar_por": "+58",
                "longitud_total": 10,
                "primer_digito": "No puede ser 0",
                "digitos_validos": "0-9"
            }
        },
        "DOMINICANA": {
            "codigo_pais": "+1",
            "operadoras": ["809", "829", "849"],
            "longitud_sin_codigo": 10,  # 809 1234567
            "patron_completo": r"^\+1\s?[0-9]{3}\s?[0-9]{7}$",
            "formato_display": "+1 XXX XXXXXXX"
        },
        "COLOMBIA": {
            "codigo_pais": "+57",
            "operadoras": ["300", "301", "302", "310", "311", "312", "313", "314", "315", "316", "317", "318", "319", "320", "321", "322", "323"],
            "longitud_sin_codigo": 10,
            "patron_completo": r"^\+57\s?[0-9]{3}\s?[0-9]{7}$",
            "formato_display": "+57 XXX XXXXXXX"
        }
    }
    
    @staticmethod
    def validar_y_formatear_telefono(
        telefono: str, 
        pais: str = "VENEZUELA"
    ) -> Dict[str, Any]:
        """
        📱 Validar y formatear número de teléfono
        
        Ejemplos de entrada:
        - "4241234567" → "+58 424 1234567"
        - "424 1234567" → "+58 424 1234567"
        - "+58 424 1234567" → "+58 424 1234567" (ya correcto)
        """
        try:
            if not telefono:
                return {
                    "valido": False,
                    "error": "Teléfono requerido",
                    "valor_original": telefono,
                    "valor_formateado": None
                }
            
            # Limpiar entrada
            telefono_limpio = re.sub(r'[^\d+]', '', telefono.strip())
            
            config = ValidadorTelefono.PAISES_CONFIG.get(pais.upper())
            if not config:
                return {
                    "valido": False,
                    "error": f"País '{pais}' no soportado",
                    "valor_original": telefono,
                    "valor_formateado": None
                }
            
            # Casos de formateo específicos por país
            if pais.upper() == "VENEZUELA":
                return ValidadorTelefono._formatear_telefono_venezolano(telefono_limpio, config)
            else:
                # Lógica original para otros países
                if telefono_limpio.startswith(config["codigo_pais"].replace("+", "")):
                    # Ya tiene código de país: "584241234567"
                    numero_formateado = "+" + telefono_limpio[:2] + " " + telefono_limpio[2:5] + " " + telefono_limpio[5:]
                    
                elif telefono_limpio.startswith(config["codigo_pais"]):
                    # Ya tiene + y código: "+584241234567"
                    numero_sin_plus = telefono_limpio[1:]
                    numero_formateado = "+" + numero_sin_plus[:2] + " " + numero_sin_plus[2:5] + " " + numero_sin_plus[5:]
                    
                elif len(telefono_limpio) == config["longitud_sin_codigo"]:
                    # Solo número local: "4241234567"
                    operadora = telefono_limpio[:3]
                    if operadora in config["operadoras"]:
                        numero_formateado = f"{config['codigo_pais']} {operadora} {telefono_limpio[3:]}"
                    else:
                        return {
                            "valido": False,
                            "error": f"Operadora '{operadora}' no válida para {pais}. Válidas: {', '.join(config['operadoras'])}",
                            "valor_original": telefono,
                            "valor_formateado": None,
                            "sugerencia": f"Debe comenzar con: {', '.join(config['operadoras'])}"
                        }
                else:
                    return {
                        "valido": False,
                        "error": f"Longitud incorrecta. Formato esperado: {config['formato_display']}",
                        "valor_original": telefono,
                        "valor_formateado": None,
                        "longitud_actual": len(telefono_limpio),
                        "longitud_esperada": config["longitud_sin_codigo"]
                    }
            
            # Validar formato final
            if re.match(config["patron_completo"], numero_formateado):
                return {
                    "valido": True,
                    "valor_original": telefono,
                    "valor_formateado": numero_formateado,
                    "pais": pais,
                    "operadora": numero_formateado.split()[1],
                    "cambio_realizado": telefono != numero_formateado
                }
            else:
                return {
                    "valido": False,
                    "error": "Formato final inválido",
                    "valor_original": telefono,
                    "valor_formateado": numero_formateado
                }
                
        except Exception as e:
            logger.error(f"Error validando teléfono: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": telefono,
                "valor_formateado": None
            }
    
    @staticmethod
    def _formatear_telefono_venezolano(telefono_limpio: str, config: Dict) -> Dict[str, Any]:
        """
        📱 Formatear teléfono venezolano con nuevos requisitos:
        - Debe empezar por +58
        - Seguido de 10 dígitos
        - El primer dígito no puede ser 0
        """
        try:
            # Casos de entrada
            if telefono_limpio.startswith("58"):
                # Ya tiene código de país sin +: "581234567890"
                numero_sin_codigo = telefono_limpio[2:]  # Quitar "58"
                if len(numero_sin_codigo) == 10:
                    # Validar que el primer dígito no sea 0
                    if numero_sin_codigo[0] == "0":
                        return {
                            "valido": False,
                            "error": "El primer dígito del número no puede ser 0",
                            "valor_original": telefono_limpio,
                            "valor_formateado": None,
                            "requisitos": config["requisitos"]
                        }
                    numero_formateado = f"+58{numero_sin_codigo}"
                else:
                    return {
                        "valido": False,
                        "error": f"Longitud incorrecta. Debe tener 10 dígitos después de +58, tiene {len(numero_sin_codigo)}",
                        "valor_original": telefono_limpio,
                        "valor_formateado": None,
                        "requisitos": config["requisitos"]
                    }
                    
            elif telefono_limpio.startswith("+58"):
                # Ya tiene +58: "+581234567890"
                numero_sin_codigo = telefono_limpio[3:]  # Quitar "+58"
                if len(numero_sin_codigo) == 10:
                    # Validar que el primer dígito no sea 0
                    if numero_sin_codigo[0] == "0":
                        return {
                            "valido": False,
                            "error": "El primer dígito del número no puede ser 0",
                            "valor_original": telefono_limpio,
                            "valor_formateado": None,
                            "requisitos": config["requisitos"]
                        }
                    numero_formateado = telefono_limpio
                else:
                    return {
                        "valido": False,
                        "error": f"Longitud incorrecta. Debe tener 10 dígitos después de +58, tiene {len(numero_sin_codigo)}",
                        "valor_original": telefono_limpio,
                        "valor_formateado": None,
                        "requisitos": config["requisitos"]
                    }
                    
            elif len(telefono_limpio) == 10:
                # Solo número local: "1234567890"
                # Validar que el primer dígito no sea 0
                if telefono_limpio[0] == "0":
                    return {
                        "valido": False,
                        "error": "El primer dígito del número no puede ser 0",
                        "valor_original": telefono_limpio,
                        "valor_formateado": None,
                        "requisitos": config["requisitos"]
                    }
                numero_formateado = f"+58{telefono_limpio}"
                
            else:
                return {
                    "valido": False,
                    "error": f"Longitud incorrecta. Formato esperado: +58 seguido de 10 dígitos (primer dígito no puede ser 0)",
                    "valor_original": telefono_limpio,
                    "valor_formateado": None,
                    "longitud_actual": len(telefono_limpio),
                    "requisitos": config["requisitos"]
                }
            
            # Validar formato final con regex
            if re.match(config["patron_completo"], numero_formateado):
                return {
                    "valido": True,
                    "valor_original": telefono_limpio,
                    "valor_formateado": numero_formateado,
                    "pais": "VENEZUELA",
                    "cambio_realizado": telefono_limpio != numero_formateado,
                    "codigo_pais": "+58",
                    "numero_local": numero_formateado[3:],  # Sin +58
                    "requisitos_cumplidos": {
                        "empieza_por_58": True,
                        "longitud_10_digitos": True,
                        "primer_digito_no_cero": numero_formateado[3] != "0"
                    }
                }
            else:
                return {
                    "valido": False,
                    "error": "Formato final no cumple con los requisitos",
                    "valor_original": telefono_limpio,
                    "valor_formateado": numero_formateado,
                    "requisitos": config["requisitos"]
                }
                
        except Exception as e:
            logger.error(f"Error formateando teléfono venezolano: {e}")
            return {
                "valido": False,
                "error": f"Error de formateo: {str(e)}",
                "valor_original": telefono_limpio,
                "valor_formateado": None
            }


class ValidadorCedula:
    """
    📝 Validador y formateador de cédulas
    Soporta múltiples países con auto-formateo
    """
    
    PAISES_CEDULA = {
        "VENEZUELA": {
            "prefijos": ["V", "E", "J"],  # V=Venezolano, E=Extranjero, J=Jurídico
            "longitud_numero": [7, 8, 9, 10],  # 7 a 10 dígitos
            "patron": r"^[VEJ]\d{7,10}$",
            "formato_display": "V12345678",
            "descripcion": "Cédula venezolana: V/E/J + 7-10 dígitos"
        },
        "DOMINICANA": {
            "prefijos": [],  # Sin prefijo de letra
            "longitud_numero": [11],  # XXX-XXXXXXX-X
            "patron": r"^\d{3}-\d{7}-\d{1}$",
            "formato_display": "001-1234567-8",
            "descripcion": "Cédula dominicana: XXX-XXXXXXX-X"
        },
        "COLOMBIA": {
            "prefijos": [],  # Sin prefijo
            "longitud_numero": [8, 9, 10],
            "patron": r"^\d{8,10}$",
            "formato_display": "12345678",
            "descripcion": "Cédula colombiana: 8-10 dígitos"
        }
    }
    
    @staticmethod
    def validar_y_formatear_cedula(
        cedula: str,
        pais: str = "VENEZUELA"
    ) -> Dict[str, Any]:
        """
        📝 Validar y formatear cédula
        
        Ejemplos de entrada:
        - "12345678" → "V12345678" (asume V si no especifica)
        - "v12345678" → "V12345678" (mayúscula)
        - "V-12345678" → "V12345678" (quita guiones)
        """
        try:
            if not cedula:
                return {
                    "valido": False,
                    "error": "Cédula requerida",
                    "valor_original": cedula,
                    "valor_formateado": None
                }
            
            config = ValidadorCedula.PAISES_CEDULA.get(pais.upper())
            if not config:
                return {
                    "valido": False,
                    "error": f"País '{pais}' no soportado",
                    "valor_original": cedula,
                    "valor_formateado": None
                }
            
            # Limpiar entrada
            cedula_limpia = re.sub(r'[^\w]', '', cedula.strip().upper())
            
            if pais.upper() == "VENEZUELA":
                return ValidadorCedula._formatear_cedula_venezolana(cedula_limpia, config)
            elif pais.upper() == "DOMINICANA":
                return ValidadorCedula._formatear_cedula_dominicana(cedula, config)
            elif pais.upper() == "COLOMBIA":
                return ValidadorCedula._formatear_cedula_colombiana(cedula_limpia, config)
            else:
                return {
                    "valido": False,
                    "error": "País no implementado",
                    "valor_original": cedula
                }
                
        except Exception as e:
            logger.error(f"Error validando cédula: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": cedula,
                "valor_formateado": None
            }
    
    @staticmethod
    def _formatear_cedula_venezolana(cedula_limpia: str, config: Dict) -> Dict[str, Any]:
        """Formatear cédula venezolana"""
        # Si no tiene prefijo, asumir V
        if cedula_limpia.isdigit():
            cedula_formateada = f"V{cedula_limpia}"
        else:
            cedula_formateada = cedula_limpia
        
        # Validar formato final
        if re.match(config["patron"], cedula_formateada):
            prefijo = cedula_formateada[0]
            numero = cedula_formateada[1:]
            
            # Validar que el prefijo sea válido
            if prefijo not in config["prefijos"]:
                return {
                    "valido": False,
                    "error": f"Prefijo '{prefijo}' no válido. Válidos: {', '.join(config['prefijos'])}",
                    "valor_original": cedula_limpia,
                    "valor_formateado": None,
                    "formato_esperado": config["descripcion"]
                }
            
            # Validar longitud del número
            if len(numero) not in config["longitud_numero"]:
                return {
                    "valido": False,
                    "error": f"Longitud inválida: {len(numero)} dígitos. Válidos: {config['longitud_numero']} dígitos",
                    "valor_original": cedula_limpia,
                    "valor_formateado": None,
                    "formato_esperado": config["descripcion"]
                }
            
            # Validar que todos los dígitos sean números
            if not numero.isdigit():
                return {
                    "valido": False,
                    "error": "Los dígitos deben ser números del 0 al 9",
                    "valor_original": cedula_limpia,
                    "valor_formateado": None,
                    "formato_esperado": config["descripcion"]
                }
            
            return {
                "valido": True,
                "valor_original": cedula_limpia,
                "valor_formateado": cedula_formateada,
                "pais": "VENEZUELA",
                "tipo": {
                    "V": "Venezolano",
                    "E": "Extranjero",
                    "J": "Jurídico"
                }.get(prefijo, "Desconocido"),
                "cambio_realizado": cedula_limpia != cedula_formateada,
                "prefijo": prefijo,
                "numero": numero,
                "longitud": len(numero)
            }
        
        return {
            "valido": False,
            "error": f"Formato inválido. Esperado: {config['formato_display']}",
            "valor_original": cedula_limpia,
            "valor_formateado": cedula_formateada,
            "formato_esperado": config["descripcion"]
        }
    
    @staticmethod
    def _formatear_cedula_dominicana(cedula: str, config: Dict) -> Dict[str, Any]:
        """Formatear cédula dominicana"""
        # Limpiar y formatear XXX-XXXXXXX-X
        numeros = re.sub(r'[^\d]', '', cedula)
        
        if len(numeros) == 11:
            cedula_formateada = f"{numeros[:3]}-{numeros[3:10]}-{numeros[10]}"
            
            if re.match(config["patron"], cedula_formateada):
                return {
                    "valido": True,
                    "valor_original": cedula,
                    "valor_formateado": cedula_formateada,
                    "pais": "DOMINICANA",
                    "cambio_realizado": cedula != cedula_formateada
                }
        
        return {
            "valido": False,
            "error": f"Formato inválido. Esperado: {config['formato_display']}",
            "valor_original": cedula,
            "formato_esperado": config["descripcion"]
        }
    
    @staticmethod
    def _formatear_cedula_colombiana(cedula_limpia: str, config: Dict) -> Dict[str, Any]:
        """Formatear cédula colombiana"""
        if cedula_limpia.isdigit() and len(cedula_limpia) in config["longitud_numero"]:
            return {
                "valido": True,
                "valor_original": cedula_limpia,
                "valor_formateado": cedula_limpia,
                "pais": "COLOMBIA",
                "cambio_realizado": False
            }
        
        return {
            "valido": False,
            "error": f"Formato inválido. Esperado: {config['formato_display']}",
            "valor_original": cedula_limpia,
            "formato_esperado": config["descripcion"]
        }


class ValidadorFecha:
    """
    📅 Validador y formateador de fechas con reglas de negocio
    """
    
    @staticmethod
    def validar_fecha_entrega(fecha_str: str) -> Dict[str, Any]:
        """
        📅 Validar fecha de entrega del vehículo
        
        Reglas:
        - No puede ser fecha futura
        - Debe ser fecha válida
        - Formato: DD/MM/YYYY o YYYY-MM-DD
        """
        try:
            if not fecha_str or fecha_str.upper() == "ERROR":
                return {
                    "valido": False,
                    "error": "Fecha de entrega requerida",
                    "valor_original": fecha_str,
                    "valor_formateado": None,
                    "requiere_calendario": True
                }
            
            # Intentar parsear diferentes formatos
            fecha_parseada = ValidadorFecha._parsear_fecha_flexible(fecha_str)
            
            if not fecha_parseada:
                return {
                    "valido": False,
                    "error": "Formato de fecha inválido",
                    "valor_original": fecha_str,
                    "valor_formateado": None,
                    "formatos_aceptados": ["DD/MM/YYYY", "YYYY-MM-DD", "DD-MM-YYYY"],
                    "requiere_calendario": True
                }
            
            # Validar reglas de negocio
            hoy = date.today()
            
            if fecha_parseada > hoy:
                return {
                    "valido": False,
                    "error": "La fecha de entrega no puede ser futura",
                    "valor_original": fecha_str,
                    "valor_formateado": fecha_parseada.strftime("%d/%m/%Y"),
                    "fecha_maxima": hoy.strftime("%d/%m/%Y"),
                    "requiere_calendario": True
                }
            
            # Validar que no sea muy antigua (más de 10 años)
            fecha_minima = hoy - timedelta(days=3650)  # 10 años
            if fecha_parseada < fecha_minima:
                return {
                    "valido": False,
                    "error": "Fecha de entrega muy antigua",
                    "valor_original": fecha_str,
                    "valor_formateado": fecha_parseada.strftime("%d/%m/%Y"),
                    "fecha_minima": fecha_minima.strftime("%d/%m/%Y")
                }
            
            return {
                "valido": True,
                "valor_original": fecha_str,
                "valor_formateado": fecha_parseada.strftime("%d/%m/%Y"),
                "fecha_iso": fecha_parseada.isoformat(),
                "cambio_realizado": fecha_str != fecha_parseada.strftime("%d/%m/%Y"),
                "requiere_recalculo_amortizacion": True,
                "mensaje_recalculo": "¿Desea recalcular la tabla de amortización con la nueva fecha?"
            }
            
        except Exception as e:
            logger.error(f"Error validando fecha: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": fecha_str,
                "valor_formateado": None
            }
    
    @staticmethod
    def validar_fecha_pago(fecha_str: str) -> Dict[str, Any]:
        """
        📅 Validar fecha de pago
        
        Reglas:
        - No puede ser más de 1 día en el futuro
        - Debe ser fecha válida
        """
        try:
            if not fecha_str or fecha_str.upper() == "ERROR":
                return {
                    "valido": False,
                    "error": "Fecha de pago requerida",
                    "valor_original": fecha_str,
                    "valor_formateado": None
                }
            
            fecha_parseada = ValidadorFecha._parsear_fecha_flexible(fecha_str)
            
            if not fecha_parseada:
                return {
                    "valido": False,
                    "error": "Formato de fecha inválido",
                    "valor_original": fecha_str,
                    "formatos_aceptados": ["DD/MM/YYYY", "YYYY-MM-DD"]
                }
            
            # Validar reglas de negocio
            hoy = date.today()
            manana = hoy + timedelta(days=1)
            
            if fecha_parseada > manana:
                return {
                    "valido": False,
                    "error": "La fecha de pago no puede ser más de 1 día en el futuro",
                    "valor_original": fecha_str,
                    "valor_formateado": fecha_parseada.strftime("%d/%m/%Y"),
                    "fecha_maxima": manana.strftime("%d/%m/%Y")
                }
            
            return {
                "valido": True,
                "valor_original": fecha_str,
                "valor_formateado": fecha_parseada.strftime("%d/%m/%Y"),
                "fecha_iso": fecha_parseada.isoformat(),
                "cambio_realizado": fecha_str != fecha_parseada.strftime("%d/%m/%Y")
            }
            
        except Exception as e:
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": fecha_str
            }
    
    @staticmethod
    def _parsear_fecha_flexible(fecha_str: str) -> Optional[date]:
        """
        Parsear fecha con validación estricta de formato DD/MM/YYYY
        
        Requisitos:
        - Día: 2 dígitos (01-31)
        - Mes: 2 dígitos (01-12)  
        - Año: 4 dígitos
        - Separador: / (barra)
        """
        fecha_limpia = fecha_str.strip()
        
        # Validar formato básico con regex
        if not re.match(r'^\d{2}/\d{2}/\d{4}$', fecha_limpia):
            return None
        
        try:
            # Parsear estrictamente como DD/MM/YYYY
            fecha_parseada = datetime.strptime(fecha_limpia, "%d/%m/%Y").date()
            
            # Validaciones adicionales
            dia, mes, año = fecha_limpia.split('/')
            
            # Validar que el día sea válido (01-31)
            if not (1 <= int(dia) <= 31):
                return None
                
            # Validar que el mes sea válido (01-12)
            if not (1 <= int(mes) <= 12):
                return None
                
            # Validar que el año sea razonable (1900-2100)
            if not (1900 <= int(año) <= 2100):
                return None
            
            # Validar que la fecha sea válida (ej: 31/02/2024 no existe)
            try:
                datetime.strptime(fecha_limpia, "%d/%m/%Y").date()
                return fecha_parseada
            except ValueError:
                return None
                
        except (ValueError, IndexError):
            return None


class ValidadorMonto:
    """
    💰 Validador y formateador de montos financieros
    """
    
    @staticmethod
    def validar_y_formatear_monto(
        monto_str: str,
        tipo_monto: str = "GENERAL",
        saldo_maximo: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        💰 Validar y formatear monto
        
        Ejemplos:
        - "ERROR" → Error, requiere valor
        - "15000" → 15000.00
        - "15,000.50" → 15000.50
        - "$15,000" → 15000.00
        """
        try:
            if not monto_str or monto_str.upper() == "ERROR":
                return {
                    "valido": False,
                    "error": f"Monto {tipo_monto.lower()} requerido",
                    "valor_original": monto_str,
                    "valor_formateado": None,
                    "requiere_input_numerico": True
                }
            
            # Limpiar entrada (quitar $, comas, espacios)
            monto_limpio = re.sub(r'[$,\s]', '', monto_str.strip())
            
            # Intentar convertir a decimal
            try:
                monto_decimal = Decimal(monto_limpio)
            except InvalidOperation:
                return {
                    "valido": False,
                    "error": "Formato numérico inválido",
                    "valor_original": monto_str,
                    "valor_formateado": None,
                    "ejemplo_valido": "15000.00 o 15,000.50"
                }
            
            # Validar que sea positivo
            if monto_decimal <= 0:
                return {
                    "valido": False,
                    "error": "El monto debe ser mayor a cero",
                    "valor_original": monto_str,
                    "valor_formateado": str(monto_decimal)
                }
            
            # Validar límites específicos por tipo
            error_limite = ValidadorMonto._validar_limites_por_tipo(monto_decimal, tipo_monto, saldo_maximo)
            if error_limite:
                return {
                    "valido": False,
                    "error": error_limite,
                    "valor_original": monto_str,
                    "valor_formateado": f"{monto_decimal:.2f}"
                }
            
            # Formatear a 2 decimales
            monto_formateado = monto_decimal.quantize(Decimal('0.01'))
            
            return {
                "valido": True,
                "valor_original": monto_str,
                "valor_formateado": str(monto_formateado),
                "valor_decimal": monto_formateado,
                "valor_display": f"${monto_formateado:,.2f}",
                "cambio_realizado": monto_str != str(monto_formateado),
                "tipo_monto": tipo_monto
            }
            
        except Exception as e:
            logger.error(f"Error validando monto: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": monto_str
            }
    
    @staticmethod
    def _validar_limites_por_tipo(monto: Decimal, tipo: str, saldo_maximo: Optional[Decimal]) -> Optional[str]:
        """Validar límites específicos por tipo de monto"""
        if tipo == "TOTAL_FINANCIAMIENTO":
            if monto < Decimal("100"):
                return "Monto mínimo de financiamiento: $100"
            if monto > Decimal("50000000"):  # 50M
                return "Monto máximo de financiamiento: $50,000,000"
        
        elif tipo == "MONTO_PAGO":
            if monto < Decimal("1"):
                return "Monto mínimo de pago: $1"
            if saldo_maximo and monto > saldo_maximo:
                return f"Monto no puede exceder el saldo pendiente: ${saldo_maximo:,.2f}"
        
        elif tipo == "CUOTA_INICIAL":
            if monto < Decimal("0"):
                return "Cuota inicial no puede ser negativa"
        
        return None  # Sin errores


class ValidadorAmortizaciones:
    """
    🔢 Validador de número de amortizaciones
    """
    
    @staticmethod
    def validar_amortizaciones(amortizaciones_str: str) -> Dict[str, Any]:
        """
        🔢 Validar número de amortizaciones
        
        Reglas:
        - Debe ser número entero
        - Mínimo: 1
        - Máximo: 84 (7 años)
        """
        try:
            if not amortizaciones_str or amortizaciones_str.upper() == "ERROR":
                return {
                    "valido": False,
                    "error": "Número de amortizaciones requerido",
                    "valor_original": amortizaciones_str,
                    "valor_formateado": None,
                    "rango_valido": "1 - 84 meses"
                }
            
            # Intentar convertir a entero
            try:
                amortizaciones = int(float(amortizaciones_str.strip()))
            except ValueError:
                return {
                    "valido": False,
                    "error": "Debe ser un número entero",
                    "valor_original": amortizaciones_str,
                    "valor_formateado": None
                }
            
            # Validar rango
            if amortizaciones < 1:
                return {
                    "valido": False,
                    "error": "Mínimo 1 amortización",
                    "valor_original": amortizaciones_str,
                    "valor_formateado": str(amortizaciones)
                }
            
            if amortizaciones > 84:
                return {
                    "valido": False,
                    "error": "Máximo 84 amortizaciones (7 años)",
                    "valor_original": amortizaciones_str,
                    "valor_formateado": str(amortizaciones)
                }
            
            return {
                "valido": True,
                "valor_original": amortizaciones_str,
                "valor_formateado": str(amortizaciones),
                "valor_entero": amortizaciones,
                "equivalente_anos": round(amortizaciones / 12, 1),
                "cambio_realizado": amortizaciones_str.strip() != str(amortizaciones)
            }
            
        except Exception as e:
            logger.error(f"Error validando amortizaciones: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": amortizaciones_str
            }


class ValidadorEmail:
    """
    📧 Validador de email con reglas avanzadas
    """
    
    DOMINIOS_BLOQUEADOS = [
        "tempmail.org", "10minutemail.com", "guerrillamail.com",
        "mailinator.com", "throwaway.email"
    ]
    
    @staticmethod
    def validar_email(email_str: str, verificar_dominio: bool = True) -> Dict[str, Any]:
        """
        📧 Validar email con normalización automática a minúsculas
        
        Características:
        - Convierte automáticamente a minúsculas (incluyendo @)
        - Validación RFC 5322
        - Verificación de dominios bloqueados
        - Normalización de espacios
        """
        try:
            if not email_str or email_str.upper() == "ERROR":
                return {
                    "valido": False,
                    "error": "Email requerido",
                    "valor_original": email_str,
                    "valor_formateado": None
                }
            
            # Normalizar email: quitar espacios y convertir a minúsculas
            email_limpio = email_str.strip().lower()
            
            # Validar que contenga el símbolo @
            if '@' not in email_limpio:
                return {
                    "valido": False,
                    "error": "Email debe contener el símbolo @",
                    "valor_original": email_str,
                    "valor_formateado": email_limpio,
                    "formato_esperado": "usuario@dominio.com"
                }
            
            # Validar formato RFC 5322
            patron_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            
            if not re.match(patron_email, email_limpio):
                return {
                    "valido": False,
                    "error": "Formato de email inválido",
                    "valor_original": email_str,
                    "valor_formateado": email_limpio,
                    "formato_esperado": "usuario@dominio.com",
                    "ejemplo_valido": "usuario@ejemplo.com"
                }
            
            # Extraer partes del email
            partes_email = email_limpio.split('@')
            usuario = partes_email[0]
            dominio = partes_email[1]
            
            # Validaciones adicionales
            if len(usuario) == 0:
                return {
                    "valido": False,
                    "error": "La parte del usuario no puede estar vacía",
                    "valor_original": email_str,
                    "valor_formateado": email_limpio
                }
            
            if len(dominio) == 0:
                return {
                    "valido": False,
                    "error": "El dominio no puede estar vacío",
                    "valor_original": email_str,
                    "valor_formateado": email_limpio
                }
            
            # Verificar dominio bloqueado
            if verificar_dominio:
                if dominio in ValidadorEmail.DOMINIOS_BLOQUEADOS:
                    return {
                        "valido": False,
                        "error": f"Dominio '{dominio}' no permitido",
                        "valor_original": email_str,
                        "valor_formateado": email_limpio,
                        "razon": "Dominio de email temporal bloqueado",
                        "dominios_bloqueados": ValidadorEmail.DOMINIOS_BLOQUEADOS
                    }
            
            # Determinar qué cambios se realizaron
            cambios_realizados = []
            if email_str != email_limpio:
                if email_str.strip() != email_limpio:
                    cambios_realizados.append("Espacios removidos")
                if email_str.lower() != email_limpio:
                    cambios_realizados.append("Convertido a minúsculas")
            
            return {
                "valido": True,
                "valor_original": email_str,
                "valor_formateado": email_limpio,
                "usuario": usuario,
                "dominio": dominio,
                "cambio_realizado": email_str != email_limpio,
                "cambios_aplicados": cambios_realizados,
                "normalizacion": {
                    "espacios_removidos": email_str.strip() != email_str,
                    "convertido_minusculas": email_str.lower() != email_str,
                    "aroba_normalizada": '@' in email_limpio
                }
            }
            
        except Exception as e:
            logger.error(f"Error validando email: {e}")
            return {
                "valido": False,
                "error": f"Error de validación: {str(e)}",
                "valor_original": email_str
            }


class ServicioCorreccionDatos:
    """
    🔧 Servicio principal para corrección de datos incorrectos
    """
    
    @staticmethod
    def corregir_datos_cliente(
        cliente_id: int,
        datos_correccion: Dict[str, Any],
        pais: str = "VENEZUELA"
    ) -> Dict[str, Any]:
        """
        🔧 Corregir múltiples datos de un cliente
        """
        try:
            resultados_correccion = {
                "cliente_id": cliente_id,
                "correcciones_aplicadas": [],
                "errores_encontrados": [],
                "requiere_recalculo_amortizacion": False,
                "cambios_realizados": False
            }
            
            # Procesar cada campo a corregir
            for campo, nuevo_valor in datos_correccion.items():
                try:
                    if campo == "telefono":
                        resultado = ValidadorTelefono.validar_y_formatear_telefono(nuevo_valor, pais)
                        
                    elif campo == "cedula":
                        resultado = ValidadorCedula.validar_y_formatear_cedula(nuevo_valor, pais)
                        
                    elif campo == "email":
                        resultado = ValidadorEmail.validar_email(nuevo_valor)
                        
                    elif campo == "fecha_entrega":
                        resultado = ValidadorFecha.validar_fecha_entrega(nuevo_valor)
                        if resultado.get("requiere_recalculo_amortizacion"):
                            resultados_correccion["requiere_recalculo_amortizacion"] = True
                    
                    elif campo == "fecha_pago":
                        resultado = ValidadorFecha.validar_fecha_pago(nuevo_valor)
                        
                    elif campo in ["total_financiamiento", "monto_pagado", "cuota_inicial"]:
                        tipo_monto = campo.upper()
                        resultado = ValidadorMonto.validar_y_formatear_monto(nuevo_valor, tipo_monto)
                        
                    elif campo == "amortizaciones":
                        resultado = ValidadorAmortizaciones.validar_amortizaciones(nuevo_valor)
                        
                    else:
                        # Campo no requiere validación especial
                        resultado = {
                            "valido": True,
                            "valor_original": nuevo_valor,
                            "valor_formateado": str(nuevo_valor).strip(),
                            "cambio_realizado": False
                        }
                    
                    # Agregar resultado
                    if resultado["valido"]:
                        resultados_correccion["correcciones_aplicadas"].append({
                            "campo": campo,
                            "valor_anterior": resultado["valor_original"],
                            "valor_nuevo": resultado["valor_formateado"],
                            "cambio_realizado": resultado.get("cambio_realizado", False)
                        })
                        
                        if resultado.get("cambio_realizado"):
                            resultados_correccion["cambios_realizados"] = True
                    else:
                        resultados_correccion["errores_encontrados"].append({
                            "campo": campo,
                            "error": resultado["error"],
                            "valor_intentado": nuevo_valor,
                            "sugerencia": resultado.get("formato_esperado") or resultado.get("ejemplo_valido")
                        })
                
                except Exception as e:
                    resultados_correccion["errores_encontrados"].append({
                        "campo": campo,
                        "error": f"Error procesando campo: {str(e)}",
                        "valor_intentado": nuevo_valor
                    })
            
            return resultados_correccion
            
        except Exception as e:
            logger.error(f"Error corrigiendo datos: {e}")
            return {
                "cliente_id": cliente_id,
                "error_general": str(e),
                "correcciones_aplicadas": [],
                "errores_encontrados": []
            }
    
    @staticmethod
    def detectar_datos_incorrectos_masivo(db, limite: int = 100) -> Dict[str, Any]:
        """
        🔍 Detectar datos incorrectos en la base de datos masivamente
        """
        try:
            from app.models.cliente import Cliente
            from app.models.pago import Pago
            
            # Obtener clientes con posibles errores
            clientes = db.query(Cliente).filter(Cliente.activo == True).limit(limite).all()
            
            clientes_con_errores = []
            tipos_errores = {
                "telefono_mal_formateado": 0,
                "cedula_sin_letra": 0,
                "email_invalido": 0,
                "fecha_error": 0,
                "monto_error": 0
            }
            
            for cliente in clientes:
                errores_cliente = []
                
                # Verificar teléfono
                if cliente.telefono and not cliente.telefono.startswith("+"):
                    errores_cliente.append({
                        "campo": "telefono",
                        "valor_actual": cliente.telefono,
                        "problema": "Sin código de país",
                        "solucion_sugerida": f"+58 {cliente.telefono}"
                    })
                    tipos_errores["telefono_mal_formateado"] += 1
                
                # Verificar cédula
                if cliente.cedula and cliente.cedula.isdigit():
                    errores_cliente.append({
                        "campo": "cedula",
                        "valor_actual": cliente.cedula,
                        "problema": "Sin letra V/E",
                        "solucion_sugerida": f"V{cliente.cedula}"
                    })
                    tipos_errores["cedula_sin_letra"] += 1
                
                # Verificar email
                if cliente.email and "@" not in cliente.email:
                    errores_cliente.append({
                        "campo": "email",
                        "valor_actual": cliente.email,
                        "problema": "Formato de email inválido",
                        "solucion_sugerida": "Corregir formato"
                    })
                    tipos_errores["email_invalido"] += 1
                
                if errores_cliente:
                    clientes_con_errores.append({
                        "cliente_id": cliente.id,
                        "nombre": cliente.nombre_completo,
                        "cedula": cliente.cedula,
                        "errores": errores_cliente,
                        "total_errores": len(errores_cliente)
                    })
            
            # Verificar pagos con errores
            pagos_error = db.query(Pago).filter(
                Pago.observaciones.like("%ERROR%")
            ).limit(50).all()
            
            for pago in pagos_error:
                if "MONTO PAGADO" in pago.observaciones:
                    tipos_errores["monto_error"] += 1
            
            return {
                "titulo": "🔍 DETECCIÓN MASIVA DE DATOS INCORRECTOS",
                "fecha_analisis": datetime.now().isoformat(),
                "clientes_analizados": len(clientes),
                "clientes_con_errores": len(clientes_con_errores),
                "porcentaje_errores": round(len(clientes_con_errores) / len(clientes) * 100, 2),
                
                "tipos_errores_encontrados": tipos_errores,
                
                "clientes_requieren_correccion": clientes_con_errores[:20],  # Top 20
                
                "acciones_recomendadas": [
                    "Usar herramienta de corrección masiva",
                    "Configurar validadores en formularios",
                    "Implementar auto-formateo en frontend",
                    "Capacitar usuarios en formatos correctos"
                ],
                
                "herramientas_disponibles": {
                    "correccion_individual": "POST /api/v1/validadores/corregir-cliente/{id}",
                    "correccion_masiva": "POST /api/v1/validadores/corregir-masivo",
                    "validacion_tiempo_real": "POST /api/v1/validadores/validar-campo"
                }
            }
            
        except Exception as e:
            logger.error(f"Error detectando datos incorrectos: {e}")
            return {"error": str(e)}


class AutoFormateador:
    """
    ✨ Auto-formateador para uso en tiempo real en el frontend
    """
    
    @staticmethod
    def formatear_mientras_escribe(campo: str, valor: str, pais: str = "VENEZUELA") -> Dict[str, Any]:
        """
        ✨ Formatear valor mientras el usuario escribe (para frontend)
        """
        try:
            if campo == "telefono":
                return AutoFormateador._formatear_telefono_tiempo_real(valor, pais)
            elif campo == "cedula":
                return AutoFormateador._formatear_cedula_tiempo_real(valor, pais)
            elif campo == "monto":
                return AutoFormateador._formatear_monto_tiempo_real(valor)
            else:
                return {
                    "valor_formateado": valor,
                    "cursor_posicion": len(valor),
                    "valido": True
                }
                
        except Exception as e:
            return {
                "valor_formateado": valor,
                "cursor_posicion": len(valor),
                "valido": False,
                "error": str(e)
            }
    
    @staticmethod
    def _formatear_telefono_tiempo_real(valor: str, pais: str) -> Dict[str, Any]:
        """Formatear teléfono mientras se escribe"""
        # Limpiar solo números
        numeros = re.sub(r'[^\d]', '', valor)
        
        if pais.upper() == "VENEZUELA":
            if len(numeros) == 0:
                return {"valor_formateado": "", "cursor_posicion": 0, "valido": False}
            elif len(numeros) <= 3:
                return {"valor_formateado": f"+58 {numeros}", "cursor_posicion": len(f"+58 {numeros}"), "valido": False}
            elif len(numeros) <= 10:
                formatted = f"+58 {numeros[:3]} {numeros[3:]}"
                return {"valor_formateado": formatted, "cursor_posicion": len(formatted), "valido": len(numeros) == 10}
            else:
                # Truncar si es muy largo
                numeros = numeros[:10]
                formatted = f"+58 {numeros[:3]} {numeros[3:]}"
                return {"valor_formateado": formatted, "cursor_posicion": len(formatted), "valido": True}
        
        return {"valor_formateado": valor, "cursor_posicion": len(valor), "valido": False}
    
    @staticmethod
    def _formatear_cedula_tiempo_real(valor: str, pais: str) -> Dict[str, Any]:
        """Formatear cédula mientras se escribe"""
        if pais.upper() == "VENEZUELA":
            # Limpiar entrada
            limpio = re.sub(r'[^\dVEJG]', '', valor.upper())
            
            # Auto-agregar V si empieza con número
            if limpio and limpio[0].isdigit():
                limpio = "V" + limpio
            
            return {
                "valor_formateado": limpio,
                "cursor_posicion": len(limpio),
                "valido": len(limpio) >= 8 and len(limpio) <= 9 and limpio[0] in ["V", "E", "J", "G"]
            }
        
        return {"valor_formateado": valor, "cursor_posicion": len(valor), "valido": False}
    
    @staticmethod
    def _formatear_monto_tiempo_real(valor: str) -> Dict[str, Any]:
        """Formatear monto mientras se escribe"""
        # Limpiar entrada
        numeros = re.sub(r'[^\d.]', '', valor)
        
        # Validar formato decimal
        partes = numeros.split('.')
        if len(partes) > 2:
            # Más de un punto decimal
            numeros = partes[0] + '.' + ''.join(partes[1:])[:2]
        elif len(partes) == 2 and len(partes[1]) > 2:
            # Más de 2 decimales
            numeros = partes[0] + '.' + partes[1][:2]
        
        try:
            if numeros and numeros != ".":
                monto = float(numeros)
                # Formatear con comas para miles
                if '.' in numeros:
                    entero, decimal = numeros.split('.')
                    entero_formateado = f"{int(entero):,}" if entero else "0"
                    formateado = f"${entero_formateado}.{decimal}"
                else:
                    formateado = f"${int(numeros):,}" if numeros else "$0"
                
                return {
                    "valor_formateado": formateado,
                    "cursor_posicion": len(formateado),
                    "valido": monto > 0
                }
            else:
                return {"valor_formateado": "$", "cursor_posicion": 1, "valido": False}
                
        except ValueError:
            return {"valor_formateado": valor, "cursor_posicion": len(valor), "valido": False}


# ============================================
# VALIDADORES ADICIONALES CRÍTICOS
# ============================================

class ValidadorEdad:
    """
    📅 Validador de edad del cliente
    Requisito legal para contratos de financiamiento
    """
    
    EDAD_MINIMA = 18  # Mayoría de edad
    EDAD_MAXIMA = 80  # Límite prudencial
    
    @staticmethod
    def validar_edad(fecha_nacimiento: str) -> Dict[str, Any]:
        """
        Validar que el cliente tenga edad legal para contratar
        
        Args:
            fecha_nacimiento: Fecha en formato DD/MM/YYYY, YYYY-MM-DD o date object
            
        Returns:
            Dict con validación y edad calculada
        """
        try:
            # Convertir a date si es string
            if isinstance(fecha_nacimiento, str):
                # Intentar diferentes formatos
                for formato in ["%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"]:
                    try:
                        fecha = datetime.strptime(fecha_nacimiento, formato).date()
                        break
                    except ValueError:
                        continue
                else:
                    return {
                        "valido": False,
                        "error": "Formato de fecha inválido. Use DD/MM/YYYY",
                        "edad": None
                    }
            elif isinstance(fecha_nacimiento, date):
                fecha = fecha_nacimiento
            else:
                return {
                    "valido": False,
                    "error": "Tipo de dato inválido para fecha",
                    "edad": None
                }
            
            # Calcular edad
            hoy = date.today()
            edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
            
            # Validar que no sea fecha futura
            if fecha > hoy:
                return {
                    "valido": False,
                    "error": "La fecha de nacimiento no puede ser futura",
                    "edad": None,
                    "fecha_nacimiento": fecha.isoformat()
                }
            
            # Validar edad mínima
            if edad < ValidadorEdad.EDAD_MINIMA:
                return {
                    "valido": False,
                    "error": f"El cliente debe ser mayor de {ValidadorEdad.EDAD_MINIMA} años (edad actual: {edad} años)",
                    "edad": edad,
                    "edad_minima": ValidadorEdad.EDAD_MINIMA,
                    "fecha_nacimiento": fecha.isoformat()
                }
            
            # Validar edad máxima
            if edad > ValidadorEdad.EDAD_MAXIMA:
                return {
                    "valido": False,
                    "error": f"La edad máxima permitida es {ValidadorEdad.EDAD_MAXIMA} años (edad actual: {edad} años)",
                    "edad": edad,
                    "edad_maxima": ValidadorEdad.EDAD_MAXIMA,
                    "fecha_nacimiento": fecha.isoformat()
                }
            
            # Todo correcto
            return {
                "valido": True,
                "edad": edad,
                "fecha_nacimiento": fecha.isoformat(),
                "mensaje": f"Cliente tiene {edad} años (edad válida para contrato)"
            }
            
        except Exception as e:
            logger.error(f"Error validando edad: {e}")
            return {
                "valido": False,
                "error": f"Error al validar edad: {str(e)}",
                "edad": None
            }


class ValidadorCoherenciaFinanciera:
    """
    💰 Validador de coherencia financiera
    Asegura que los datos de financiamiento sean coherentes y viables
    """
    
    CUOTA_INICIAL_MINIMA_PORCENTAJE = 10.0  # 10% mínimo
    CUOTA_INICIAL_MAXIMA_PORCENTAJE = 50.0  # 50% máximo recomendado
    
    @staticmethod
    def validar_coherencia(
        total_financiamiento: Decimal,
        cuota_inicial: Decimal,
        numero_amortizaciones: int,
        modalidad_pago: str = "MENSUAL"
    ) -> Dict[str, Any]:
        """
        Validar coherencia entre datos financieros
        
        Args:
            total_financiamiento: Monto total del financiamiento
            cuota_inicial: Cuota inicial a pagar
            numero_amortizaciones: Número de cuotas
            modalidad_pago: SEMANAL, QUINCENAL, MENSUAL, BIMENSUAL
        """
        errores = []
        advertencias = []
        
        try:
            # Convertir a Decimal si es necesario
            if not isinstance(total_financiamiento, Decimal):
                total_financiamiento = Decimal(str(total_financiamiento))
            if not isinstance(cuota_inicial, Decimal):
                cuota_inicial = Decimal(str(cuota_inicial))
            
            # 1. Cuota inicial no puede ser mayor al total
            if cuota_inicial > total_financiamiento:
                errores.append("La cuota inicial no puede ser mayor al total del financiamiento")
            
            # 2. Validar cuota inicial mínima (10%)
            cuota_minima = total_financiamiento * Decimal(ValidadorCoherenciaFinanciera.CUOTA_INICIAL_MINIMA_PORCENTAJE) / Decimal("100")
            if cuota_inicial < cuota_minima:
                errores.append(f"La cuota inicial debe ser al menos el {ValidadorCoherenciaFinanciera.CUOTA_INICIAL_MINIMA_PORCENTAJE}% del total (mínimo: ${cuota_minima:.2f})")
            
            # 3. Advertencia si cuota inicial es muy alta
            cuota_maxima_recomendada = total_financiamiento * Decimal(ValidadorCoherenciaFinanciera.CUOTA_INICIAL_MAXIMA_PORCENTAJE) / Decimal("100")
            if cuota_inicial > cuota_maxima_recomendada:
                advertencias.append(f"La cuota inicial es muy alta ({(cuota_inicial/total_financiamiento*100):.1f}% del total)")
            
            # 4. Monto financiado debe ser positivo
            monto_financiado = total_financiamiento - cuota_inicial
            if monto_financiado <= 0:
                errores.append("El monto a financiar debe ser mayor a cero")
            
            # 5. Validar número de amortizaciones coherente con modalidad
            if modalidad_pago == "SEMANAL" and numero_amortizaciones > 208:  # 4 años máximo
                advertencias.append("Número de amortizaciones muy alto para modalidad semanal")
            elif modalidad_pago == "QUINCENAL" and numero_amortizaciones > 96:  # 4 años máximo
                advertencias.append("Número de amortizaciones muy alto para modalidad quincenal")
            elif modalidad_pago == "MENSUAL" and numero_amortizaciones > 84:  # 7 años máximo
                advertencias.append("Número de amortizaciones muy alto para modalidad mensual")
            
            # Calcular cuota aproximada
            if monto_financiado > 0 and numero_amortizaciones > 0:
                cuota_aproximada = monto_financiado / Decimal(str(numero_amortizaciones))
            else:
                cuota_aproximada = Decimal("0")
            
            # Resultado
            if errores:
                return {
                    "valido": False,
                    "errores": errores,
                    "advertencias": advertencias,
                    "detalles": {
                        "total_financiamiento": float(total_financiamiento),
                        "cuota_inicial": float(cuota_inicial),
                        "monto_financiado": float(monto_financiado),
                        "porcentaje_cuota_inicial": float((cuota_inicial / total_financiamiento * 100)) if total_financiamiento > 0 else 0,
                        "cuota_aproximada": float(cuota_aproximada)
                    }
                }
            else:
                return {
                    "valido": True,
                    "advertencias": advertencias,
                    "mensaje": "Datos financieros coherentes",
                    "detalles": {
                        "total_financiamiento": float(total_financiamiento),
                        "cuota_inicial": float(cuota_inicial),
                        "monto_financiado": float(monto_financiado),
                        "porcentaje_cuota_inicial": float((cuota_inicial / total_financiamiento * 100)) if total_financiamiento > 0 else 0,
                        "cuota_aproximada": float(cuota_aproximada)
                    }
                }
                
        except Exception as e:
            logger.error(f"Error validando coherencia financiera: {e}")
            return {
                "valido": False,
                "error": f"Error al validar coherencia: {str(e)}"
            }


class ValidadorDuplicados:
    """
    🔍 Validador de duplicados en base de datos
    Previene fraude y errores de captura
    """
    
    @staticmethod
    def validar_chasis_unico(chasis: str, db_session, cliente_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Validar que el número de chasis sea único en la BD
        
        Args:
            chasis: Número de chasis del vehículo
            db_session: Sesión de base de datos
            cliente_id: ID del cliente (para excluir en updates)
        """
        try:
            from app.models.cliente import Cliente
            
            if not chasis or not chasis.strip():
                return {
                    "valido": True,  # Chasis es opcional
                    "mensaje": "Chasis no proporcionado (opcional)"
                }
            
            # Limpiar y normalizar
            chasis_limpio = chasis.strip().upper()
            
            # Buscar duplicados
            query = db_session.query(Cliente).filter(Cliente.chasis == chasis_limpio)
            
            # Excluir el cliente actual si es un update
            if cliente_id:
                query = query.filter(Cliente.id != cliente_id)
            
            existe = query.first()
            
            if existe:
                return {
                    "valido": False,
                    "error": f"El número de chasis ya está registrado para el cliente {existe.nombre_completo} (ID: {existe.id})",
                    "chasis": chasis_limpio,
                    "cliente_existente": {
                        "id": existe.id,
                        "nombre": existe.nombre_completo,
                        "cedula": existe.cedula
                    }
                }
            
            return {
                "valido": True,
                "chasis": chasis_limpio,
                "mensaje": "Número de chasis único"
            }
            
        except Exception as e:
            logger.error(f"Error validando chasis: {e}")
            return {
                "valido": False,
                "error": f"Error al validar chasis: {str(e)}"
            }
    
    @staticmethod
    def validar_email_unico(email: str, db_session, cliente_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Validar que el email sea único (opcional, puede haber clientes sin email)
        """
        try:
            from app.models.cliente import Cliente
            
            if not email or not email.strip():
                return {
                    "valido": True,  # Email es opcional
                    "mensaje": "Email no proporcionado (opcional)"
                }
            
            # Normalizar
            email_limpio = email.strip().lower()
            
            # Buscar duplicados
            query = db_session.query(Cliente).filter(Cliente.email == email_limpio)
            
            # Excluir el cliente actual si es un update
            if cliente_id:
                query = query.filter(Cliente.id != cliente_id)
            
            existe = query.first()
            
            if existe:
                return {
                    "valido": False,
                    "error": f"El email ya está registrado para el cliente {existe.nombre_completo}",
                    "email": email_limpio,
                    "cliente_existente": {
                        "id": existe.id,
                        "nombre": existe.nombre_completo,
                        "cedula": existe.cedula
                    }
                }
            
            return {
                "valido": True,
                "email": email_limpio,
                "mensaje": "Email único"
            }
            
        except Exception as e:
            logger.error(f"Error validando email: {e}")
            return {
                "valido": False,
                "error": f"Error al validar email: {str(e)}"
            }