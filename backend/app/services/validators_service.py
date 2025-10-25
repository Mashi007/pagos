from datetime import date
# backend/app/services/validators_service.py"""Servicio de Validadores y Auto-FormateoSistema completo para validar y"""
# import Decimal, InvalidOperationfrom typing import Any, Dict, Optionalfrom app.models.cliente import Clientefrom
# app.models.pago import Pagologger = logging.getLogger(__name__)class ValidadorTelefono: """ 📱 Validador y formateador de"""
# "longitud_sin_codigo": 10, # 809 1234567 "patron_completo": r"^\+1\s?[0-9]{3}\s?[0-9]{7}$", "formato_display": "+1 XXX
# XXXXXXX", }, "COLOMBIA": 
# r"^\+57\s?[0-9]{3}\s?[0-9]{7}$", "formato_display": "+57 XXX XXXXXXX", }, } @staticmethod def
# _validar_entrada_telefono(telefono: str) -> Optional[Dict[str, Any]]: """Validar entrada básica de teléfono""" if not
# telefono: return { "valido": False, "error": "Teléfono requerido", "valor_original": telefono, "valor_formateado": None, }
# return None @staticmethod def _validar_pais_soportado( pais: str, telefono: str ) -> Optional[Dict[str, Any]]: """Validar
# que el país esté soportado""" config = ValidadorTelefono.PAISES_CONFIG.get(pais.upper()) if not config: return """
# False, "error": f"País '{pais}' no soportado", "valor_original": telefono, "valor_formateado": None, } return config
# @staticmethod def _formatear_telefono_con_codigo( telefono_limpio: str, config: Dict[str, Any] ) -> str: """Formatear
# teléfono que ya tiene código de país""" return """
# telefono_limpio[5:] ) @staticmethod def _formatear_telefono_con_plus( telefono_limpio: str, config: Dict[str, Any] ) ->
# str: """Formatear teléfono que ya tiene + y código""" numero_sin_plus = telefono_limpio[1:] return 
# numero_sin_plus[:2] + " " + numero_sin_plus[2:5] + " " + numero_sin_plus[5:] ) @staticmethod def _formatear_telefono_local
# telefono_limpio: str, config: Dict[str, Any], pais: str, telefono_original: str, ) -> Dict[str, Any]: """Formatear teléfono
# local sin código de país""" operadora = telefono_limpio[:3] if operadora in config["operadoras"]: numero_formateado = """
# f"{config['codigo_pais']} {operadora} {telefono_limpio[3:]}" ) return 
# None} else: return 
# + f"para \ {pais}. Válidas: {', '.join(config['operadoras'])}" ), "valor_original": telefono_original, "valor_formateado":
# None, "sugerencia": f"Debe comenzar con: {', '.join(config \ ['operadoras'])}", }, } @staticmethod def
# _validar_formato_final( numero_formateado: str, config: Dict[str, Any], telefono_original: str ) -> Dict[str, Any]:
# """Validar formato final del teléfono""" if re.match(config["patron_completo"], numero_formateado): return 
# "operadora": numero_formateado.split()[1], "cambio_realizado": telefono_original != numero_formateado, } else: return 
# numero_formateado, } @staticmethod def validar_y_formatear_telefono( telefono: str, pais: str = "VENEZUELA" ) -> Dict[str,
# 1234567" - "424 1234567" → "+58 424 1234567" - "+58 424 1234567" → "+58 424 1234567" (ya correcto) """ try: # 1. Validar"""
# entrada básica error_entrada = ValidadorTelefono._validar_entrada_telefono( telefono ) if error_entrada: return
# error_entrada # 2. Limpiar entrada telefono_limpio = re.sub(r"[^\d+]", "", telefono.strip()) # 3. Validar país soportado
# config = ValidadorTelefono._validar_pais_soportado(pais, telefono) if isinstance(config, dict) and "valido" in config:
# = None if telefono_limpio.startswith( config["codigo_pais"].replace("+", "") ): # Ya tiene código de país: "584241234567"
# numero_formateado = ( ValidadorTelefono._formatear_telefono_con_codigo( telefono_limpio, config ) ) elif
# telefono_limpio.startswith(config["codigo_pais"]): # Ya tiene + y código: "+584241234567" numero_formateado = 
# ValidadorTelefono._formatear_telefono_con_plus( telefono_limpio, config ) ) elif len(telefono_limpio) ==
# config["longitud_sin_codigo"]: # Solo número local: "4241234567" resultado_local =
# ValidadorTelefono._formatear_telefono_local( telefono_limpio, config, pais, telefono ) if resultado_local["error"]: return
# resultado_local["error"] numero_formateado = resultado_local["numero_formateado"] else: return 
# f"Longitud incorrecta. Formato esperado: {config['formato_display']}", "valor_original": telefono, "valor_formateado":
# None, "longitud_actual": len(telefono_limpio), "longitud_esperada": config["longitud_sin_codigo"], } # 6. Validar formato
# final return ValidadorTelefono._validar_formato_final( numero_formateado, config, telefono ) except Exception as e:
# logger.error(f"Error validando teléfono: {e}") return { "valido": False, "error": f"Error de validación: {str(e)}",
# "valor_original": telefono, "valor_formateado": None, } @staticmethod def _crear_error_formato
# error: str, config: Dict, longitud_actual: int = None, ) -> Dict[str, Any]: """Crear respuesta de error para formato de
# teléfono""" resultado = """
# tiene {len(numero_sin_codigo)}", config, ) error_primer_digito = ValidadorTelefono._validar_primer_digito
# numero_sin_codigo, telefono_limpio, config ) if error_primer_digito: return error_primer_digito return
# ValidadorTelefono._crear_exito_formato( telefono_limpio, f"+58{numero_sin_codigo}", config ) @staticmethod def
# _procesar_telefono_con_mas_58( telefono_limpio: str, config: Dict ) -> Optional[Dict[str, Any]]: """Procesar teléfono que
# empieza con +58""" numero_sin_codigo = telefono_limpio[3:] # Quitar "+58" if len(numero_sin_codigo) != 10: return"""
# tiene {len(numero_sin_codigo)}", config, ) error_primer_digito = ValidadorTelefono._validar_primer_digito
# numero_sin_codigo, telefono_limpio, config ) if error_primer_digito: return error_primer_digito return
# ValidadorTelefono._crear_exito_formato( telefono_limpio, telefono_limpio, config ) @staticmethod def
# _procesar_telefono_local( telefono_limpio: str, config: Dict ) -> Optional[Dict[str, Any]]: """Procesar teléfono local de"""
# error_primer_digito: return error_primer_digito return ValidadorTelefono._crear_exito_formato
# f"+58{telefono_limpio}", config ) @staticmethod def _formatear_telefono_venezolano( telefono_limpio: str, config: Dict ) ->
# Ya tiene código de país sin +: "581234567890" resultado = ValidadorTelefono._procesar_telefono_con_58
# config ) if resultado: return resultado elif telefono_limpio.startswith("+58"): # Ya tiene +58: "+581234567890" resultado =
# ValidadorTelefono._procesar_telefono_con_mas_58( telefono_limpio, config ) if resultado: return resultado elif
# len(telefono_limpio) == 10: # Solo número local: "1234567890" resultado = ValidadorTelefono._procesar_telefono_local
# telefono_limpio, config ) if resultado: return resultado else: return ValidadorTelefono._crear_error_formato
# "Error interno en el procesamiento", config ) except Exception as e: logger.error
# {e}") return ValidadorTelefono._crear_error_formato( telefono_limpio, f"Error de formateo: {str(e)}", config )class
# ValidadorCedula: """ 📝 Validador y formateador de cédulas Soporta múltiples países con auto-formateo """ PAISES_CEDULA = 
# Sin prefijo "longitud_numero": [8, 9, 10], "patron": r"^\d{8,10}$", "formato_display": "12345678", "descripcion": "Cédula
# - "v12345678" → "V12345678" (mayúscula) - "V-12345678" → "V12345678" (quita guiones) """ try: if not cedula: return """
# "valido": False, "error": "Cédula requerida", "valor_original": cedula, "valor_formateado": None, } config =
# ValidadorCedula.PAISES_CEDULA.get(pais.upper()) if not config: return { "valido": False, "error": f"País '{pais}' no
# soportado", "valor_original": cedula, "valor_formateado": None, } # Limpiar entrada cedula_limpia = re.sub
# cedula.strip().upper()) if pais.upper() == "VENEZUELA": return ValidadorCedula._formatear_cedula_venezolana
# config ) elif pais.upper() == "DOMINICANA": return ValidadorCedula._formatear_cedula_dominicana( cedula, config ) elif
# pais.upper() == "COLOMBIA": return ValidadorCedula._formatear_cedula_colombiana( cedula_limpia, config ) else: return 
# "valido": False, "error": "País no implementado", "valor_original": cedula, } except Exception as e: logger.error
# validando cédula: {e}") return { "valido": False, "error": f"Error de validación: {str(e)}", "valor_original": cedula,
# "valor_formateado": None, } @staticmethod def _formatear_cedula_venezolana( cedula_limpia: str, config: Dict ) -> Dict[str,
# Any]: """ Formatear cédula venezolana con validación estricta: - DEBE empezar por V, E o J (siempre) - Seguido de"""
# re.sub(r"[^VEJ\d]", "", cedula_limpia.upper()) # Validar que tenga un prefijo válido desde el inicio if cedula_limpia and
# cedula_limpia[0] not in ["V", "E", "J"]: # Si no tiene prefijo válido, rechazar inmediatamente return 
# "error": ( f"Prefijo '{cedula_limpia[0] if cedula_limpia else 'ninguno'}' no válido. DEBE empezar por V, E o J" ),
# else: cedula_formateada = cedula_limpia # Validar formato final con regex estricto if re.match
# cedula_formateada): prefijo = cedula_formateada[0] numero = cedula_formateada[1:] # Validar que el prefijo sea válido 
# "tipo": ( { "V": "Venezolano", "E": "Extranjero", "J": "Jurídico", }.get(prefijo, "Desconocido") ), "cambio_realizado":
# numero.isdigit(), "sin_caracteres_especiales": True, }, } return 
# cedula_formateada, "pais": "DOMINICANA", "cambio_realizado": cedula != cedula_formateada, } return 
# "error": f"Formato inválido. Esperado: {config['formato_display']}", "valor_original": cedula, "formato_esperado":
# config["descripcion"], } @staticmethod def _formatear_cedula_colombiana( cedula_limpia: str, config: Dict ) -> Dict[str,
# Any]: """Formatear cédula colombiana""" if ( cedula_limpia.isdigit() and len(cedula_limpia) in config["longitud_numero"] ):
# return 
# "cambio_realizado": False, } return { "valido": False, "error": f"Formato inválido. Esperado: {config['formato_display']}",
# "valor_original": cedula_limpia, "formato_esperado": config["descripcion"], }class ValidadorNombre: """ 👤 Validador de"""
# False, "error": "Nombre requerido", "valor_original": nombre, "palabras_encontradas": 0, "palabras_requeridas": 4, } #
# Limpiar y dividir en palabras palabras = [p.strip() for p in nombre.split() if p.strip()] if len(palabras) < 4: return 
# nombre, "palabras_encontradas": len(palabras), "palabras_requeridas": 4, "palabras": palabras, } # Validar que cada palabra
# "valido": False, "error": f"Palabras muy cortas: {palabras_invalidas}", "valor_original": nombre, "palabras_encontradas":
# len(palabras), "palabras_invalidas": palabras_invalidas, } return 
# > 2 else palabras[-1] ), "segundo_apellido": palabras[-1] if len(palabras) > 3 else "", } except Exception as e:
# logger.error(f"Error validando nombre: {e}") return { "valido": False, "error": f"Error de validación: {str(e)}",
# "valor_original": nombre, }class ValidadorFecha: """ 📅 Validador y formateador de fechas con reglas de negocio """
# @staticmethod def validar_fecha_entrega(fecha_str: str) -> Dict[str, Any]: """ 📅 Validar fecha de entrega del vehículo
# """ try: if not fecha_str or fecha_str.upper() == "ERROR": return """
# "valor_original": fecha_str, "valor_formateado": None, "requiere_calendario": True, } # Intentar parsear diferentes
# recalcular la tabla de amortización con la nueva fecha?" ), } except Exception as e: logger.error
# {e}") return { "valido": False, "error": f"Error de validación: {str(e)}", "valor_original": fecha_str, "valor_formateado":
# None, } @staticmethod def validar_fecha_pago(fecha_str: str) -> Dict[str, Any]: """ 📅 Validar fecha de pago Reglas: - No
# puede ser más de 1 día en el futuro - Debe ser fecha válida """ try: if not fecha_str or fecha_str.upper() == "ERROR":"""
# return { "valido": False, "error": "Fecha de pago requerida", "valor_original": fecha_str, "valor_formateado": None, }
# fecha_parseada = ValidadorFecha._parsear_fecha_flexible(fecha_str) if not fecha_parseada: return 
# return { "valido": False, "error": f"Error de validación: {str(e)}", "valor_original": fecha_str, } @staticmethod def
# _convertir_numero_serie_excel(fecha_limpia: str) -> Optional[date]: """Convertir número de serie de Excel a fecha""" if not
# (fecha_limpia.isdigit() and len(fecha_limpia) >= 4): return None try: numero_serie = int(fecha_limpia) # Excel cuenta desde
# OverflowError): return None @staticmethod def _validar_formato_fecha(fecha_limpia: str) -> bool: """Validar formato básico
# DD/MM/YYYY con regex""" return bool(re.match(r"^\d{2}/\d{2}/\d{4}$", fecha_limpia)) @staticmethod def
# _validar_componentes_fecha(dia: str, mes: str, año: str) -> bool: """Validar componentes individuales de la fecha""" #
# Validar que el día sea válido (01-31) if not (1 <= int(dia) <= 31): return False # Validar que el mes sea válido (01-12) if
# not (1 <= int(mes) <= 12): return False # Validar que el año sea razonable (1900-2100) if not (1900 <= int(año) <= 2100):
# return False return True @staticmethod def _validar_fecha_completa(fecha_limpia: str) -> Optional[date]: """Validar que la
# ValueError: return None @staticmethod def _parsear_fecha_flexible(fecha_str: str) -> Optional[date]: """ Parsear fecha con"""
# ValidadorFecha._convertir_numero_serie_excel( fecha_limpia ) if fecha_excel: return fecha_excel # 2. Validar formato básico
# con regex if not ValidadorFecha._validar_formato_fecha(fecha_limpia): return None try: # 3. Parsear estrictamente como
# fecha_limpia.split("/") # 5. Validar componentes individuales if not ValidadorFecha._validar_componentes_fecha
# año): return None # 6. Validar fecha completa return ValidadorFecha._validar_fecha_completa(fecha_limpia) except
# @staticmethod def validar_y_formatear_monto
# - "15,000.50" → 15000.50 - "$15,000" → 15000.00 """ try: if not monto_str or monto_str.upper() == "ERROR": return """
# "valido": False, "error": f"Monto {tipo_monto.lower()} requerido", "valor_original": monto_str, "valor_formateado": None,
# monto_str.strip()) # Intentar convertir a decimal try: monto_decimal = Decimal(monto_limpio) except InvalidOperation:
# return 
# "error": "El monto debe ser mayor a cero", "valor_original": monto_str, "valor_formateado": str(monto_decimal), } # Validar
# saldo_maximo ) if error_limite: return 
# "valor_formateado": f"{monto_decimal:.2f}", } # Formatear a 2 decimales monto_formateado =
# monto_decimal.quantize(Decimal("0.01")) return 
# str(monto_formateado), "valor_decimal": monto_formateado, "valor_display": f"${monto_formateado:,.2f}", "cambio_realizado":
# monto_str != str(monto_formateado), "tipo_monto": tipo_monto, } except Exception as e: logger.error
# monto: {e}") return { "valido": False, "error": f"Error de validación: {str(e)}", "valor_original": monto_str, }
# @staticmethod def _validar_limites_por_tipo( monto: Decimal, tipo: str, saldo_maximo: Optional[Decimal] ) -> Optional[str]:
# "Monto mínimo de financiamiento: $1" if monto > Decimal("50000000"): # 50M return "Monto máximo de financiamiento:
# $50,000,000" elif tipo == "MONTO_PAGO": if monto < Decimal("1"): return "Monto mínimo de pago: $1" if saldo_maximo and
# monto > saldo_maximo: return f"Monto no puede exceder el saldo " f"pendiente: ${saldo_maximo:,.2f}" elif tipo ==
# "CUOTA_INICIAL": if monto < Decimal("0"): return "Cuota inicial no puede ser negativa" return None # Sin erroresclass
# ValidadorAmortizaciones: """ 🔢 Validador de número de amortizaciones """ @staticmethod def
# validar_amortizaciones(amortizaciones_str: str) -> Dict[str, Any]: """ 🔢 Validar número de amortizaciones Reglas: - Debe"""
# "ERROR": return 
# "valor_formateado": None, "rango_valido": "1 - 84 meses", } # Intentar convertir a entero try: amortizaciones =
# int(float(amortizaciones_str.strip())) except ValueError: return 
# "valor_original": amortizaciones_str, "valor_formateado": None, } # Validar rango if amortizaciones < 1: return 
# False, "error": "Mínimo 1 amortización", "valor_original": amortizaciones_str, "valor_formateado": str(amortizaciones), }
# amortizaciones_str, "valor_formateado": str(amortizaciones), } return 
# round(amortizaciones / 12, 1), "cambio_realizado": amortizaciones_str.strip() != str(amortizaciones), } except Exception as
# e: logger.error(f"Error validando amortizaciones: {e}") return 
# {str(e)}", "valor_original": amortizaciones_str, }class ValidadorEmail: """ 📧 Validador de email con reglas avanzadas """
# DOMINIOS_BLOQUEADOS = [ "tempmail.org", "10minutemail.com", "guerrillamail.com", "mailinator.com", "throwaway.email", ]
# @staticmethod def _validar_entrada_email(email_str: str) -> Optional[Dict[str, Any]]: """Validar entrada básica de email"""
# if not email_str or email_str.upper() == "ERROR": return 
# email_str, "valor_formateado": None, } return None @staticmethod def _normalizar_email(email_str: str) -> str:
# _validar_simbolo_arroba( email_limpio: str, email_original: str ) -> Optional[Dict[str, Any]]: """Validar que contenga el
# símbolo @""" if "@" not in email_limpio: return """
# "valor_original": email_original, "valor_formateado": email_limpio, "formato_esperado": "usuario@dominio.com", } return
# None @staticmethod def _validar_formato_rfc( email_limpio: str, email_original: str ) -> Optional[Dict[str, Any]]:
# """Validar formato RFC 5322""" patron_email = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$" if not
# re.match(patron_email, email_limpio): return 
# "usuario@ejemplo.com", } return None @staticmethod def _extraer_partes_email(email_limpio: str) -> tuple[str, str]:
# """Extraer partes del email""" partes_email = email_limpio.split("@") return partes_email[0], partes_email[1] @staticmethod
# def _validar_partes_email( usuario: str, dominio: str, email_original: str, email_limpio: str ) -> Optional[Dict[str,
# Any]]: """Validar partes del email""" if len(usuario) == 0: return 
# puede estar vacía", "valor_original": email_original, "valor_formateado": email_limpio, } if len(dominio) == 0: return 
# email_limpio, } return None @staticmethod def _validar_dominio_bloqueado
# str, verificar_dominio: bool, ) -> Optional[Dict[str, Any]]: """Verificar dominio bloqueado""" if verificar_dominio and
# dominio in ValidadorEmail.DOMINIOS_BLOQUEADOS: return { "valido": False, "error": f"Dominio '{dominio}' no permitido",
# "valor_original": email_original, "valor_formateado": email_limpio, "razon": "Dominio de email temporal bloqueado",
# @staticmethod def validar_email( email_str: str, verificar_dominio: bool = True ) -> Dict[str, Any]: """ 📧 Validar email"""
# con normalización automática a minúsculas (VERSIÓN REFACTORIZADA) Características: - Convierte automáticamente a minúsculas
# Validar entrada básica error_entrada = ValidadorEmail._validar_entrada_email(email_str) if error_entrada: return
# error_entrada # 2. Normalizar email email_limpio = ValidadorEmail._normalizar_email(email_str) # 3. Validar símbolo @
# error_arroba = ValidadorEmail._validar_simbolo_arroba( email_limpio, email_str ) if error_arroba: return error_arroba # 4.
# Validar formato RFC error_formato = ValidadorEmail._validar_formato_rfc( email_limpio, email_str ) if error_formato: return
# error_formato # 5. Extraer partes del email usuario, dominio = ValidadorEmail._extraer_partes_email( email_limpio ) # 6.
# Validar partes del email error_partes = ValidadorEmail._validar_partes_email( usuario, dominio, email_str, email_limpio )
# if error_partes: return error_partes # 7. Verificar dominio bloqueado error_dominio =
# ValidadorEmail._validar_dominio_bloqueado( dominio, email_str, email_limpio, verificar_dominio ) if error_dominio: return
# email_limpio ) return 
# email_str, "aroba_normalizada": "@" in email_limpio, }, } except Exception as e: logger.error
# {e}") return { "valido": False, "error": f"Error de validación: {str(e)}", "valor_original": email_str, }class
# resultado = ( ValidadorTelefono.validar_y_formatear_telefono( nuevo_valor, pais ) ) elif campo == "cedula": resultado =
# ValidadorCedula.validar_y_formatear_cedula( nuevo_valor, pais ) elif campo == "email": resultado =
# ValidadorEmail.validar_email(nuevo_valor) elif campo == "fecha_entrega": resultado = ValidadorFecha.validar_fecha_entrega
# ] = True elif campo == "fecha_pago": resultado = ValidadorFecha.validar_fecha_pago( nuevo_valor ) elif campo in [
# "total_financiamiento", "monto_pagado", "cuota_inicial", ]: tipo_monto = campo.upper() resultado =
# ValidadorMonto.validar_y_formatear_monto( nuevo_valor, tipo_monto ) elif campo == "amortizaciones": resultado = 
# ValidadorAmortizaciones.validar_amortizaciones( nuevo_valor ) ) else: # Campo no requiere validación especial resultado = 
# "valido": True, "valor_original": nuevo_valor, "valor_formateado": str(nuevo_valor).strip(), "cambio_realizado": False, } #
# "valor_anterior": resultado["valor_original"], "valor_nuevo": resultado["valor_formateado"], "cambio_realizado":
# resultado.get( "cambio_realizado", False ), } ) if resultado.get("cambio_realizado"):
# campo, "error": resultado["error"], "valor_intentado": nuevo_valor, "sugerencia": ( resultado.get("formato_esperado") or
# "campo": campo, "error": f"Error procesando campo: {str(e)}", "valor_intentado": nuevo_valor, } ) return
# "telefono_mal_formateado": 0, "cedula_sin_letra": 0, "email_invalido": 0, "fecha_error": 0, "monto_error": 0, } for cliente
# in clientes: errores_cliente = [] # Verificar teléfono if cliente.telefono and not cliente.telefono.startswith("+"):
# errores_cliente.append
# cliente.cedula and cliente.cedula.isdigit(): errores_cliente.append
# cliente.email, "problema": "Formato de email inválido", "solucion_sugerida": "Corregir formato", } )
# cliente.nombre_completo, "cedula": cliente.cedula, "errores": errores_cliente, "total_errores": len(errores_cliente), } ) #
# len(clientes), "clientes_con_errores": len(clientes_con_errores), "porcentaje_errores": round( len(clientes_con_errores) /
# clientes_con_errores[ :20 ], # Top 20 "acciones_recomendadas": [ "Usar herramienta de corrección masiva", "Configurar
# "herramientas_disponibles": { "correccion_individual": "POST /api/v1/validadores \ /corregir-cliente/{id}",
# "correccion_masiva": "POST /api/v1/validadores/cor \ regir-masivo", "validacion_tiempo_real": "POST
# return {"error": str(e)}class AutoFormateador: """ ✨ Auto-formateador para uso en tiempo real en el frontend """
# @staticmethod def formatear_mientras_escribe( campo: str, valor: str, pais: str = "VENEZUELA" ) -> Dict[str, Any]: """ ✨
# Formatear valor mientras el usuario escribe (para frontend) """ try: if campo == "telefono": return"""
# AutoFormateador._formatear_telefono_tiempo_real( valor, pais ) elif campo == "cedula": return
# AutoFormateador._formatear_cedula_tiempo_real( valor, pais ) elif campo == "monto": return
# "valido": False, "error": str(e), } @staticmethod def _formatear_telefono_tiempo_real( valor: str, pais: str ) -> Dict[str,
# @staticmethod def _formatear_cedula_tiempo_real(valor: str, pais: str) -> Dict[str, Any]: """Formatear cédula mientras se"""
# re.sub(r"[^VEJ\d]", "", valor.upper()) # Auto-agregar V si empieza con número if limpio and limpio[0].isdigit(): limpio =
# "V" + limpio # Validar longitud mientras se escribe if len(limpio) == 0: valido = False elif len(limpio) == 1: valido =
# limpio[0] in ["V", "E", "J"] elif len(limpio) >= 2: prefijo = limpio[0] numero = limpio[1:] valido = 
# "E", "J"] and numero.isdigit() and 7 <= len(numero) <= 10 ) else: valido = False return 
# } @staticmethod def _formatear_monto_tiempo_real(valor: str) -> Dict[str, Any]: """Formatear monto mientras se escribe""" #
# f"{int(entero):,}" if entero else "0" formateado = f"${entero_formateado}.{decimal}" else: formateado =
# ============================================# VALIDADORES ADICIONALES CRÍTICOS#
# ============================================class ValidadorEdad: """ 📅 Validador de edad del cliente Requisito legal para
# _convertir_fecha_nacimiento( fecha_nacimiento: str, ) -> tuple[Optional[date], Optional[Dict[str, Any]]]: """Convertir"""
# fecha, None except ValueError: continue error = 
# "edad": None, } return None, error elif isinstance(fecha_nacimiento, date): return fecha_nacimiento, None else: error = 
# "valido": False, "error": "Tipo de dato inválido para fecha", "edad": None, } return None, error @staticmethod def
# _calcular_edad(fecha: date) -> int: """Calcular edad basada en fecha de nacimiento""" hoy = date.today() return 
# - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day)) ) @staticmethod def _validar_fecha_futura(fecha: date) ->
# Optional[Dict[str, Any]]: """Validar que la fecha no sea futura""" hoy = date.today() if fecha > hoy: return 
# False, "error": "La fecha de nacimiento no puede ser futura", "edad": None, "fecha_nacimiento": fecha.isoformat(), } return
# None @staticmethod def _validar_edad_minima( edad: int, fecha: date ) -> Optional[Dict[str, Any]]: """Validar edad
# mínima""" if edad < ValidadorEdad.EDAD_MINIMA: return """
# "fecha_nacimiento": fecha.isoformat(), } return None @staticmethod def _validar_edad_maxima( edad: int, fecha: date ) ->
# Optional[Dict[str, Any]]: """Validar edad máxima""" if edad > ValidadorEdad.EDAD_MAXIMA: return 
# "edad_maxima": ValidadorEdad.EDAD_MAXIMA, "fecha_nacimiento": fecha.isoformat(), } return None @staticmethod def
# validar_edad(fecha_nacimiento: str) -> Dict[str, Any]: """ Validar que el cliente tenga edad legal para contratar """
# REFACTORIZADA) Args: fecha_nacimiento: Fecha en formato DD/MM/YYYY, YYYY-MM-DD o date object Returns: Dict con validación y
# edad calculada """ try: # 1. Convertir fecha de nacimiento fecha, error_conversion = """
# ValidadorEdad._convertir_fecha_nacimiento(fecha_nacimiento) ) if error_conversion: return error_conversion # 2. Calcular
# edad edad = ValidadorEdad._calcular_edad(fecha) # 3. Validar fecha futura error_futura =
# ValidadorEdad._validar_fecha_futura(fecha) if error_futura: return error_futura # 4. Validar edad mínima error_minima =
# ValidadorEdad._validar_edad_minima(edad, fecha) if error_minima: return error_minima # 5. Validar edad máxima error_maxima
# = ValidadorEdad._validar_edad_maxima(edad, fecha) if error_maxima: return error_maxima # 6. Todo correcto return 
# para contrato)", } except Exception as e: logger.error(f"Error validando edad: {e}") return 
# f"Error al validar edad: {str(e)}", "edad": None, }class ValidadorCoherenciaFinanciera: """ 💰 Validador de coherencia"""
# 10% mínimo CUOTA_INICIAL_MAXIMA_PORCENTAJE = 50.0 # 50% máximo recomendado @staticmethod def validar_coherencia
# total_financiamiento: Decimal, cuota_inicial: Decimal, numero_amortizaciones: int, modalidad_pago: str = "MENSUAL", ) ->
# cuota_inicial: Cuota inicial a pagar numero_amortizaciones: Número de cuotas modalidad_pago: SEMANAL, QUINCENAL, MENSUAL,
# BIMENSUAL """ errores = [] advertencias = [] try: # Convertir a Decimal si es necesario if not"""
# isinstance(total_financiamiento, Decimal): total_financiamiento = Decimal(str(total_financiamiento)) if not
# isinstance(cuota_inicial, Decimal): cuota_inicial = Decimal(str(cuota_inicial)) # 1. Cuota inicial no puede ser mayor al
# total if cuota_inicial > total_financiamiento: errores.append
# financiamiento" ) # 2. Validar cuota inicial mínima (10%) cuota_minima = 
# ValidadorCoherenciaFinanciera.CUOTA_INICIAL_MINIMA_PORCENTAJE ) / Decimal("100") ) if cuota_inicial < cuota_minima:
# f"{ValidadorCoherenciaFinanciera.CUOTA_INICIAL_MINIMA_PORCENTAJE}% " f"" f"del total (mínimo: ${cuota_minima:.2f})" ) # 3.
# Advertencia si cuota inicial es muy alta cuota_maxima_recomendada = 
# ValidadorCoherenciaFinanciera.CUOTA_INICIAL_MAXIMA_PORCENTAJE ) / Decimal("100") ) if cuota_inicial >
# cuota_maxima_recomendada: advertencias.append
# monto_financiado <= 0: errores.append("El monto a financiar debe ser mayor a cero") # 5. Validar número de amortizaciones
# advertencias.append( "Número de amortizaciones muy alto para modalidad semanal" ) elif 
# "Número de amortizaciones muy alto para modalidad mensual" ) # Calcular cuota aproximada if monto_financiado > 0 and
# numero_amortizaciones > 0: cuota_aproximada = monto_financiado / Decimal( str(numero_amortizaciones) ) else:
# cuota_aproximada = Decimal("0") # Resultado if errores: return 
# 100)) if total_financiamiento > 0 else 0 ), "cuota_aproximada": float(cuota_aproximada), }, } else: return 
# "cuota_aproximada": float(cuota_aproximada), }, } except Exception as e: logger.error
# validar_chasis_unico( chasis: str, db_session, cliente_id: Optional[int] = None ) -> Dict[str, Any]: """ Validar que el
# cliente_id: ID del cliente (para excluir en updates) """ try: if not chasis or not chasis.strip(): return """
# # Chasis es opcional "mensaje": "Chasis no proporcionado (opcional)", } # Limpiar y normalizar chasis_limpio =
# Excluir el cliente actual si es un update if cliente_id: query = query.filter(Cliente.id != cliente_id) existe =
# query.first() if existe: return 
# f"{existe.nombre_completo} (ID: {existe.id})" ), "chasis": chasis_limpio, "cliente_existente": 
# existe.nombre_completo, "cedula": existe.cedula, }, } return 
# de chasis único", } except Exception as e: logger.error(f"Error validando chasis: {e}") return 
# f"Error al validar chasis: {str(e)}", } @staticmethod def validar_email_unico
# Optional[int] = None ) -> Dict[str, Any]: """ Validar que el email sea único (opcional, puede haber clientes sin email) """
# try: if not email or not email.strip(): return 
# "error": ( f"El email ya está registrado para el " f"cliente {existe.nombre_completo}" ), "email": email_limpio,
# "cliente_existente": { "id": existe.id, "nombre": existe.nombre_completo, "cedula": existe.cedula, }, } return 
# True, "email": email_limpio, "mensaje": "Email único", } except Exception as e: logger.error(f"Error validando email: {e}")
# return { "valido": False, "error": f"Error al validar email: {str(e)}", }

""""""