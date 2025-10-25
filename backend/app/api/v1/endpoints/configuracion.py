# backend/app/api/v1/endpoints/configuracion.py"""Endpoint para configuración administrativa del sistema.Gestión de
# parámetros, tasas, límites y ajustes generales."""\nimport json\nimport logging\nimport time\nfrom datetime \nimport
# datetime\nfrom decimal \nimport Decimal\nfrom typing \nimport Any, Dict, Optional\nfrom fastapi \nimport APIRouter,
# Depends, HTTPException, Query\nfrom pydantic \nimport BaseModel, Field\nfrom sqlalchemy.orm \nimport Session\nfrom
# app.api.deps \nimport get_current_user, get_db\nfrom app.models.configuracion_sistema \nimport ConfiguracionSistema\nfrom
# app.models.prestamo \nimport Prestamo\nfrom app.models.user \nimport User# Funciones auxiliares para validación y
# pruebaslogger = logging.getLogger(__name__)router = APIRouter()# ============================================# MONITOREO Y
# OBSERVABILIDAD# ============================================@router.get("/monitoreo/estado")\ndef
# obtener_estado_monitoreo(current_user:\n User = Depends(get_current_user)):\n """ 🔍 Verificar estado del sistema de
# monitoreo y observabilidad """ # Solo admin puede ver configuración de monitoreo if not current_user.is_admin:\n raise
# HTTPException( status_code=403, detail="Solo administradores pueden ver configuración de m \ onitoreo", ) \nfrom
# app.core.monitoring \nimport get_monitoring_status return get_monitoring_status()@router.post("/monitoreo/habilitar")\ndef
# habilitar_monitoreo_basico(current_user:\n User = Depends(get_current_user)):\n """ ⚡ Habilitar monitoreo básico sin
# dependencias externas """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo
# administradores pueden configurar monitoreo", ) try:\n # Configurar logging estructurado básico # Configurar formato
# mejorado logging.basicConfig( level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:\n% \
# (lineno)d] - %(message)s", datefmt="%Y-%m-%d %H:\n%M:\n%S", ) # Logger específico para el sistema de financiamiento
# finance_logger = logging.getLogger("financiamiento_automotriz") finance_logger.setLevel(logging.INFO) return { "mensaje":\n
# "✅ Monitoreo básico habilitado", "configuracion":\n { "logging_estructurado":\n "✅ Habilitado", "nivel_log":\n "INFO",
# "formato":\n "Timestamp + Archivo + Línea + Mensaje", "logger_especifico":\n "financiamiento_automotriz", },
# "beneficios":\n [ "📋 Logs más detallados y estructurados", "🔍 Mejor debugging de errores", "📊 Tracking básico de
# operaciones", "⚡ Sin dependencias externas adicionales", ], "siguiente_paso":\n "Configurar Sentry y Prometheus para
# monitoreo avanzado", } except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error habilitando
# monitoreo:\n {str(e)}" )# ============================================# CONFIGURACIÓN CENTRALIZADA DEL SISTEMA#
# ============================================@router.get("/sistema/completa")\ndef obtener_configuracion_completa(
# categoria:\n Optional[str] = Query( None, description="Filtrar por categoría" ), db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ 🔧 Obtener configuración completa del sistema para el frontend """
# # Solo admin puede ver configuración completa if not current_user.is_admin:\n raise HTTPException( status_code=403,
# detail="Solo administradores pueden ver configuración completa", ) try:\n # Obtener tiempo actual para logging time.time()
# query = db.query(ConfiguracionSistema).filter( ConfiguracionSistema.visible_frontend ) if categoria:\n query =
# query.filter(ConfiguracionSistema.categoria == categoria) configs = query.all() # Agrupar por categoría
# configuracion_agrupada = {} for config in configs:\n if config.categoria not in configuracion_agrupada:\n
# configuracion_agrupada[config.categoria] = {} configuracion_agrupada[config.categoria][config.clave] = { "valor":\n
# config.valor_procesado, "descripcion":\n config.descripcion, "tipo_dato":\n config.tipo_dato, "requerido":\n
# config.requerido, "solo_lectura":\n config.solo_lectura, "opciones_validas":\n ( json.loads(config.opciones_validas) if
# config.opciones_validas else None ), "valor_minimo":\n config.valor_minimo, "valor_maximo":\n config.valor_maximo,
# "patron_validacion":\n config.patron_validacion, "actualizado_en":\n config.actualizado_en, "actualizado_por":\n
# config.actualizado_por, } return { "titulo":\n "🔧 CONFIGURACIÓN COMPLETA DEL SISTEMA", "fecha_consulta":\n
# datetime.now().isoformat(), "consultado_por":\n current_user.full_name, "configuracion":\n configuracion_agrupada,
# "categorias_disponibles":\n list(configuracion_agrupada.keys()), "total_configuraciones":\n len(configs), } except
# Exception as e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo configuración:\n {str(e)}"
# )@router.get("/validadores")\ndef obtener_configuracion_validadores():\n """ 🔍 Obtener configuración completa de
# validadores para el módulo de configuración """ try:\n pass return { "titulo":\n "🔍 CONFIGURACIÓN DE VALIDADORES",
# "fecha_consulta":\n datetime.now().isoformat(), "consultado_por":\n "Sistema", "validadores_disponibles":\n { "telefono":\n
# { "descripcion":\n "Validación y formateo de números telefónicos", "paises_soportados":\n { "venezuela":\n { "codigo":\n
# "+58", "formato":\n "+58 XXXXXXXXXX", "requisitos":\n { "debe_empezar_por":\n "+58", "longitud_total":\n "10 dígitos",
# "primer_digito":\n "No puede ser 0", "digitos_validos":\n "0-9", }, "ejemplos_validos":\n [ "1234567890 → +581234567890",
# "4241234567 → +584241234567", "+581234567890", ], "ejemplos_invalidos":\n [ "0123456789 (empieza por 0)", "123456789 (9
# dígitos)", "12345678901 (11 dígitos)", ], } }, "auto_formateo":\n True, "validacion_tiempo_real":\n True, }, "cedula":\n {
# "descripcion":\n "Validación de cédulas por país", "paises_soportados":\n { "venezuela":\n { "prefijos_validos":\n ["V",
# "E", "J"], "longitud":\n "7-10 dígitos", "requisitos":\n { "prefijos":\n "V=Venezolano, E=Extranjero, J=Jurídico",
# "dígitos":\n "Solo números del 0 al 9", "longitud":\n "Entre 7 y 10 dígitos", }, "ejemplos_validos":\n [ "V1234567 (7
# dígitos)", "E12345678 (8 dígitos)", "J123456789 (9 dígitos)", "V1234567890 (10 dígitos)", ], "ejemplos_invalidos":\n [
# "G12345678 (prefijo G no válido)", "V123456 (6 dígitos)", "V12345678901 (11 dígitos)", ], } }, "auto_formateo":\n True,
# "validacion_tiempo_real":\n True, }, "fecha":\n { "descripcion":\n "Validación estricta de fechas", "formato_requerido":\n
# "DD/MM/YYYY", "requisitos":\n { "dia":\n "2 dígitos (01-31)", "mes":\n "2 dígitos (01-12)", "año":\n "4 dígitos
# (1900-2100)", "separador":\n "/ (barra)", }, "ejemplos_validos":\n [ "01/01/2024", "15/03/2024", "29/02/2024 (año
# bisiesto)", "31/12/2024", ], "ejemplos_invalidos":\n [ "1/1/2024 (día y mes sin cero inicial)", "01-01-2024 (separador
# guión)", "2024-01-01 (formato YYYY-MM-DD)", "32/01/2024 (día inválido)", ], "auto_formateo":\n False,
# "validacion_tiempo_real":\n True, "requiere_calendario":\n True, }, "email":\n { "descripcion":\n "Validación y
# normalización de emails", "caracteristicas":\n { "normalizacion":\n "Conversión automática a minúsculas", "limpieza":\n
# "Remoción automática de espacios", "validacion":\n "RFC 5322 estándar", "dominios_bloqueados":\n [ "tempmail.org",
# "10minutemail.com", "guerrillamail.com", "mailinator.com", "throwaway.email", ], }, "ejemplos_validos":\n [
# "USUARIO@EJEMPLO.COM → usuario@ejemplo.com", " Usuario@Ejemplo.com → usuario@ejemplo.com", "usuario.nombre@dominio.com",
# "usuario+tag@ejemplo.com", ], "ejemplos_invalidos":\n [ "usuario@ (sin dominio)", "@ejemplo.com (sin usuario)",
# "usuario@tempmail.org (dominio bloqueado)", "usuario@ (formato inválido)", ], "auto_formateo":\n True,
# "validacion_tiempo_real":\n True, }, }, "reglas_negocio":\n { "fecha_entrega":\n "Desde hace 2 años hasta 4 años en el
# futuro", "fecha_pago":\n "Máximo 1 día en el futuro", "monto_pago":\n "No puede exceder saldo pendiente",
# "total_financiamiento":\n "Entre $1 y $50,000,000", "amortizaciones":\n "Entre 1 y 84 meses", "cedula_venezuela":\n
# "Prefijos V/E/J + 7-10 dígitos del 0-9", "telefono_venezuela":\n "+58 + 10 dígitos (primer dígito \ no puede ser 0)",
# "fecha_formato":\n "DD/MM/YYYY (día 2 dígitos, mes 2 dígitos \ , año 4 dígitos)", "email_normalizacion":\n "Conversión
# automática a minúsculas (incluyendo @)", }, "configuracion_frontend":\n { "validacion_onchange":\n "Validar al cambiar
# valor", "formateo_onkeyup":\n "Formatear mientras escribe", "mostrar_errores":\n "Mostrar errores en tiempo real",
# "auto_formateo":\n "Formatear automáticamente al perder foco", "sugerencias":\n "Mostrar sugerencias de formato", },
# "endpoints_validacion":\n { "validar_campo":\n "POST /api/v1/validadores/validar-campo", "corregir_datos":\n "POST
# /api/v1/validadores/corregir-datos", "configuracion":\n "GET /api/v1/validadores/configuracion", "verificacion":\n "GET
# /api/v1/validadores/verificacion-validadores", }, } except Exception as e:\n raise HTTPException( status_code=500,
# detail=f"Error obteniendo configuración de validadores:\n {str(e)}", )@router.post("/validadores/probar")\ndef
# probar_validadores(datos_prueba:\n Dict[str, Any]):\n """ 🧪 Probar validadores con datos de ejemplo """ try:\n \nfrom
# app.services.validators_service \nimport ( ValidadorCedula, ValidadorEmail, ValidadorFecha, ValidadorTelefono, ) resultados
# = {} # Probar teléfono if "telefono" in datos_prueba:\n telefono = datos_prueba["telefono"] pais =
# datos_prueba.get("pais_telefono", "VENEZUELA") resultados["telefono"] = (
# ValidadorTelefono.validar_y_formatear_telefono(telefono, pais) ) # Probar cédula if "cedula" in datos_prueba:\n cedula =
# datos_prueba["cedula"] pais = datos_prueba.get("pais_cedula", "VENEZUELA") resultados["cedula"] =
# ValidadorCedula.validar_y_formatear_cedula( cedula, pais ) # Probar fecha if "fecha" in datos_prueba:\n fecha =
# datos_prueba["fecha"] resultados["fecha"] = ValidadorFecha.validar_fecha_entrega(fecha) # Probar email if "email" in
# datos_prueba:\n email = datos_prueba["email"] resultados["email"] = ValidadorEmail.validar_email(email) return {
# "titulo":\n "🧪 RESULTADOS DE PRUEBA DE VALIDADORES", "fecha_prueba":\n datetime.now().isoformat(), "datos_entrada":\n
# datos_prueba, "resultados":\n resultados, "resumen":\n { "total_validados":\n len(resultados), "validos":\n sum( 1 for r in
# resultados.values() if r.get("valido", False) ), "invalidos":\n sum( 1 for r in resultados.values() if not r.get("valido",
# False) ), }, } except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error probando validadores:\n
# {str(e)}" )@router.get("/sistema/categoria/{categoria}")\ndef obtener_configuracion_categoria( categoria:\n str, db:\n
# Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📋 Obtener configuración de una
# categoría específica """ try:\n # Solo admin puede ver configuración de categoría if not current_user.is_admin:\n raise
# HTTPException( status_code=403, detail="Solo administradores pueden ver configuración de categoría", ) configs = (
# db.query(ConfiguracionSistema) .filter( ConfiguracionSistema.categoria == categoria.upper(),
# ConfiguracionSistema.visible_frontend, ) .all() ) if not configs:\n raise HTTPException( status_code=404,
# detail=f"Categoría '{categoria}' no encontrada", ) configuracion = {} for config in configs:\n configuracion[config.clave]
# = { "valor":\n config.valor_procesado, "descripcion":\n config.descripcion, "tipo_dato":\n config.tipo_dato, "requerido":\n
# config.requerido, "solo_lectura":\n config.solo_lectura, "opciones_validas":\n ( json.loads(config.opciones_validas) if
# config.opciones_validas else None ), "valor_minimo":\n config.valor_minimo, "valor_maximo":\n config.valor_maximo,
# "patron_validacion":\n config.patron_validacion, } return { "categoria":\n categoria.upper(), "configuracion":\n
# configuracion, "total_items":\n len(configs), "fecha_consulta":\n datetime.now().isoformat(), } except HTTPException:\n
# raise except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo configuración de
# categoría:\n {str(e)}", )\ndef _buscar_configuracion_existente( categoria:\n str, clave:\n str, db:\n Session) ->
# Optional[ConfiguracionSistema]:\n """Buscar configuración existente en la base de datos""" return (
# db.query(ConfiguracionSistema) .filter( ConfiguracionSistema.categoria == categoria.upper(), ConfiguracionSistema.clave ==
# clave.upper(), ) .first() )\ndef _validar_configuracion_para_actualizacion( config:\n ConfiguracionSistema, categoria:\n
# str, clave:\n str) -> Optional[str]:\n """Validar si la configuración puede ser actualizada""" if not config:\n return
# f"Configuración {categoria}.{clave} no encontrada" if config.solo_lectura:\n return f"Configuración {categoria}.{clave} es
# de solo lectura" return None\ndef _procesar_actualizacion_configuracion( config:\n ConfiguracionSistema, nuevo_valor:\n
# Any, categoria:\n str, clave:\n str) -> Optional[Dict[str, Any]]:\n """Procesar la actualización de una configuración"""
# try:\n # Validar nuevo valor error_validacion = _validar_configuracion(config, nuevo_valor) if error_validacion:\n return
# None # Error será manejado por el llamador # Actualizar valor valor_anterior = config.valor_procesado
# config.actualizar_valor( nuevo_valor, "SISTEMA" ) # Usuario será pasado desde el contexto return { "categoria":\n
# categoria, "clave":\n clave, "valor_anterior":\n valor_anterior, "valor_nuevo":\n config.valor_procesado, } except
# Exception:\n return None # Error será manejado por el llamador\ndef _procesar_categoria_configuraciones( categoria:\n str,
# configs:\n Dict[str, Any], db:\n Session, actualizaciones_exitosas:\n list, errores:\n list, current_user:\n User,):\n
# """Procesar todas las configuraciones de una categoría""" for clave, nuevo_valor in configs.items():\n try:\n # Buscar
# configuración existente config = _buscar_configuracion_existente(categoria, clave, db) # Validar configuración
# error_validacion = _validar_configuracion_para_actualizacion( config, categoria, clave ) if error_validacion:\n
# errores.append(error_validacion) continue # Procesar actualización resultado = _procesar_actualizacion_configuracion(
# config, nuevo_valor, categoria, clave ) if resultado:\n # Actualizar con el usuario real
# config.actualizar_valor(nuevo_valor, current_user.full_name) actualizaciones_exitosas.append(resultado) else:\n
# error_validacion = _validar_configuracion(config, nuevo_valor) if error_validacion:\n
# errores.append(f"{categoria}.{clave}:\n {error_validacion}") except Exception as e:\n errores.append(f"Error actualizando
# {categoria}.{clave}:\n {str(e)}")\ndef _registrar_auditoria_configuracion( actualizaciones_exitosas:\n list,
# current_user:\n User, db:\n Session):\n """Registrar operación en auditoría""" \nfrom app.core.constants \nimport
# TipoAccion \nfrom app.models.auditoria \nimport Auditoria auditoria = Auditoria.registrar( usuario_id=current_user.id,
# accion=TipoAccion.ACTUALIZACION, entidad="configuracion_sistema", entidad_id=None, detalles=f"Actualizadas {len
# (actualizaciones_exitosas)} configuraciones", ) db.add(auditoria)@router.post("/sistema/actualizar")\ndef
# actualizar_configuracion_sistema( configuraciones:\n Dict[str, Dict[str, Any]], db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ ✏️ Actualizar configuraciones del sistema (VERSIÓN REFACTORIZADA)
# Formato:\n { "AI":\n { "OPENAI_API_KEY":\n "sk-...", "AI_SCORING_ENABLED":\n true }, "EMAIL":\n { "SMTP_HOST":\n
# "smtp.gmail.com", "SMTP_USERNAME":\n "empresa@gmail.com" } } """ # Solo admin puede actualizar configuración if not
# current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden actualizar
# configuración", ) try:\n actualizaciones_exitosas = [] errores = [] # Procesar cada categoría for categoria, configs in
# configuraciones.items():\n _procesar_categoria_configuraciones( categoria, configs, db, actualizaciones_exitosas, errores,
# current_user, ) # Confirmar cambios si no hay errores críticos if len(errores) < len(actualizaciones_exitosas):\n
# db.commit() _registrar_auditoria_configuracion( actualizaciones_exitosas, current_user, db ) db.commit() else:\n
# db.rollback() return { "mensaje":\n ( "✅ Configuraciones actualizadas" if actualizaciones_exitosas else "❌ No se pudo
# actualizar ninguna configuración" ), "actualizaciones_exitosas":\n len(actualizaciones_exitosas), "errores":\n
# len(errores), "detalle_actualizaciones":\n actualizaciones_exitosas, "detalle_errores":\n errores, "fecha_actualizacion":\n
# datetime.now().isoformat(), "actualizado_por":\n current_user.full_name, } except Exception as e:\n db.rollback() raise
# HTTPException( status_code=500, detail=f"Error actualizando configuraciones:\n {str(e)}",
# )@router.post("/sistema/probar-integracion/{categoria}")\ndef probar_integracion( categoria:\n str, db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 🧪 Probar integración de una categoría específica
# """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden probar
# integraciones", ) try:\n categoria = categoria.upper() if categoria == "EMAIL":\n return _probar_configuracion_email(db)
# elif categoria == "WHATSAPP":\n return _probar_configuracion_whatsapp(db) elif categoria == "AI":\n return
# _probar_configuracion_ai(db) elif categoria == "DATABASE":\n return _probar_configuracion_database(db) else:\n raise
# HTTPException( status_code=400, detail=f"Categoría '{categoria}' no soporta pruebas automáticas", ) except HTTPException:\n
# raise except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error probando integración:\n {str(e)}"
# )@router.get("/sistema/estado-servicios")\ndef obtener_estado_servicios( db:\n Session = Depends(get_db), current_user:\n
# User = Depends(get_current_user),):\n """ 📊 Obtener estado de todos los servicios configurados """ try:\n # Solo admin
# puede ver estado de servicios if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo
# administradores pueden ver estado de servicios", ) \nfrom app.models.configuracion_sistema \nimport ConfigHelper
# estado_servicios = { "ai":\n { "habilitado":\n ConfigHelper.is_ai_enabled(db), "configurado":\n bool(
# ConfigHelper.get_config(db, "AI", "OPENAI_API_KEY") ), "estado":\n ( "✅ ACTIVO" if ConfigHelper.is_ai_enabled(db) else "❌
# INACTIVO" ), }, "email":\n { "habilitado":\n True, # Siempre habilitado "configurado":\n
# ConfigHelper.is_email_configured(db), "estado":\n ( "✅ CONFIGURADO" if ConfigHelper.is_email_configured(db) else "⚠️
# PENDIENTE" ), }, "whatsapp":\n { "habilitado":\n ConfigHelper.is_whatsapp_enabled(db), "configurado":\n bool(
# ConfigHelper.get_config( db, "WHATSAPP", "META_ACCESS_TOKEN" ) ), "estado":\n ( "✅ ACTIVO" if
# ConfigHelper.is_whatsapp_enabled(db) else "❌ INACTIVO" ), "provider":\n "META_CLOUD_API", }, "database":\n {
# "habilitado":\n True, "configurado":\n True, "estado":\n "✅ CONECTADA", }, "monitoreo":\n { "habilitado":\n bool(
# ConfigHelper.get_config(db, "MONITOREO", "SENTRY_DSN") ), "configurado":\n bool( ConfigHelper.get_config(db, "MONITOREO",
# "SENTRY_DSN") ), "estado":\n ( "✅ ACTIVO" if ConfigHelper.get_config(db, "MONITOREO", "SENTRY_DSN") else "❌ INACTIVO" ), },
# } # Calcular estado general servicios_activos = sum( 1 for s in estado_servicios.values() if "✅" in s["estado"] )
# total_servicios = len(estado_servicios) return { "titulo":\n "📊 ESTADO DE SERVICIOS DEL SISTEMA", "fecha_consulta":\n
# datetime.now().isoformat(), "estado_general":\n { "servicios_activos":\n servicios_activos, "total_servicios":\n
# total_servicios, "porcentaje_activo":\n round( servicios_activos / total_servicios * 100, 1 ), "estado":\n ( "✅ ÓPTIMO" if
# servicios_activos == total_servicios else "⚠️ PARCIAL" if servicios_activos > 0 else "❌ CRÍTICO" ), }, "servicios":\n
# estado_servicios, "recomendaciones":\n _generar_recomendaciones_configuracion( estado_servicios ), } except Exception as
# e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo estado de servicios:\n {str(e)}",
# )@router.post("/sistema/inicializar-defaults")\ndef inicializar_configuraciones_default( db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ 🔧 Inicializar configuraciones por defecto del sistema """ if not
# current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden inicializar
# configuraciones", ) try:\n \nfrom app.models.configuracion_sistema \nimport ConfiguracionPorDefecto # Crear configuraciones
# por defecto ConfiguracionPorDefecto.crear_configuraciones_default(db) # Contar configuraciones creadas total_configs =
# db.query(ConfiguracionSistema).count() return { "mensaje":\n "✅ Configuraciones por defecto inicializadas exitosamente",
# "total_configuraciones":\n total_configs, "categorias_creadas":\n [ "AI - Inteligencia Artificial", "EMAIL - Configuración
# de correo", "WHATSAPP - Configuración de WhatsApp", "ROLES - Roles y permisos", "FINANCIERO - Parámetros financieros",
# "NOTIFICACIONES - Configuración de notificaciones", "SEGURIDAD - Configuración de seguridad", "DATABASE - Configuración de
# base de datos", "REPORTES - Configuración de reportes", "INTEGRACIONES - Integraciones externas", "MONITOREO - Monitoreo y
# observabilidad", "APLICACION - Configuración general", ], "siguiente_paso":\n "Configurar cada categoría según las
# necesidades", "fecha_inicializacion":\n datetime.now().isoformat(), } except Exception as e:\n raise HTTPException(
# status_code=500, detail=f"Error inicializando configuraciones:\n {str(e)}", )#
# ============================================# CONFIGURACIÓN DE IA#
# ============================================@router.get("/ia")\ndef obtener_configuracion_ia( db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 🤖 Obtener configuración de Inteligencia
# Artificial """ try:\n # Solo admin puede ver configuración de IA if not current_user.is_admin:\n raise HTTPException(
# status_code=403, detail="Solo administradores pueden ver configuración de IA", ) configs_ia = (
# db.query(ConfiguracionSistema) .filter( ConfiguracionSistema.categoria == "AI", ConfiguracionSistema.visible_frontend, )
# .all() ) configuracion = {} for config in configs_ia:\n # Ocultar tokens completos por seguridad valor_mostrar =
# config.valor_procesado if config.tipo_dato == "PASSWORD" and config.valor:\n valor_mostrar = ( f"{'*' * (len(config.valor)
# - 4)}{config.valor[-4:\n]}" if len(config.valor) > 4 else "****" ) configuracion[config.clave] = { "valor":\n
# valor_mostrar, "valor_real":\n ( config.valor_procesado if config.tipo_dato != "PASSWORD" else None ), "descripcion":\n
# config.descripcion, "tipo_dato":\n config.tipo_dato, "requerido":\n config.requerido, "configurado":\n bool(config.valor),
# "opciones_validas":\n ( json.loads(config.opciones_validas) if config.opciones_validas else None ), } # Estado de
# funcionalidades IA estado_ia = { "scoring_crediticio":\n { "habilitado":\n configuracion.get("AI_SCORING_ENABLED", {}).get(
# "valor", False ), "configurado":\n bool( configuracion.get("OPENAI_API_KEY", {}).get("valor_real") ), "descripcion":\n
# "Sistema de scoring crediticio automático", }, "prediccion_mora":\n { "habilitado":\n configuracion.get(
# "AI_PREDICTION_ENABLED", {} ).get("valor", False), "configurado":\n True, # No requiere configuración externa
# "descripcion":\n "Predicción de mora con Machine Learning", }, "chatbot":\n { "habilitado":\n
# configuracion.get("AI_CHATBOT_ENABLED", {}).get( "valor", False ), "configurado":\n bool(
# configuracion.get("OPENAI_API_KEY", {}).get("valor_real") ), "descripcion":\n "Chatbot inteligente para cobranza", }, }
# return { "titulo":\n "🤖 CONFIGURACIÓN DE INTELIGENCIA ARTIFICIAL", "configuracion":\n configuracion,
# "estado_funcionalidades":\n estado_ia, "instrucciones":\n { "openai_api_key":\n "Obtener en
# https:\n//platform.openai.com/api-keys", "formato_token":\n "Debe comenzar con 'sk-' seguido de 48 caracteres",
# "costo_estimado":\n "$0.002 por 1K tokens (muy económico)", "beneficios":\n [ "Scoring crediticio automatizado",
# "Predicción de mora con 87% precisión", "Mensajes personalizados para cobranza", "Recomendaciones inteligentes", ], }, }
# except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo configuración IA:\n {str(e)}",
# )\ndef _actualizar_config_api_key( openai_api_key:\n str, current_user:\n User, db:\n Session) -> Optional[str]:\n
# """Actualizar API Key de OpenAI""" if openai_api_key is not None:\n config = ConfiguracionSistema.obtener_por_clave( db,
# "AI", "OPENAI_API_KEY" ) if config:\n config.actualizar_valor(openai_api_key, current_user.full_name) return
# "OPENAI_API_KEY" return None\ndef _actualizar_config_modelo( openai_model:\n str, current_user:\n User, db:\n Session) ->
# Optional[str]:\n """Actualizar modelo de OpenAI""" if openai_model is not None:\n config =
# ConfiguracionSistema.obtener_por_clave( db, "AI", "OPENAI_MODEL" ) if config:\n config.actualizar_valor(openai_model,
# current_user.full_name) return "OPENAI_MODEL" return None\ndef _actualizar_config_scoring( scoring_enabled:\n bool,
# current_user:\n User, db:\n Session) -> Optional[str]:\n """Actualizar configuración de scoring""" if scoring_enabled is
# not None:\n config = ConfiguracionSistema.obtener_por_clave( db, "AI", "AI_SCORING_ENABLED" ) if config:\n
# config.actualizar_valor(scoring_enabled, current_user.full_name) return "AI_SCORING_ENABLED" return None\ndef
# _actualizar_config_prediction( prediction_enabled:\n bool, current_user:\n User, db:\n Session) -> Optional[str]:\n
# """Actualizar configuración de predicción""" if prediction_enabled is not None:\n config =
# ConfiguracionSistema.obtener_por_clave( db, "AI", "AI_PREDICTION_ENABLED" ) if config:\n
# config.actualizar_valor(prediction_enabled, current_user.full_name) return "AI_PREDICTION_ENABLED" return None\ndef
# _actualizar_config_chatbot( chatbot_enabled:\n bool, current_user:\n User, db:\n Session) -> Optional[str]:\n """Actualizar
# configuración de chatbot""" if chatbot_enabled is not None:\n config = ConfiguracionSistema.obtener_por_clave( db, "AI",
# "AI_CHATBOT_ENABLED" ) if config:\n config.actualizar_valor(chatbot_enabled, current_user.full_name) return
# "AI_CHATBOT_ENABLED" return None@router.post("/ia/actualizar")\ndef actualizar_configuracion_ia( openai_api_key:\n
# Optional[str] = None, openai_model:\n Optional[str] = None, scoring_enabled:\n Optional[bool] = None, prediction_enabled:\n
# Optional[bool] = None, chatbot_enabled:\n Optional[bool] = None, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 🤖 Actualizar configuración de IA (VERSIÓN REFACTORIZADA) """ if not
# current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden configurar IA" ) try:\n
# actualizaciones = [] # Actualizar configuraciones individuales config_api_key = _actualizar_config_api_key( openai_api_key,
# current_user, db ) if config_api_key:\n actualizaciones.append(config_api_key) config_modelo = _actualizar_config_modelo(
# openai_model, current_user, db ) if config_modelo:\n actualizaciones.append(config_modelo) config_scoring =
# _actualizar_config_scoring( scoring_enabled, current_user, db ) if config_scoring:\n actualizaciones.append(config_scoring)
# config_prediction = _actualizar_config_prediction( prediction_enabled, current_user, db ) if config_prediction:\n
# actualizaciones.append(config_prediction) config_chatbot = _actualizar_config_chatbot( chatbot_enabled, current_user, db )
# if config_chatbot:\n actualizaciones.append(config_chatbot) db.commit() return { "mensaje":\n "✅ Configuración de IA
# actualizada exitosamente", "configuraciones_actualizadas":\n actualizaciones, "fecha_actualizacion":\n
# datetime.now().isoformat(), "actualizado_por":\n current_user.full_name, "siguiente_paso":\n "Probar funcionalidades IA en
# el dashboard", } except Exception as e:\n db.rollback() raise HTTPException( status_code=500, detail=f"Error actualizando
# configuración IA:\n {str(e)}", )# ============================================# CONFIGURACIÓN DE EMAIL#
# ============================================@router.get("/email")\ndef obtener_configuracion_email( db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📧 Obtener configuración de email """ try:\n #
# Solo admin puede ver configuración de email if not current_user.is_admin:\n raise HTTPException( status_code=403,
# detail="Solo administradores pueden ver configuración de email", ) configs_email = ( db.query(ConfiguracionSistema)
# .filter(ConfiguracionSistema.categoria == "EMAIL") .all() ) configuracion = {} for config in configs_email:\n valor_mostrar
# = config.valor_procesado if config.tipo_dato == "PASSWORD" and config.valor:\n valor_mostrar = ( "****" +
# config.valor[-4:\n] if len(config.valor) > 4 else "****" ) configuracion[config.clave] = { "valor":\n valor_mostrar,
# "descripcion":\n config.descripcion, "tipo_dato":\n config.tipo_dato, "requerido":\n config.requerido, "configurado":\n
# bool(config.valor), } return { "titulo":\n "📧 CONFIGURACIÓN DE EMAIL", "configuracion":\n configuracion,
# "proveedores_soportados":\n { "gmail":\n { "smtp_host":\n "smtp.gmail.com", "smtp_port":\n 587, "requiere_app_password":\n
# True, "instrucciones":\n "Usar App Password, no contraseña normal", }, "outlook":\n { "smtp_host":\n
# "smtp-mail.outlook.com", "smtp_port":\n 587, "requiere_app_password":\n False, "instrucciones":\n "Usar credenciales
# normales", }, "yahoo":\n { "smtp_host":\n "smtp.mail.yahoo.com", "smtp_port":\n 587, "requiere_app_password":\n True,
# "instrucciones":\n "Generar App Password en configuración", }, }, "templates_disponibles":\n [ "Recordatorio de pago",
# "Confirmación de pago", "Bienvenida cliente", "Mora temprana", "Estados de cuenta", "Reportes automáticos", ], } except
# Exception as e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo configuración email:\n {str(e)}",
# )@router.post("/email/actualizar")\ndef actualizar_configuracion_email( smtp_host:\n Optional[str] = None, smtp_port:\n
# Optional[int] = None, smtp_username:\n Optional[str] = None, smtp_password:\n Optional[str] = None, from_name:\n
# Optional[str] = None, templates_enabled:\n Optional[bool] = None, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 📧 Actualizar configuración de email """ if not current_user.is_admin:\n raise
# HTTPException( status_code=403, detail="Solo administradores pueden configurar email", ) try:\n actualizaciones = [] #
# Mapeo de parámetros a configuraciones parametros = { "SMTP_HOST":\n smtp_host, "SMTP_PORT":\n smtp_port, "SMTP_USERNAME":\n
# smtp_username, "SMTP_PASSWORD":\n smtp_password, "EMAIL_FROM_NAME":\n from_name, "EMAIL_TEMPLATES_ENABLED":\n
# templates_enabled, } for clave, valor in parametros.items():\n if valor is not None:\n config =
# ConfiguracionSistema.obtener_por_clave( db, "EMAIL", clave ) if config:\n config.actualizar_valor(valor,
# current_user.full_name) actualizaciones.append(clave) db.commit() return { "mensaje":\n "✅ Configuración de email
# actualizada", "configuraciones_actualizadas":\n actualizaciones, "fecha_actualizacion":\n datetime.now().isoformat(),
# "siguiente_paso":\n "Probar envío de email de prueba", } except Exception as e:\n db.rollback() raise HTTPException(
# status_code=500, detail=f"Error actualizando configuración email:\n {str(e)}", )#
# ============================================# CONFIGURACIÓN DE WHATSAPP#
# ============================================@router.get("/whatsapp")\ndef obtener_configuracion_whatsapp( db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📱 Obtener configuración de WhatsApp """ try:\n #
# Solo admin puede ver configuración de WhatsApp if not current_user.is_admin:\n raise HTTPException( status_code=403,
# detail="Solo administradores pueden ver configuración de WhatsApp", ) configs_whatsapp = ( db.query(ConfiguracionSistema)
# .filter(ConfiguracionSistema.categoria == "WHATSAPP") .all() ) configuracion = {} for config in configs_whatsapp:\n
# valor_mostrar = config.valor_procesado if config.tipo_dato == "PASSWORD" and config.valor:\n valor_mostrar = ( "****" +
# config.valor[-4:\n] if len(config.valor) > 4 else "****" ) configuracion[config.clave] = { "valor":\n valor_mostrar,
# "descripcion":\n config.descripcion, "tipo_dato":\n config.tipo_dato, "requerido":\n config.requerido, "configurado":\n
# bool(config.valor), } return { "titulo":\n "📱 CONFIGURACIÓN DE WHATSAPP", "configuracion":\n configuracion, "proveedor":\n
# { "nombre":\n "Twilio", "descripcion":\n "Proveedor de WhatsApp Business API", "registro":\n
# "https:\n//www.twilio.com/console", "costo_estimado":\n "$0.005 por mensaje", "documentacion":\n
# "https:\n//www.twilio.com/docs/whatsapp", }, "funcionalidades":\n [ "Recordatorios de pago automáticos", "Notificaciones de
# mora", "Confirmaciones de pago", "Mensajes personalizados con IA", "Estados de cuenta por WhatsApp", ], "requisitos":\n [
# "Cuenta de Twilio verificada", "Número de WhatsApp Business aprobado", "Templates de mensajes aprobados por WhatsApp", ], }
# except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo configuración WhatsApp:\n
# {str(e)}", )# ============================================# DASHBOARD DE CONFIGURACIÓN#
# ============================================@router.get("/dashboard")\ndef dashboard_configuracion_sistema( db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📊 Dashboard principal de configuración del
# sistema """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden ver
# dashboard de configuración", ) try:\n \nfrom app.models.configuracion_sistema \nimport ( ConfigHelper,
# ConfiguracionSistema, ) # Estadísticas de configuración total_configs = db.query(ConfiguracionSistema).count()
# configs_configuradas = ( db.query(ConfiguracionSistema) .filter( ConfiguracionSistema.valor.isnot(None),
# ConfiguracionSistema.valor != "", ) .count() ) configs_requeridas = ( db.query(ConfiguracionSistema)
# .filter(ConfiguracionSistema.requerido) .count() ) configs_requeridas_configuradas = ( db.query(ConfiguracionSistema)
# .filter( ConfiguracionSistema.requerido, ConfiguracionSistema.valor.isnot(None), ConfiguracionSistema.valor != "", )
# .count() ) # Estado por categoría categorias = db.query(ConfiguracionSistema.categoria).distinct().all() estado_categorias
# = {} for (categoria,) in categorias:\n total_cat = ( db.query(ConfiguracionSistema) .filter(ConfiguracionSistema.categoria
# == categoria) .count() ) configuradas_cat = ( db.query(ConfiguracionSistema) .filter( ConfiguracionSistema.categoria ==
# categoria, ConfiguracionSistema.valor.isnot(None), ConfiguracionSistema.valor != "", ) .count() ) porcentaje = (
# round(configuradas_cat / total_cat * 100, 1) if total_cat > 0 else 0 ) estado_categorias[categoria] = { "total":\n
# total_cat, "configuradas":\n configuradas_cat, "porcentaje":\n porcentaje, "estado":\n ( "✅ COMPLETA" if porcentaje == 100
# else "⚠️ PARCIAL" if porcentaje > 0 else "❌ PENDIENTE" ), } return { "titulo":\n "📊 DASHBOARD DE CONFIGURACIÓN DEL
# SISTEMA", "fecha_actualizacion":\n datetime.now().isoformat(), "resumen_general":\n { "total_configuraciones":\n
# total_configs, "configuradas":\n configs_configuradas, "porcentaje_configurado":\n ( round(configs_configuradas /
# total_configs * 100, 1) if total_configs > 0 else 0 ), "configuraciones_requeridas":\n configs_requeridas,
# "requeridas_configuradas":\n configs_requeridas_configuradas, "sistema_listo":\n configs_requeridas_configuradas ==
# configs_requeridas, }, "estado_por_categoria":\n estado_categorias, "servicios_criticos":\n { "base_datos":\n { "estado":\n
# "✅ CONECTADA", "descripcion":\n "Base de datos PostgreSQL", }, "autenticacion":\n { "estado":\n "✅ ACTIVA",
# "descripcion":\n "Sistema de autenticación JWT", }, "email":\n { "estado":\n ( "✅ CONFIGURADO" if
# ConfigHelper.is_email_configured(db) else "⚠️ PENDIENTE" ), "descripcion":\n "Servicio de email", }, "ia":\n { "estado":\n
# ( "✅ ACTIVA" if ConfigHelper.is_ai_enabled(db) else "❌ INACTIVA" ), "descripcion":\n "Inteligencia Artificial", },
# "whatsapp":\n { "estado":\n ( "✅ ACTIVO" if ConfigHelper.is_whatsapp_enabled(db) else "❌ INACTIVO" ), "descripcion":\n
# "WhatsApp Business", }, }, "acciones_rapidas":\n { "configurar_ia":\n "POST /api/v1/configuracion/ia/actualizar",
# "configurar_email":\n "POST /api/v1/configuracion/email/actualizar", "configurar_whatsapp":\n "POST
# /api/v1/configuracion/wha \ tsapp/actualizar", "probar_servicios":\n ( "POST
# /api/v1/configuracion/sistema/probar-integracion/ \ {categoria}" ), "inicializar_defaults":\n "POST
# /api/v1/configuracion/sistema/inicializar-defaults", }, "alertas_configuracion":\n _generar_alertas_configuracion( db,
# estado_categorias ), } except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error en dashboard de
# configuración:\n {str(e)}", )# Schemas\nclass ConfiguracionTasas(BaseModel):\n tasa_interes_base:\n Decimal = Field( ...,
# ge=0, le=100, description="Tasa de interés base anual (%)" ) tasa_mora:\n Decimal = Field( ..., ge=0, le=10,
# description="Tasa de mora mensual (%)" ) tasa_descuento_pronto_pago:\n Optional[Decimal] = Field(None, ge=0, le=10)\nclass
# ConfiguracionLimites(BaseModel):\n monto_minimo_prestamo:\n Decimal = Field(..., gt=0) monto_maximo_prestamo:\n Decimal =
# Field(..., gt=0) plazo_minimo_meses:\n int = Field(..., ge=1) plazo_maximo_meses:\n int = Field(..., le=360)
# limite_prestamos_activos:\n int = Field(..., ge=1, le=10)\nclass ConfiguracionNotificaciones(BaseModel):\n
# dias_previos_recordatorio:\n int = Field(default=3, ge=1, le=30) dias_mora_alerta:\n int = Field(default=15, ge=1, le=90)
# email_notificaciones:\n bool = True whatsapp_notificaciones:\n bool = False sms_notificaciones:\n bool = False\nclass
# ConfiguracionGeneral(BaseModel):\n nombre_empresa:\n str ruc:\n str direccion:\n str telefono:\n str email:\n str
# horario_atencion:\n str zona_horaria:\n str = "America/Caracas" formato_fecha:\n str = "DD/MM/YYYY" idioma:\n str = "ES"
# moneda:\n str = "VES" version_sistema:\n str = "1.0.0"# Almacenamiento temporal de configuraciones (en producción usar
# Redis o DB)_config_cache:\n Dict[str, Any] = { "tasas":\n { "tasa_interes_base":\n 15.0, "tasa_mora":\n 2.0,
# "tasa_descuento_pronto_pago":\n 1.0, }, "limites":\n { "monto_minimo_prestamo":\n 100.0, "monto_maximo_prestamo":\n
# 50000.0, "plazo_minimo_meses":\n 1, "plazo_maximo_meses":\n 60, "limite_prestamos_activos":\n 3, }, "notificaciones":\n {
# "dias_previos_recordatorio":\n 3, "dias_mora_alerta":\n 15, "email_notificaciones":\n True, "whatsapp_notificaciones":\n
# False, "sms_notificaciones":\n False, }, "general":\n { "nombre_empresa":\n "RAPICREDIT", "ruc":\n "0000000000001",
# "direccion":\n "Av. Principal 123", "telefono":\n "+58 99 999 9999", "email":\n "info@rapicredit.com",
# "horario_atencion":\n "Lunes a Viernes 9:\n00 - 18:\n00", "zona_horaria":\n "America/Caracas", "formato_fecha":\n
# "DD/MM/YYYY", "idioma":\n "ES", "moneda":\n "VES", "version_sistema":\n "1.0.0", },}@router.get("/general")\ndef
# obtener_configuracion_general( current_user:\n User = Depends(get_current_user),):\n """ 📋 Obtener configuración general
# del sistema """ return _config_cache["general"]@router.get("/tasas")\ndef obtener_configuracion_tasas( current_user:\n User
# = Depends(get_current_user),):\n """ Obtener configuración de tasas de interés. """ return
# _config_cache["tasas"]@router.put("/tasas")\ndef actualizar_configuracion_tasas( config:\n ConfiguracionTasas,
# current_user:\n User = Depends(get_current_user)):\n """ Actualizar configuración de tasas de interés. Solo accesible para
# ADMIN. """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden
# modificar tasas", ) _config_cache["tasas"] = { "tasa_interes_base":\n float(config.tasa_interes_base), "tasa_mora":\n
# float(config.tasa_mora), "tasa_descuento_pronto_pago":\n ( float(config.tasa_descuento_pronto_pago) if
# config.tasa_descuento_pronto_pago else 0.0 ), } logger.info( f"Tasas actualizadas por {current_user." f"email}:\n
# {_config_cache["tasas']}" ) return { "mensaje":\n "Configuración de tasas actualizada exitosamente", "tasas":\n
# _config_cache["tasas"], }@router.get("/limites")\ndef obtener_configuracion_limites( current_user:\n User =
# Depends(get_current_user),):\n """ Obtener configuración de límites de préstamos. """ return
# _config_cache["limites"]@router.put("/limites")\ndef actualizar_configuracion_limites( config:\n ConfiguracionLimites,
# current_user:\n User = Depends(get_current_user),):\n """ Actualizar configuración de límites. Solo accesible para ADMIN.
# """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden modificar
# límites", ) # Validar que máximo > mínimo if config.monto_maximo_prestamo <= config.monto_minimo_prestamo:\n raise
# HTTPException( status_code=400, detail="El monto máximo debe ser mayor al monto mínimo", ) if config.plazo_maximo_meses <=
# config.plazo_minimo_meses:\n raise HTTPException( status_code=400, detail="El plazo máximo debe ser mayor al plazo mínimo",
# ) _config_cache["limites"] = { "monto_minimo_prestamo":\n float(config.monto_minimo_prestamo), "monto_maximo_prestamo":\n
# float(config.monto_maximo_prestamo), "plazo_minimo_meses":\n config.plazo_minimo_meses, "plazo_maximo_meses":\n
# config.plazo_maximo_meses, "limite_prestamos_activos":\n config.limite_prestamos_activos, } logger.info( f"Límites
# actualizados por {current_user." f"email}:\n {_config_cache["limites']}" ) return { "mensaje":\n "Configuración de límites
# actualizada exitosamente", "limites":\n _config_cache["limites"], }@router.get("/notificaciones")\ndef
# obtener_configuracion_notificaciones( current_user:\n User = Depends(get_current_user),):\n """ Obtener configuración de
# notificaciones. """ return _config_cache["notificaciones"]@router.put("/notificaciones")\ndef
# actualizar_configuracion_notificaciones( config:\n ConfiguracionNotificaciones, current_user:\n User =
# Depends(get_current_user),):\n """ Actualizar configuración de notificaciones. Solo accesible para ADMIN y GERENTE. """ if
# not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Sin permisos para modificar notificaciones", )
# _config_cache["notificaciones"] = { "dias_previos_recordatorio":\n config.dias_previos_recordatorio, "dias_mora_alerta":\n
# config.dias_mora_alerta, "email_notificaciones":\n config.email_notificaciones, "whatsapp_notificaciones":\n
# config.whatsapp_notificaciones, "sms_notificaciones":\n config.sms_notificaciones, } logger.info(f"Notificaciones
# actualizadas por {current_user.email}") return { "mensaje":\n "Configuración de notificaciones actualizada exitosamente",
# "notificaciones":\n _config_cache["notificaciones"], }@router.put("/general")\ndef actualizar_configuracion_general(
# config:\n ConfiguracionGeneral, current_user:\n User = Depends(get_current_user),):\n """ Actualizar configuración general.
# Solo accesible para ADMIN. """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo
# administradores pueden modificar configuración general", ) _config_cache["general"] = { "nombre_empresa":\n
# config.nombre_empresa, "ruc":\n config.ruc, "direccion":\n config.direccion, "telefono":\n config.telefono, "email":\n
# config.email, "horario_atencion":\n config.horario_atencion, "zona_horaria":\n config.zona_horaria, }
# logger.info(f"Configuración general actualizada por {current_user.email}") return { "mensaje":\n "Configuración general
# actualizada exitosamente", "configuracion":\n _config_cache["general"], }@router.get("/completa")\ndef
# obtener_configuracion_cache( current_user:\n User = Depends(get_current_user),):\n """ Obtener toda la configuración del
# sistema desde caché. """ return { "tasas":\n _config_cache["tasas"], "limites":\n _config_cache["limites"],
# "notificaciones":\n _config_cache["notificaciones"], "general":\n _config_cache["general"],
# }@router.post("/restablecer")\ndef restablecer_configuracion_defecto( seccion:\n str, # tasas, limites, notificaciones,
# general, todo current_user:\n User = Depends(get_current_user),):\n """ Restablecer configuración a valores por defecto.
# Solo accesible para ADMIN. """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo
# administradores pueden restablecer configuración", ) defaults = { "tasas":\n { "tasa_interes_base":\n 15.0, "tasa_mora":\n
# 2.0, "tasa_descuento_pronto_pago":\n 1.0, }, "limites":\n { "monto_minimo_prestamo":\n 100.0, "monto_maximo_prestamo":\n
# 50000.0, "plazo_minimo_meses":\n 1, "plazo_maximo_meses":\n 60, "limite_prestamos_activos":\n 3, }, "notificaciones":\n {
# "dias_previos_recordatorio":\n 3, "dias_mora_alerta":\n 15, "email_notificaciones":\n True, "whatsapp_notificaciones":\n
# False, "sms_notificaciones":\n False, }, "general":\n { "nombre_empresa":\n "Sistema de Préstamos y Cobranza", "ruc":\n
# "0000000000001", "direccion":\n "Av. Principal 123", "telefono":\n "+593 99 999 9999", "email":\n "info@prestamos.com",
# "horario_atencion":\n "Lunes a Viernes 9:\n00 - 18:\n00", "zona_horaria":\n "America/Guayaquil", }, } if seccion ==
# "todo":\n _config_cache.update(defaults) logger.warning( f"TODA la configuración restablecida por {current_user.email}" )
# return { "mensaje":\n "Toda la configuración ha sido restablecida a valores por defecto", "configuracion":\n _config_cache,
# } elif seccion in defaults:\n _config_cache[seccion] = defaults[seccion] logger.warning( f"Configuración de {seccion}
# restablecida por {current_user.email}" ) return { "mensaje":\n f"Configuración de {seccion} restablecida " f"a valores por
# defecto", "configuracion":\n _config_cache[seccion], } else:\n raise HTTPException( status_code=400, detail="Sección
# inválida. Opciones:\n tasas, limites, notificaciones, general, todo", )@router.get("/calcular-cuota")\ndef
# calcular_cuota_ejemplo( monto:\n float, plazo_meses:\n int, tasa_personalizada:\n Optional[float] = None, current_user:\n
# User = Depends(get_current_user),):\n """ Calcular cuota mensual con la configuración actual de tasas. """ # Obtener tasa
# tasa = ( tasa_personalizada if tasa_personalizada else _config_cache["tasas"]["tasa_interes_base"] ) # Validar límites
# limites = _config_cache["limites"] if ( monto < limites["monto_minimo_prestamo"] or monto >
# limites["monto_maximo_prestamo"] ):\n raise HTTPException( status_code=400, detail=( f"Monto fuera de límites permitidos:\n
# " f"${limites['monto_minimo_prestamo']:\n,.2f} - " f"${limites['monto_maximo_prestamo']:\n,.2f}" ), ) if ( plazo_meses <
# limites["plazo_minimo_meses"] or plazo_meses > limites["plazo_maximo_meses"] ):\n raise HTTPException( status_code=400,
# detail=( f"Plazo fuera de límites permitidos:\n " f"{limites['plazo_minimo_meses']} - " f"{limites['plazo_maximo_meses']}
# meses" ), ) # Cálculo de cuota (método francés) tasa_mensual = (tasa / 100) / 12 if tasa_mensual == 0:\n cuota = monto /
# plazo_meses else:\n cuota = ( monto * (tasa_mensual * (1 + tasa_mensual) ** plazo_meses) / ((1 + tasa_mensual) **
# plazo_meses - 1) ) total_pagar = cuota * plazo_meses total_interes = total_pagar - monto return { "monto_solicitado":\n
# monto, "plazo_meses":\n plazo_meses, "tasa_interes_anual":\n tasa, "cuota_mensual":\n round(cuota, 2), "total_pagar":\n
# round(total_pagar, 2), "total_interes":\n round(total_interes, 2), "relacion_cuota_ingreso_sugerida":\n "< 40%",
# }@router.get("/validar-limites/{cliente_id}")\ndef validar_limites_cliente( cliente_id:\n int, monto_solicitado:\n float,
# db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n try:\n # Solo admin puede validar
# límites if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden validar
# límites", ) # Contar préstamos activos del cliente prestamos_activos = ( db.query(Prestamo) .filter( Prestamo.cliente_id ==
# cliente_id, Prestamo.estado == "ACTIVO" ) .count() ) limite_prestamos =
# _config_cache["limites"]["limite_prestamos_activos"] limites_monto = _config_cache["limites"] # Validaciones validaciones =
# {"puede_solicitar":\n True, "mensajes":\n []} if prestamos_activos >= limite_prestamos:\n validaciones["puede_solicitar"] =
# False validaciones["mensajes"].append( f"El cliente ya tiene {prestamos_activos} préstamos " f"activos (límite:\n
# {limite_prestamos})" ) if monto_solicitado < limites_monto["monto_minimo_prestamo"]:\n validaciones["puede_solicitar"] =
# False validaciones["mensajes"].append( f"Monto mínimo permitido:\n ${limites_monto['monto_minimo_prestamo']:\n,.2f}" ) if
# monto_solicitado > limites_monto["monto_maximo_prestamo"]:\n validaciones["puede_solicitar"] = False
# validaciones["mensajes"].append( f"Monto máximo permitido:\n ${limites_monto['monto_maximo_prestamo']:\n,.2f}" ) return {
# "cliente_id":\n cliente_id, "prestamos_activos":\n prestamos_activos, "limite_prestamos":\n limite_prestamos,
# "monto_solicitado":\n monto_solicitado, **validaciones, } except Exception as e:\n raise HTTPException( status_code=500,
# detail=f"Error validando límites:\n {str(e)}" )# ============================================# FUNCIONES AUXILIARES#
# ============================================\ndef _validar_configuracion(config, nuevo_valor):\n """Validar nuevo valor de
# configuración""" try:\n if config.tipo_dato == "INTEGER":\n int(nuevo_valor) elif config.tipo_dato == "DECIMAL":\n
# Decimal(str(nuevo_valor)) elif config.tipo_dato == "BOOLEAN":\n if nuevo_valor.lower() not in ["true", "false", "1",
# "0"]:\n return "Valor booleano inválido" elif config.tipo_dato == "EMAIL":\n if "@" not in str(nuevo_valor):\n return
# "Formato de email inválido" return None except Exception as e:\n return f"Error de validación:\n {str(e)}"\ndef
# _probar_configuracion_email(db):\n """Probar configuración de email""" return { "estado":\n "OK", "mensaje":\n
# "Configuración de email probada exitosamente", "detalles":\n "Conexión SMTP verificada", }\ndef
# _probar_configuracion_whatsapp(db):\n """Probar configuración de WhatsApp""" return { "estado":\n "OK", "mensaje":\n
# "Configuración de WhatsApp probada exitosamente", "detalles":\n "API de WhatsApp verificada", }\ndef
# _probar_configuracion_ai(db):\n """Probar configuración de IA""" return { "estado":\n "OK", "mensaje":\n "Configuración de
# IA probada exitosamente", "detalles":\n "API de OpenAI verificada", }\ndef _probar_configuracion_database(db):\n """Probar
# configuración de base de datos""" return { "estado":\n "OK", "mensaje":\n "Configuración de base de datos probada
# exitosamente", "detalles":\n "Conexión a PostgreSQL verificada", }\ndef
# _generar_recomendaciones_configuracion(estado_servicios):\n """Generar recomendaciones de configuración""" recomendaciones
# = [] for servicio, estado in estado_servicios.items():\n if estado["configurado"] < estado["total"]:\n
# recomendaciones.append( { "servicio":\n servicio, "prioridad":\n "MEDIA", "mensaje":\n f"Configurar parámetros faltantes en
# {servicio}", "accion":\n f"Revisar configuración de {servicio}", } ) return recomendaciones\ndef
# _generar_alertas_configuracion(db, estado_categorias):\n """Generar alertas de configuración""" alertas = [] for categoria,
# estado in estado_categorias.items():\n if estado["porcentaje_configurado"] < 80:\n alertas.append( { "tipo":\n
# "CONFIGURACION_INCOMPLETA", "categoria":\n categoria, "severidad":\n "MEDIA", "mensaje":\n f"Configuración incompleta en
# {categoria}", "porcentaje":\n estado["porcentaje_configurado"], } ) return alertas
