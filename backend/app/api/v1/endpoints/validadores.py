# backend/app/api/v1/endpoints/validadores.py"""Endpoints de Validadores y Corrección de DatosSistema para validar y corregir
# formatos incorrectos"""\nimport logging\nfrom datetime \nimport datetime\nfrom decimal \nimport Decimal\nfrom typing
# \nimport Any, Dict, List, Optional\nfrom fastapi \nimport APIRouter, BackgroundTasks, Depends, HTTPException, Query\nfrom
# pydantic \nimport BaseModel, Field\nfrom sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_current_user,
# get_db\nfrom app.models.auditoria \nimport Auditoria, TipoAccion\nfrom app.models.cliente \nimport Cliente\nfrom
# app.models.pago \nimport Pago\nfrom app.models.user \nimport User\nfrom app.services.validators_service \nimport (
# AutoFormateador, ServicioCorreccionDatos, ValidadorAmortizaciones, ValidadorCedula, ValidadorEmail, ValidadorFecha,
# ValidadorMonto, ValidadorTelefono,)logger = logging.getLogger(__name__)router = APIRouter()#
# ============================================# SCHEMAS PARA VALIDADORES# ============================================\nclass
# ValidacionCampo(BaseModel):\n """Schema para validación de campo individual""" campo:\n str = Field(...,
# description="Nombre del campo a validar") valor:\n str = Field(..., description="Valor a validar") pais:\n str = Field(
# "VENEZUELA", description="País para validaciones específicas" ) contexto:\n Optional[Dict[str, Any]] = Field( None,
# description="Contexto adicional para validación" )\nclass CorreccionDatos(BaseModel):\n """Schema para corrección de datos
# de cliente""" cliente_id:\n int = Field(..., description="ID del cliente") correcciones:\n Dict[str, str] = Field( ...,
# description="Campos a corregir con nuevos valores" ) pais:\n str = Field("VENEZUELA", description="País para validaciones")
# recalcular_amortizacion:\n bool = Field( True, description="Recalcular amortización si cambia fecha" )#
# ============================================# VALIDACIÓN EN TIEMPO REAL#
# ============================================@router.get("/test-cedula/{cedula}")\ndef test_cedula_simple(cedula:\n str):\n
# """Endpoint simple para probar validación de cédula sin autenticación""" try:\n resultado =
# ValidadorCedula.validar_y_formatear_cedula( cedula, "VENEZUELA" ) return { "cedula_test":\n cedula, "resultado":\n
# resultado, "reglas":\n { "prefijos_validos":\n ["V", "E", "J"], "longitud_digitos":\n "7-10 dígitos", "patron":\n
# "^[VEJ]\\d{7,10}$", "ejemplos_validos":\n [ "V1234567", "E12345678", "J123456789", "V1234567890", ], }, } except Exception
# as e:\n return {"error":\n str(e), "cedula_test":\n cedula}@router.get("/test-simple")\ndef test_simple():\n """Endpoint de
# prueba muy simple para verificar que el servidor responde""" return { "mensaje":\n "Servidor funcionando correctamente",
# "timestamp":\n datetime.now().isoformat(), "status":\n "ok", }@router.post("/test-cedula-post")\ndef
# test_cedula_post(cedula:\n str = "E12345678"):\n """Endpoint POST simple para probar validación sin autenticación""" try:\n
# resultado = ValidadorCedula.validar_y_formatear_cedula( cedula, "VENEZUELA" ) return { "cedula_test":\n cedula,
# "resultado":\n resultado, "deberia_ser_valido":\n True, "explicacion":\n "E12345678:\n E (válido) + 8 dígitos (válido) \ =
# VÁLIDO", } except Exception as e:\n return {"error":\n str(e), "cedula_test":\n
# cedula}@router.post("/test-cedula-custom")\ndef test_cedula_custom(cedula:\n str):\n """Endpoint POST para probar cualquier
# cédula sin autenticación""" try:\n resultado = ValidadorCedula.validar_y_formatear_cedula( cedula, "VENEZUELA" ) return {
# "cedula_test":\n cedula, "resultado":\n resultado, "reglas":\n { "prefijos_validos":\n ["V", "E", "J"],
# "longitud_digitos":\n "7-10 dígitos", "patron":\n "^[VEJ]\\d{7,10}$", "ejemplos_validos":\n [ "V1234567", "E12345678",
# "J123456789", "V1234567890", ], }, } except Exception as e:\n return {"error":\n str(e), "cedula_test":\n cedula}\ndef
# _validar_campo_telefono(valor:\n str, pais:\n str) -> Dict[str, Any]:\n """Validar campo de teléfono""" return
# ValidadorTelefono.validar_y_formatear_telefono(valor, pais)\ndef _validar_campo_cedula(valor:\n str, pais:\n str) ->
# Dict[str, Any]:\n """Validar campo de cédula""" return ValidadorCedula.validar_y_formatear_cedula(valor, pais)\ndef
# _validar_campo_email(valor:\n str) -> Dict[str, Any]:\n """Validar campo de email""" return
# ValidadorEmail.validar_email(valor)\ndef _validar_campo_fecha_entrega(valor:\n str) -> Dict[str, Any]:\n """Validar campo
# de fecha de entrega""" return ValidadorFecha.validar_fecha_entrega(valor)\ndef _validar_campo_fecha_pago(valor:\n str) ->
# Dict[str, Any]:\n """Validar campo de fecha de pago""" return ValidadorFecha.validar_fecha_pago(valor)\ndef
# _validar_campo_monto( valor:\n str, campo:\n str, contexto:\n Optional[Dict[str, Any]]) -> Dict[str, Any]:\n """Validar
# campo de monto""" saldo_maximo = None if contexto and "saldo_pendiente" in contexto:\n saldo_maximo =
# Decimal(str(contexto["saldo_pendiente"])) return ValidadorMonto.validar_y_formatear_monto( valor, campo.upper(),
# saldo_maximo )\ndef _validar_campo_amortizaciones(valor:\n str) -> Dict[str, Any]:\n """Validar campo de amortizaciones"""
# return ValidadorAmortizaciones.validar_amortizaciones(valor)\ndef _crear_error_campo_no_soportado(campo:\n str, valor:\n
# str) -> Dict[str, Any]:\n """Crear error para campo no soportado""" return { "valido":\n False, "error":\n f"Campo
# '{campo}' no soporta validación automática", "valor_original":\n valor, }@router.post("/validar-campo")\ndef
# validar_campo_tiempo_real(validacion:\n ValidacionCampo):\n """ 🔍 Validar campo individual en tiempo real (VERSIÓN
# REFACTORIZADA) Ejemplos de uso:\n • Teléfono:\n "4241234567" → "+58 424 1234567" • Cédula:\n "12345678" → "V12345678" •
# Email:\n "USUARIO@GMAIL.COM" → "usuario@gmail.com" • Fecha:\n "15/03/2024" → Validación + formato ISO • Monto:\n "15000" →
# "$15,000.00" """ try:\n campo = validacion.campo.lower() valor = validacion.valor pais = validacion.pais # Validar según el
# tipo de campo if campo == "telefono":\n resultado = _validar_campo_telefono(valor, pais) elif campo == "cedula":\n
# resultado = _validar_campo_cedula(valor, pais) elif campo == "email":\n resultado = _validar_campo_email(valor) elif campo
# == "fecha_entrega":\n resultado = _validar_campo_fecha_entrega(valor) elif campo == "fecha_pago":\n resultado =
# _validar_campo_fecha_pago(valor) elif campo in [ "total_financiamiento", "monto_pagado", "cuota_inicial", ]:\n resultado =
# _validar_campo_monto(valor, campo, validacion.contexto) elif campo == "amortizaciones":\n resultado =
# _validar_campo_amortizaciones(valor) else:\n return _crear_error_campo_no_soportado(campo, valor) return { "campo":\n
# validacion.campo, "validacion":\n resultado, "timestamp":\n datetime.now().isoformat(), "recomendaciones":\n
# _generar_recomendaciones_campo( campo, resultado ), } except Exception as e:\n raise HTTPException( status_code=500,
# detail=f"Error validando campo:\n {str(e)}" )@router.post("/formatear-tiempo-real")\ndef formatear_mientras_escribe(
# campo:\n str, valor:\n str, pais:\n str = "VENEZUELA", current_user:\n User = Depends(get_current_user),):\n """ ✨
# Auto-formatear valor mientras el usuario escribe (para frontend) Uso en frontend:\n - onKeyUp/onChange del input - Formateo
# instantáneo sin validación completa - Para mejorar UX mientras el usuario escribe """ try:\n resultado =
# AutoFormateador.formatear_mientras_escribe( campo, valor, pais ) return { "campo":\n campo, "valor_original":\n valor,
# "resultado_formateo":\n resultado, "timestamp":\n datetime.now().isoformat(), } except Exception as e:\n raise
# HTTPException( status_code=500, detail=f"Error formateando:\n {str(e)}", )# ============================================#
# CORRECCIÓN DE DATOS# ============================================\ndef _aplicar_correccion_campo( cliente:\n Cliente,
# campo:\n str, nuevo_valor:\n str) -> dict:\n """Aplicar corrección a un campo específico del cliente""" valor_anterior =
# None if campo == "telefono":\n valor_anterior = cliente.telefono cliente.telefono = nuevo_valor elif campo == "cedula":\n
# valor_anterior = cliente.cedula cliente.cedula = nuevo_valor elif campo == "email":\n valor_anterior = cliente.email
# cliente.email = nuevo_valor elif campo == "fecha_entrega":\n valor_anterior = cliente.fecha_entrega cliente.fecha_entrega =
# datetime.strptime( nuevo_valor, "%d/%m/%Y" ).date() elif campo == "total_financiamiento":\n valor_anterior =
# cliente.total_financiamiento cliente.total_financiamiento = Decimal(nuevo_valor) elif campo == "cuota_inicial":\n
# valor_anterior = cliente.cuota_inicial cliente.cuota_inicial = Decimal(nuevo_valor) elif campo == "amortizaciones":\n
# valor_anterior = cliente.numero_amortizaciones cliente.numero_amortizaciones = int(nuevo_valor) return { "campo":\n campo,
# "valor_anterior":\n valor_anterior, "valor_nuevo":\n nuevo_valor, }\ndef _procesar_correcciones_cliente( cliente:\n
# Cliente, resultado_correccion:\n dict) -> list[dict]:\n """Procesar y aplicar correcciones al cliente""" cambios_aplicados
# = [] for correccion in resultado_correccion["correcciones_aplicadas"]:\n if correccion["cambio_realizado"]:\n campo =
# correccion["campo"] nuevo_valor = correccion["valor_nuevo"] cambio = _aplicar_correccion_campo(cliente, campo, nuevo_valor)
# cambios_aplicados.append(cambio) return cambios_aplicados\ndef _registrar_auditoria_correccion( cliente_id:\n int,
# cambios_aplicados:\n list[dict], current_user:\n User, db:\n Session,) -> None:\n """Registrar auditoría de corrección"""
# auditoria = Auditoria.registrar( usuario_id=current_user.id, accion=TipoAccion.ACTUALIZACION, entidad="cliente",
# entidad_id=cliente_id, detalles=f"Corrección de datos:\n {len(cambios_aplicados)} campos \ actualizados", )
# db.add(auditoria) db.commit()\ndef _generar_respuesta_correccion( cliente_id:\n int, cliente:\n Cliente,
# resultado_correccion:\n dict, cambios_aplicados:\n list[dict], recalcular_amortizacion:\n bool, current_user:\n User,) ->
# dict:\n """Generar respuesta de corrección""" mensaje_recalculo = None if (
# resultado_correccion["requiere_recalculo_amortizacion"] and recalcular_amortizacion ):\n mensaje_recalculo = "⚠️ Se
# requiere recalcular la tabla de amortización" return { "mensaje":\n "✅ Corrección de datos procesada exitosamente",
# "cliente":\n { "id":\n cliente_id, "nombre":\n cliente.nombre_completo, "cedula":\n cliente.cedula, },
# "resultado_correccion":\n resultado_correccion, "cambios_aplicados_bd":\n cambios_aplicados, "total_cambios":\n
# len(cambios_aplicados), "errores_encontrados":\n len( resultado_correccion["errores_encontrados"] ),
# "recalculo_amortizacion":\n { "requerido":\n resultado_correccion[ "requiere_recalculo_amortizacion" ], "aplicado":\n (
# recalcular_amortizacion and resultado_correccion["requiere_recalculo_amortizacion"] ), "mensaje":\n mensaje_recalculo, },
# "fecha_correccion":\n datetime.now().isoformat(), "corregido_por":\n f"{current_user.nombre}
# {current_user.apellido}".strip(), }@router.post("/corregir-cliente/{cliente_id}")\ndef corregir_datos_cliente(
# cliente_id:\n int, correcciones:\n Dict[str, str], pais:\n str = Query("VENEZUELA", description="País para validaciones"),
# recalcular_amortizacion:\n bool = Query( True, description="Recalcular amortización si cambia fecha" ), db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 🔧 Corregir datos incorrectos de un cliente
# específico Ejemplo de uso:\n { "telefono":\n "+58 424 1234567", "cedula":\n "V12345678", "email":\n "cliente@email.com",
# "fecha_entrega":\n "15/03/2024" } """ try:\n # Verificar que el cliente existe cliente =
# db.query(Cliente).filter(Cliente.id == cliente_id).first() if not cliente:\n raise HTTPException( status_code=404,
# detail="Cliente no encontrado" ) # Procesar correcciones resultado_correccion =
# ServicioCorreccionDatos.corregir_datos_cliente( cliente_id, correcciones, pais ) if
# resultado_correccion.get("error_general"):\n raise HTTPException( status_code=400,
# detail=resultado_correccion["error_general"] ) # Aplicar correcciones válidas a la base de datos cambios_aplicados =
# _procesar_correcciones_cliente( cliente, resultado_correccion ) # Guardar cambios si hay correcciones válidas if
# cambios_aplicados:\n db.commit() _registrar_auditoria_correccion( cliente_id, cambios_aplicados, current_user, db ) #
# Generar respuesta return _generar_respuesta_correccion( cliente_id, cliente, resultado_correccion, cambios_aplicados,
# recalcular_amortizacion, current_user, ) except HTTPException:\n raise except Exception as e:\n db.rollback() raise
# HTTPException( status_code=500, detail=f"Error corrigiendo datos:\n {str(e)}", )\ndef _validar_y_corregir_monto_pago(
# pago:\n Pago, monto_pagado:\n str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:\n """Validar y corregir monto
# pagado""" correcciones = [] errores = [] validacion_monto = ValidadorMonto.validar_y_formatear_monto( monto_pagado,
# "MONTO_PAGO" ) if validacion_monto["valido"]:\n pago.monto_pagado = validacion_monto["valor_decimal"] correcciones.append(
# { "campo":\n "monto_pagado", "valor_anterior":\n str(pago.monto_pagado), "valor_nuevo":\n
# str(validacion_monto["valor_decimal"]), } ) else:\n errores.append( {"campo":\n "monto_pagado", "error":\n
# validacion_monto["error"]} ) return correcciones, errores\ndef _validar_y_corregir_fecha_pago( pago:\n Pago, fecha_pago:\n
# str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:\n """Validar y corregir fecha de pago""" correcciones = []
# errores = [] validacion_fecha = ValidadorFecha.validar_fecha_pago(fecha_pago) if validacion_fecha["valido"]:\n
# fecha_parseada = datetime.strptime( validacion_fecha["fecha_iso"], "%Y-%m-%d" ).date() pago.fecha_pago = fecha_parseada
# correcciones.append( { "campo":\n "fecha_pago", "valor_anterior":\n str(pago.fecha_pago), "valor_nuevo":\n
# str(fecha_parseada), } ) else:\n errores.append( {"campo":\n "fecha_pago", "error":\n validacion_fecha["error"]} ) return
# correcciones, errores\ndef _validar_y_corregir_numero_operacion( pago:\n Pago, numero_operacion:\n str) -> List[Dict[str,
# Any]]:\n """Validar y corregir número de operación""" correcciones = [] if numero_operacion.upper() != "ERROR" and
# numero_operacion.strip():\n pago.numero_operacion = numero_operacion.strip() correcciones.append( { "campo":\n
# "numero_operacion", "valor_anterior":\n pago.numero_operacion, "valor_nuevo":\n numero_operacion.strip(), } ) return
# correcciones\ndef _limpiar_observaciones_error(pago:\n Pago, current_user:\n User) -> None:\n """Limpiar observaciones de
# error""" if pago.observaciones and "REQUIERE_VALIDACIÓN" in pago.observaciones:\n usuario_nombre = (
# f"{current_user.nombre} {current_user.apellido}".strip() ) pago.observaciones = f"CORREGIDO -
# {datetime.now().strftime('%d/%m/%Y')} por {usuario_nombre}"@router.post("/corregir-pago/{pago_id}")\ndef
# corregir_datos_pago( pago_id:\n int, monto_pagado:\n Optional[str] = None, fecha_pago:\n Optional[str] = None,
# numero_operacion:\n Optional[str] = None, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 💰 Corregir datos incorrectos de un pago específico (VERSIÓN REFACTORIZADA) Ejemplo:\n
# Pago con "MONTO PAGADO = ERROR" """ try:\n # Verificar que el pago existe pago = db.query(Pago).filter(Pago.id ==
# pago_id).first() if not pago:\n raise HTTPException(status_code=404, detail="Pago no encontrado") correcciones_aplicadas =
# [] errores_validacion = [] # Corregir monto pagado if monto_pagado is not None:\n correcciones, errores =
# _validar_y_corregir_monto_pago( pago, monto_pagado ) correcciones_aplicadas.extend(correcciones)
# errores_validacion.extend(errores) # Corregir fecha de pago if fecha_pago is not None:\n correcciones, errores =
# _validar_y_corregir_fecha_pago( pago, fecha_pago ) correcciones_aplicadas.extend(correcciones)
# errores_validacion.extend(errores) # Corregir número de operación if numero_operacion is not None:\n correcciones =
# _validar_y_corregir_numero_operacion( pago, numero_operacion ) correcciones_aplicadas.extend(correcciones) # Guardar
# cambios si hay correcciones válidas if correcciones_aplicadas:\n # Limpiar observaciones de error
# _limpiar_observaciones_error(pago, current_user) db.commit() # Registrar en auditoría _registrar_auditoria_correccion(
# pago_id, correcciones_aplicadas, current_user, db ) db.commit() return { "mensaje":\n "✅ Corrección de pago procesada
# exitosamente", "pago":\n { "id":\n pago_id, "cliente":\n ( pago.prestamo.cliente.nombre_completo if pago.prestamo else
# "N/A" ), "cuota":\n pago.numero_cuota, }, "correcciones_aplicadas":\n correcciones_aplicadas, "errores_validacion":\n
# errores_validacion, "total_correcciones":\n len(correcciones_aplicadas), "fecha_correccion":\n datetime.now().isoformat(),
# "corregido_por":\n f"{current_user.nombre} {current_user.apellido}".strip(), } except HTTPException:\n raise except
# Exception as e:\n db.rollback() raise HTTPException( status_code=500, detail=f"Error corrigiendo pago:\n {str(e)}", )#
# ============================================# DETECCIÓN MASIVA DE ERRORES#
# ============================================@router.get("/detectar-errores-masivo")\ndef detectar_errores_masivo( limite:\n
# int = Query( 100, ge=1, le=1000, description="Límite de registros a analizar" ), tipo_analisis:\n str = Query( "CLIENTES",
# description="CLIENTES, PAGOS, AMBOS" ), pais:\n str = Query("VENEZUELA", description="País para validaciones"), db:\n
# Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 🔍 Detectar datos incorrectos
# masivamente en la base de datos Detecta:\n • Teléfonos mal formateados (sin +58) • Cédulas sin letra (V/E) • Emails
# inválidos • Fechas = "ERROR" • Montos = "ERROR" """ # Solo administrador general puede ejecutar análisis masivo if not
# current_user.is_admin:\n raise HTTPException( status_code=403, detail="Sin permisos para análisis masivo" ) try:\n
# resultado = ServicioCorreccionDatos.detectar_datos_incorrectos_masivo( db, limite ) return { "analisis_masivo":\n
# resultado, "parametros":\n { "limite":\n limite, "tipo_analisis":\n tipo_analisis, "pais":\n pais, "ejecutado_por":\n
# f"{current_user.nombre} {current_user.apellido}".strip(), }, "acciones_sugeridas":\n [ "Usar herramienta de corrección
# masiva para los casos detectados", "Configurar validadores en formularios del frontend", "Capacitar usuarios en formatos
# correctos", "Implementar auto-formateo en tiempo real", ], } except Exception as e:\n raise HTTPException( status_code=500,
# detail=f"Error en análisis masivo:\n {str(e)}", )@router.post("/corregir-masivo")\ndef corregir_datos_masivo(
# correcciones_masivas:\n List[CorreccionDatos], background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ 🔧 Corrección masiva de datos incorrectos """ if not
# current_user.is_admin:\n raise HTTPException( status_code=403, detail="Sin permisos para corrección masiva" ) try:\n #
# Ejecutar correcciones en background background_tasks.add_task( _procesar_correcciones_masivas, correcciones_masivas,
# current_user.id, db, ) return { "mensaje":\n "✅ Corrección masiva iniciada en background", "total_clientes":\n
# len(correcciones_masivas), "estimacion_tiempo":\n f"{len(correcciones_masivas) * 2} segundos", "ejecutado_por":\n
# f"{current_user.nombre} {current_user.apellido}".strip(), "timestamp":\n datetime.now().isoformat(), "seguimiento":\n "GET
# /api/v1/validadores/estado-correccion-masiva", } except Exception as e:\n raise HTTPException( status_code=500,
# detail=f"Error iniciando corrección masiva:\n {str(e)}", )# ============================================# EJEMPLOS DE
# CORRECCIÓN# ============================================@router.get("/ejemplos-correccion")\ndef
# obtener_ejemplos_correccion( pais:\n str = Query("VENEZUELA", description="País para ejemplos"), current_user:\n User =
# Depends(get_current_user),):\n """ 📋 Obtener ejemplos de corrección de formatos incorrectos """ try:\n ejemplos = {
# "telefono":\n { "titulo":\n "📱 TELÉFONO MAL FORMATEADO", "ejemplo_incorrecto":\n "4241234567", "problema":\n "🟡 Sin código
# de país (+58)", "ejemplo_correccion":\n "+58 424 1234567", "proceso":\n "Sistema auto-formatea al guardar",
# "validaciones":\n [ "✅ Formato correcto", "✅ Operadora válida", "✅ Longitud correcta", ], }, "cedula":\n { "titulo":\n "📝
# CÉDULA SIN LETRA", "ejemplo_incorrecto":\n "12345678", "problema":\n "🟡 Sin prefijo V/E", "ejemplo_correccion":\n
# "V12345678", "proceso":\n "Admin edita y sistema valida", "validaciones":\n [ "✅ Prefijo válido (V/E/J/G)", "✅ Longitud
# correcta (7-8 dígitos)", "✅ Solo números después del prefijo", ], }, "fecha":\n { "titulo":\n "📅 FECHA EN FORMATO
# INCORRECTO", "ejemplo_incorrecto":\n "ERROR", "problema":\n "🔴 Valor inválido", "ejemplo_correccion":\n "15/03/2024",
# "proceso":\n "Admin selecciona en calendario", "validaciones":\n [ "✅ No es fecha futura", "✅ Formato correcto", "⚠️ Puede
# requerir recálculo de amortización", ], "accion_adicional":\n "Sistema pregunta si recalcular tabla de amortización", },
# "monto":\n { "titulo":\n "💰 MONTO PAGADO = ERROR", "ejemplo_incorrecto":\n "ERROR", "problema":\n "🔴 Valor inválido",
# "ejemplo_correccion":\n "15000.00", "proceso":\n "Admin/Cobranzas ingresa monto correcto", "validaciones":\n [ "✅ Es número
# positivo", "✅ Tiene máximo 2 decimales", "✅ No excede saldo pendiente", ], }, } return { "titulo":\n "📋 EJEMPLOS DE
# CORRECCIÓN DE FORMATOS INCORRECTOS", "pais_configurado":\n pais, "ejemplos":\n ejemplos, "herramientas_disponibles":\n {
# "validacion_tiempo_real":\n "POST /api/v1/validadores/va \ lidar-campo", "formateo_automatico":\n "POST
# /api/v1/validadores/forma \ tear-tiempo-real", "correccion_individual":\n "POST /api/v1/validadores/corregir-cliente/{id}",
# "deteccion_masiva":\n "GET /api/v1/validadores/detectar- \ errores-masivo", }, "integracion_frontend":\n {
# "validacion_onchange":\n "Usar endpoint validar-campo en \ onChange", "formateo_onkeyup":\n "Usar endpoint
# formatear-tiempo-real en onKeyUp", "calendario_fechas":\n "Usar datepicker para fechas críticas", "input_numerico":\n "Usar
# input type='number' para montos", }, } except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error
# obteniendo ejemplos:\n {str(e)}", )# ============================================# ENDPOINTS DE PRUEBA#
# ============================================@router.get("/test")\ndef test_validadores():\n """ 🧪 Endpoint de prueba simple
# """ return {"message":\n "Validadores endpoint funcionando", "status":\n "ok"}@router.get("/")@router.get("/info")\ndef
# obtener_validadores_info():\n """ 📋 Información general de validadores disponibles """ return {
# "validadores_disponibles":\n [ "ValidadorTelefono", "ValidadorCedula", "ValidadorFecha", "ValidadorMonto",
# "ValidadorAmortizaciones", "ValidadorEmail", "ValidadorEdad", "ValidadorCoherenciaFinanciera", "ValidadorDuplicados", ],
# "endpoints":\n { "validar_campo":\n "POST /api/v1/validadores/validar-campo", "formatear_tiempo_real":\n "POST
# /api/v1/validadores/formate \ ar-tiempo-real", "configuracion":\n "GET /api/v1/validadores/configuracion",
# "ejemplos_correccion":\n "GET /api/v1/validadores/ejemplos-correccion", "detectar_errores_masivo":\n "GET
# /api/v1/validadores/detectar-errores-masivo", "test_cedula":\n "GET /api/v1/validadores/test-cedula/{cedula}",
# "test_simple":\n "GET /api/v1/validadores/test-simple", "ping":\n "GET /api/v1/validadores/ping", }, "status":\n "active",
# "version":\n "1.0.0", }@router.get("/ping")\ndef ping_validadores():\n """ 🏓 Endpoint de prueba para verificar conectividad
# """ return { "status":\n "success", "message":\n "Endpoint de validadores funcionando", "timestamp":\n
# "2025-10-19T12:\n00:\n00Z", "version":\n "1.0.0", } # ============================================ # CONFIGURACIÓN DE
# VALIDADORES # ============================================# ============================================# FUNCIONES
# AUXILIARES# ============================================async \ndef _procesar_correcciones_masivas( correcciones:\n
# List[CorreccionDatos], user_id:\n int, db_session:\n Session):\n """Procesar correcciones masivas en background""" try:\n
# \nfrom app.db.session \nimport SessionLocal db = SessionLocal() exitosas = 0 fallidas = 0 for correccion in correcciones:\n
# try:\n resultado = ServicioCorreccionDatos.corregir_datos_cliente( correccion.cliente_id, correccion.correcciones,
# correccion.pais, ) if resultado.get("cambios_realizados"):\n exitosas += 1 else:\n fallidas += 1 except Exception as e:\n
# logger.error( f"Error corrigiendo cliente {correccion.cliente_id}:\n {e}" ) fallidas += 1 logger.info( f"📊 Corrección
# masiva completada:\n {exitosas} " f"exitosas, {fallidas} fallidas" ) db.close() except Exception as e:\n
# logger.error(f"Error en corrección masiva:\n {e}")\ndef _generar_recomendaciones_campo( campo:\n str,
# resultado_validacion:\n Dict) -> List[str]:\n """Generar recomendaciones específicas por campo""" recomendaciones = [] if
# not resultado_validacion.get("valido"):\n if campo == "telefono":\n recomendaciones.append( "📱 Use formato internacional:\n
# +58 424 1234567" ) recomendaciones.append("🔍 Verifique que la operadora sea válida") elif campo == "cedula":\n
# recomendaciones.append( "📝 Agregue prefijo V para venezolanos, E para extranjeros" ) recomendaciones.append( "🔢 Verifique
# que tenga 7-8 dígitos después de la letra" ) elif campo == "email":\n recomendaciones.append("📧 Verifique formato:\n
# usuario@dominio.com") recomendaciones.append("🚫 Evite dominios de email temporal") elif "fecha" in campo:\n
# recomendaciones.append("📅 Use calendario para seleccionar fecha") recomendaciones.append( "⏰ Verifique reglas de negocio
# (no futuras)" ) elif "monto" in campo:\n recomendaciones.append("💰 Use solo números y punto decimal")
# recomendaciones.append("📊 Verifique límites permitidos") return recomendaciones#
# ============================================# ENDPOINT DE VERIFICACIÓN#
# ============================================@router.get("/verificacion-validadores")\ndef verificar_sistema_validadores(
# current_user:\n User = Depends(get_current_user),):\n """ 🔍 Verificación completa del sistema de validadores """ return {
# "titulo":\n "🔍 SISTEMA DE VALIDADORES Y CORRECCIÓN DE DATOS", "fecha_verificacion":\n datetime.now().isoformat(),
# "validadores_implementados":\n { "telefono":\n { "estado":\n "✅ IMPLEMENTADO", "paises":\n ["Venezuela", "República
# Dominicana", "Colombia"], "auto_formateo":\n True, "ejemplo":\n "4241234567 → +58 424 1234567", }, "cedula":\n {
# "estado":\n "✅ IMPLEMENTADO", "paises":\n ["Venezuela", "República Dominicana", "Colombia"], "auto_formateo":\n True,
# "ejemplo":\n "12345678 → V12345678", "venezuela_prefijos":\n ["V", "E", "J"], "venezuela_longitud":\n "7-10 dígitos", },
# "email":\n { "estado":\n "✅ IMPLEMENTADO", "validacion":\n "RFC 5322", "dominios_bloqueados":\n True, "ejemplo":\n
# "USUARIO@GMAIL.COM → usuario@gmail.com", }, "fechas":\n { "estado":\n "✅ IMPLEMENTADO", "reglas_negocio":\n True,
# "formatos_multiples":\n True, "ejemplo":\n "ERROR → Calendario para selección", }, "montos":\n { "estado":\n "✅
# IMPLEMENTADO", "limites_por_tipo":\n True, "auto_formateo":\n True, "ejemplo":\n "15000 → $15,000.00", },
# "amortizaciones":\n { "estado":\n "✅ IMPLEMENTADO", "rango":\n "1-84 meses", "validacion_entero":\n True, "ejemplo":\n
# "60.5 → 60 meses", }, }, "funcionalidades_especiales":\n { "validacion_tiempo_real":\n "✅ Para uso en frontend",
# "auto_formateo_escritura":\n "✅ Mientras el usuario escribe", "deteccion_masiva":\n "✅ Análisis de toda la BD",
# "correccion_masiva":\n "✅ Corrección en lotes", "reglas_negocio":\n "✅ Validaciones específicas del dominio",
# "recalculo_amortizacion":\n "✅ Al cambiar fecha de entrega", }, "endpoints_principales":\n { "validar_campo":\n "POST
# /api/v1/validadores/validar-campo", "formatear_tiempo_real":\n "POST /api/v1/validadores/formatear-tiempo-real",
# "corregir_cliente":\n "POST /api/v1/validadores/corregir-cliente/{id}", "detectar_errores":\n "GET
# /api/v1/validadores/detectar-errores-masivo", "ejemplos":\n "GET /api/v1/validadores/ejemplos-correccion", },
# "integracion_frontend":\n { "validacion_onchange":\n "Validar cuando cambia el valor", "formateo_onkeyup":\n "Formatear
# mientras escribe", "mostrar_errores":\n "Mostrar errores en tiempo real", "sugerencias_correccion":\n "Mostrar cómo
# corregir", "calendario_fechas":\n "Usar datepicker para fechas", "input_numerico":\n "Input type='number' para montos", },
# "beneficios":\n [ "🔍 Detección automática de datos incorrectos", "✨ Auto-formateo mejora experiencia de usuario", "🔧
# Corrección masiva ahorra tiempo", "📊 Análisis de calidad de datos", "⚡ Validación en tiempo real previene errores", "🎯
# Reglas de negocio específicas del dominio", ], }@router.get("/configuracion-validadores")async \ndef
# obtener_configuracion_validadores():\n """ 🔧 Obtener configuración actualizada de validadores para el frontend """ return {
# "cedula_venezuela":\n { "descripcion":\n ( "Cédula venezolana:\n V/E/J + exactamente entre 7 y 10 dígitos, sin caracteres
# especiales" ), "requisitos":\n { "debe_empezar_por":\n "V, E o J", "longitud_digitos":\n "Entre 7 y 10 dígitos",
# "sin_caracteres_especiales":\n "Solo letra inicial + números", "ejemplos_validos":\n [ "V1234567", "E12345678",
# "J123456789", "V1234567890", ], }, "patron_regex":\n r"^[VEJ]\d{7,10}$", "formato_display":\n "V12345678", "tipos":\n
# {"V":\n "Venezolano", "E":\n "Extranjero", "J":\n "Jurídico"}, }, "telefono_venezuela":\n { "descripcion":\n ( "Teléfono
# venezolano:\n +58 seguido de 10 dígitos (primer dígito no puede ser 0)" ), "requisitos":\n { "debe_empezar_por":\n "+58",
# "longitud_total":\n 10, "primer_digito":\n "No puede ser 0", "digitos_validos":\n "0-9", }, "patron_regex":\n
# r"^\+58[1-9][0-9]{9}$", "formato_display":\n "+58 XXXXXXXXXX", }, "email":\n { "descripcion":\n "Email válido con
# normalización automática a minúsculas", "requisitos":\n { "formato":\n "usuario@dominio.com", "normalizacion":\n
# "Automática a minúsculas", "dominios_bloqueados":\n [ "tempmail.org", "10minutemail.com", "guerrillamail.com", ], },
# "patron_regex":\n r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", }, "fecha":\n { "descripcion":\n "Fecha en formato
# DD/MM/YYYY", "requisitos":\n { "formato":\n "DD/MM/YYYY", "dia":\n "01-31", "mes":\n "01-12", "año":\n "1900-2100", },
# "patron_regex":\n r"^\d{2}/\d{2}/\d{4}$", }, "monto":\n { "descripcion":\n "Monto numérico positivo con máximo 2
# decimales", "requisitos":\n { "formato":\n "Número positivo", "decimales":\n "Máximo 2", "separador_miles":\n "Comas
# opcionales", "simbolo_moneda":\n "$ opcional", }, }, }
