# backend/app/api/v1/endpoints/configuracion.py"""Endpoint para configuración administrativa del sistema.Gestión de
# Depends, HTTPException, Query\nfrom pydantic \nimport BaseModel, Field\nfrom sqlalchemy.orm \nimport Session\nfrom
# app.api.deps \nimport get_current_user, get_db\nfrom app.models.configuracion_sistema \nimport ConfiguracionSistema\nfrom
# app.models.prestamo \nimport Prestamo\nfrom app.models.user \nimport User# Funciones auxiliares para validación y
# pruebaslogger = logging.getLogger(__name__)router = APIRouter()# ============================================# MONITOREO Y
# OBSERVABILIDAD# ============================================@router.get("/monitoreo/estado")\ndef
# obtener_estado_monitoreo(current_user:\n User = Depends(get_current_user)):\n """ 🔍 Verificar estado del sistema de
# monitoreo y observabilidad """ # Solo admin puede ver configuración de monitoreo if not current_user.is_admin:\n raise
# HTTPException( status_code=403, detail="Solo administradores pueden ver configuración de m \ onitoreo", ) \nfrom
# habilitar_monitoreo_basico(current_user:\n User = Depends(get_current_user)):\n """ ⚡ Habilitar monitoreo básico sin
# dependencias externas """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo
# administradores pueden configurar monitoreo", ) try:\n # Configurar logging estructurado básico # Configurar formato
# (lineno)d] - %(message)s", datefmt="%Y-%m-%d %H:\n%M:\n%S", ) # Logger específico para el sistema de financiamiento
# finance_logger = logging.getLogger("financiamiento_automotriz") finance_logger.setLevel(logging.INFO) return { "mensaje":\n
# "✅ Monitoreo básico habilitado", "configuracion":\n { "logging_estructurado":\n "✅ Habilitado", "nivel_log":\n "INFO",
# "formato":\n "Timestamp + Archivo + Línea + Mensaje", "logger_especifico":\n "financiamiento_automotriz", },
# operaciones", "⚡ Sin dependencias externas adicionales", ], "siguiente_paso":\n "Configurar Sentry y Prometheus para
# monitoreo avanzado", } except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error habilitando
# monitoreo:\n {str(e)}" )# ============================================# CONFIGURACIÓN CENTRALIZADA DEL SISTEMA#
# ============================================@router.get("/sistema/completa")\ndef obtener_configuracion_completa(
# categoria:\n Optional[str] = Query( None, description="Filtrar por categoría" ), db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ 🔧 Obtener configuración completa del sistema para el frontend """
# # Solo admin puede ver configuración completa if not current_user.is_admin:\n raise HTTPException( status_code=403,
# query = db.query(ConfiguracionSistema).filter( ConfiguracionSistema.visible_frontend ) if categoria:\n query =
# query.filter(ConfiguracionSistema.categoria == categoria) configs = query.all() # Agrupar por categoría
# configuracion_agrupada = {} for config in configs:\n if config.categoria not in configuracion_agrupada:\n
# configuracion_agrupada[config.categoria] = {} configuracion_agrupada[config.categoria][config.clave] = { "valor":\n
# config.valor_procesado, "descripcion":\n config.descripcion, "tipo_dato":\n config.tipo_dato, "requerido":\n
# config.requerido, "solo_lectura":\n config.solo_lectura, "opciones_validas":\n ( json.loads(config.opciones_validas) if
# config.opciones_validas else None ), "valor_minimo":\n config.valor_minimo, "valor_maximo":\n config.valor_maximo,
# "patron_validacion":\n config.patron_validacion, "actualizado_en":\n config.actualizado_en, "actualizado_por":\n
# config.actualizado_por, } return { "titulo":\n "🔧 CONFIGURACIÓN COMPLETA DEL SISTEMA", "fecha_consulta":\n
# "categorias_disponibles":\n list(configuracion_agrupada.keys()), "total_configuraciones":\n len(configs), } except
# Exception as e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo configuración:\n {str(e)}"
# )@router.get("/validadores")\ndef obtener_configuracion_validadores():\n """ 🔍 Obtener configuración completa de
# validadores para el módulo de configuración """ try:\n pass return { "titulo":\n "🔍 CONFIGURACIÓN DE VALIDADORES",
# "validacion_tiempo_real":\n True, }, "fecha":\n { "descripcion":\n "Validación estricta de fechas", "formato_requerido":\n
# guión)", "2024-01-01 (formato YYYY-MM-DD)", "32/01/2024 (día inválido)", ], "auto_formateo":\n False,
# "validacion_tiempo_real":\n True, "requiere_calendario":\n True, }, "email":\n { "descripcion":\n "Validación y
# normalización de emails", "caracteristicas":\n { "normalizacion":\n "Conversión automática a minúsculas", "limpieza":\n
# "USUARIO@EJEMPLO.COM → usuario@ejemplo.com", " Usuario@Ejemplo.com → usuario@ejemplo.com", "usuario.nombre@dominio.com",
# "usuario@tempmail.org (dominio bloqueado)", "usuario@ (formato inválido)", ], "auto_formateo":\n True,
# futuro", "fecha_pago":\n "Máximo 1 día en el futuro", "monto_pago":\n "No puede exceder saldo pendiente",
# "total_financiamiento":\n "Entre $1 y $50,000,000", "amortizaciones":\n "Entre 1 y 84 meses", "cedula_venezuela":\n
# automática a minúsculas (incluyendo @)", }, "configuracion_frontend":\n { "validacion_onchange":\n "Validar al cambiar
# /api/v1/validadores/verificacion-validadores", }, } except Exception as e:\n raise HTTPException( status_code=500,
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
# raise except Exception as e:\n raise HTTPException( status_code=500, detail="Error obteniendo configuración de
# categoría:\n {str(e)}", )\ndef _buscar_configuracion_existente( categoria:\n str, clave:\n str, db:\n Session) ->
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
# """Procesar todas las configuraciones de una categoría""" for clave, nuevo_valor in configs.items():\n try:\n # Buscar
# configuración existente config = _buscar_configuracion_existente(categoria, clave, db) # Validar configuración
# error_validacion = _validar_configuracion_para_actualizacion( config, categoria, clave ) if error_validacion:\n
# errores.append(error_validacion) continue # Procesar actualización resultado = _procesar_actualizacion_configuracion(
# config, nuevo_valor, categoria, clave ) if resultado:\n # Actualizar con el usuario real
# error_validacion = _validar_configuracion(config, nuevo_valor) if error_validacion:\n
# errores.append(f"{categoria}.{clave}:\n {error_validacion}") except Exception as e:\n errores.append(f"Error actualizando
# current_user:\n User, db:\n Session):\n """Registrar operación en auditoría""" \nfrom app.core.constants \nimport
# TipoAccion \nfrom app.models.auditoria \nimport Auditoria auditoria = Auditoria.registrar( usuario_id=current_user.id,
# accion=TipoAccion.ACTUALIZACION, entidad="configuracion_sistema", entidad_id=None, detalles=f"Actualizadas {len
# actualizar_configuracion_sistema( configuraciones:\n Dict[str, Dict[str, Any]], db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ ✏️ Actualizar configuraciones del sistema (VERSIÓN REFACTORIZADA)
# Formato:\n { "AI":\n { "OPENAI_API_KEY":\n "sk-...", "AI_SCORING_ENABLED":\n true }, "EMAIL":\n { "SMTP_HOST":\n
# "smtp.gmail.com", "SMTP_USERNAME":\n "empresa@gmail.com" } } """ # Solo admin puede actualizar configuración if not
# current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden actualizar
# HTTPException( status_code=500, detail=f"Error actualizando configuraciones:\n {str(e)}",
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 🧪 Probar integración de una categoría específica
# """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden probar
# integraciones", ) try:\n categoria = categoria.upper() if categoria == "EMAIL":\n return _probar_configuracion_email(db)
# elif categoria == "WHATSAPP":\n return _probar_configuracion_whatsapp(db) elif categoria == "AI":\n return
# _probar_configuracion_ai(db) elif categoria == "DATABASE":\n return _probar_configuracion_database(db) else:\n raise
# HTTPException( status_code=400, detail=f"Categoría '{categoria}' no soporta pruebas automáticas", ) except HTTPException:\n
# raise except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error probando integración:\n {str(e)}"
# ConfigHelper.get_config(db, "AI", "OPENAI_API_KEY") ), "estado":\n ( "✅ ACTIVO" if ConfigHelper.is_ai_enabled(db) else "❌
# INACTIVO" ), }, "email":\n { "habilitado":\n True, # Siempre habilitado "configurado":\n
# ConfigHelper.is_email_configured(db), "estado":\n ( "✅ CONFIGURADO" if ConfigHelper.is_email_configured(db) else "⚠️
# PENDIENTE" ), }, "whatsapp":\n { "habilitado":\n ConfigHelper.is_whatsapp_enabled(db), "configurado":\n bool(
# ConfigHelper.get_config( db, "WHATSAPP", "META_ACCESS_TOKEN" ) ), "estado":\n ( "✅ ACTIVO" if
# ConfigHelper.is_whatsapp_enabled(db) else "❌ INACTIVO" ), "provider":\n "META_CLOUD_API", }, "database":\n {
# "habilitado":\n True, "configurado":\n True, "estado":\n "✅ CONECTADA", }, "monitoreo":\n { "habilitado":\n bool(
# ConfigHelper.get_config(db, "MONITOREO", "SENTRY_DSN") ), "configurado":\n bool( ConfigHelper.get_config(db, "MONITOREO",
# "SENTRY_DSN") ), "estado":\n ( "✅ ACTIVO" if ConfigHelper.get_config(db, "MONITOREO", "SENTRY_DSN") else "❌ INACTIVO" ), },
# current_user:\n User = Depends(get_current_user),):\n """ 🔧 Inicializar configuraciones por defecto del sistema """ if not
# current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden inicializar
# configuraciones", ) try:\n \nfrom app.models.configuracion_sistema \nimport ConfiguracionPorDefecto # Crear configuraciones
# por defecto ConfiguracionPorDefecto.crear_configuraciones_default(db) # Contar configuraciones creadas total_configs =
# "total_configuraciones":\n total_configs, "categorias_creadas":\n [ "AI - Inteligencia Artificial", "EMAIL - Configuración
# "NOTIFICACIONES - Configuración de notificaciones", "SEGURIDAD - Configuración de seguridad", "DATABASE - Configuración de
# observabilidad", "APLICACION - Configuración general", ], "siguiente_paso":\n "Configurar cada categoría según las
# status_code=500, detail=f"Error inicializando configuraciones:\n {str(e)}", )#
# ============================================# CONFIGURACIÓN DE IA#
# ============================================@router.get("/ia")\ndef obtener_configuracion_ia( db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 🤖 Obtener configuración de Inteligencia
# Artificial """ try:\n # Solo admin puede ver configuración de IA if not current_user.is_admin:\n raise HTTPException(
# status_code=403, detail="Solo administradores pueden ver configuración de IA", ) configs_ia = (
# db.query(ConfiguracionSistema) .filter( ConfiguracionSistema.categoria == "AI", ConfiguracionSistema.visible_frontend, )
# - 4)}{config.valor[-4:\n]}" if len(config.valor) > 4 else "****" ) configuracion[config.clave] = { "valor":\n
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
# el dashboard", } except Exception as e:\n db.rollback() raise HTTPException( status_code=500, detail=f"Error actualizando
# configuración IA:\n {str(e)}", )# ============================================# CONFIGURACIÓN DE EMAIL#
# ============================================@router.get("/email")\ndef obtener_configuracion_email( db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📧 Obtener configuración de email """ try:\n #
# Solo admin puede ver configuración de email if not current_user.is_admin:\n raise HTTPException( status_code=403,
# detail="Solo administradores pueden ver configuración de email", ) configs_email = ( db.query(ConfiguracionSistema)
# "descripcion":\n config.descripcion, "tipo_dato":\n config.tipo_dato, "requerido":\n config.requerido, "configurado":\n
# bool(config.valor), } return { "titulo":\n "📧 CONFIGURACIÓN DE EMAIL", "configuracion":\n configuracion,
# "smtp-mail.outlook.com", "smtp_port":\n 587, "requiere_app_password":\n False, "instrucciones":\n "Usar credenciales
# "instrucciones":\n "Generar App Password en configuración", }, }, "templates_disponibles":\n [ "Recordatorio de pago",
# Exception as e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo configuración email:\n {str(e)}",
# Optional[int] = None, smtp_username:\n Optional[str] = None, smtp_password:\n Optional[str] = None, from_name:\n
# Optional[str] = None, templates_enabled:\n Optional[bool] = None, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 📧 Actualizar configuración de email """ if not current_user.is_admin:\n raise
# HTTPException( status_code=403, detail="Solo administradores pueden configurar email", ) try:\n actualizaciones = [] #
# smtp_username, "SMTP_PASSWORD":\n smtp_password, "EMAIL_FROM_NAME":\n from_name, "EMAIL_TEMPLATES_ENABLED":\n
# ConfiguracionSistema.obtener_por_clave( db, "EMAIL", clave ) if config:\n config.actualizar_valor(valor,
# current_user.full_name) actualizaciones.append(clave) db.commit() return { "mensaje":\n "✅ Configuración de email
# "siguiente_paso":\n "Probar envío de email de prueba", } except Exception as e:\n db.rollback() raise HTTPException(
# status_code=500, detail=f"Error actualizando configuración email:\n {str(e)}", )#
# ============================================# CONFIGURACIÓN DE WHATSAPP#
# ============================================@router.get("/whatsapp")\ndef obtener_configuracion_whatsapp( db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📱 Obtener configuración de WhatsApp """ try:\n #
# Solo admin puede ver configuración de WhatsApp if not current_user.is_admin:\n raise HTTPException( status_code=403,
# detail="Solo administradores pueden ver configuración de WhatsApp", ) configs_whatsapp = ( db.query(ConfiguracionSistema)
# .filter(ConfiguracionSistema.categoria == "WHATSAPP") .all() ) configuracion = {} for config in configs_whatsapp:\n
# "descripcion":\n config.descripcion, "tipo_dato":\n config.tipo_dato, "requerido":\n config.requerido, "configurado":\n
# bool(config.valor), } return { "titulo":\n "📱 CONFIGURACIÓN DE WHATSAPP", "configuracion":\n configuracion, "proveedor":\n
# { "nombre":\n "Twilio", "descripcion":\n "Proveedor de WhatsApp Business API", "registro":\n
# except Exception as e:\n raise HTTPException( status_code=500, detail="Error obteniendo configuración WhatsApp:\n
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
# total_configs, "configuradas":\n configs_configuradas, "porcentaje_configurado":\n ( round(configs_configuradas /
# total_configs * 100, 1) if total_configs > 0 else 0 ), "configuraciones_requeridas":\n configs_requeridas,
# "requeridas_configuradas":\n configs_requeridas_configuradas, "sistema_listo":\n configs_requeridas_configuradas ==
# "descripcion":\n "Sistema de autenticación JWT", }, "email":\n { "estado":\n ( "✅ CONFIGURADO" if
# ConfigHelper.is_email_configured(db) else "⚠️ PENDIENTE" ), "descripcion":\n "Servicio de email", }, "ia":\n { "estado":\n
# ( "✅ ACTIVA" if ConfigHelper.is_ai_enabled(db) else "❌ INACTIVA" ), "descripcion":\n "Inteligencia Artificial", },
# "whatsapp":\n { "estado":\n ( "✅ ACTIVO" if ConfigHelper.is_whatsapp_enabled(db) else "❌ INACTIVO" ), "descripcion":\n
# "WhatsApp Business", }, }, "acciones_rapidas":\n { "configurar_ia":\n "POST /api/v1/configuracion/ia/actualizar",
# "configurar_email":\n "POST /api/v1/configuracion/email/actualizar", "configurar_whatsapp":\n "POST
# /api/v1/configuracion/sistema/probar-integracion/ \ {categoria}" ), "inicializar_defaults":\n "POST
# /api/v1/configuracion/sistema/inicializar-defaults", }, "alertas_configuracion":\n _generar_alertas_configuracion( db,
# estado_categorias ), } except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error en dashboard de
# configuración:\n {str(e)}", )# Schemas\nclass ConfiguracionTasas(BaseModel):\n tasa_interes_base:\n Decimal = Field( ...,
# ge=0, le=100, description="Tasa de interés base anual (%)" ) tasa_mora:\n Decimal = Field( ..., ge=0, le=10,
# description="Tasa de mora mensual (%)" ) tasa_descuento_pronto_pago:\n Optional[Decimal] = Field(None, ge=0, le=10)\nclass
# ConfiguracionLimites(BaseModel):\n monto_minimo_prestamo:\n Decimal = Field(..., gt=0) monto_maximo_prestamo:\n Decimal =
# Field(..., gt=0) plazo_minimo_meses:\n int = Field(..., ge=1) plazo_maximo_meses:\n int = Field(..., le=360)
# email_notificaciones:\n bool = True whatsapp_notificaciones:\n bool = False sms_notificaciones:\n bool = False\nclass
# ConfiguracionGeneral(BaseModel):\n nombre_empresa:\n str ruc:\n str direccion:\n str telefono:\n str email:\n str
# horario_atencion:\n str zona_horaria:\n str = "America/Caracas" formato_fecha:\n str = "DD/MM/YYYY" idioma:\n str = "ES"
# moneda:\n str = "VES" version_sistema:\n str = "1.0.0"# Almacenamiento temporal de configuraciones (en producción usar
# Redis o DB)_config_cache:\n Dict[str, Any] = { "tasas":\n { "tasa_interes_base":\n 15.0, "tasa_mora":\n 2.0,
# "tasa_descuento_pronto_pago":\n 1.0, }, "limites":\n { "monto_minimo_prestamo":\n 100.0, "monto_maximo_prestamo":\n
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
# _config_cache["tasas"], }@router.get("/limites")\ndef obtener_configuracion_limites( current_user:\n User =
# _config_cache["limites"]@router.put("/limites")\ndef actualizar_configuracion_limites( config:\n ConfiguracionLimites,
# current_user:\n User = Depends(get_current_user),):\n """ Actualizar configuración de límites. Solo accesible para ADMIN.
# """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden modificar
# límites", ) # Validar que máximo > mínimo if config.monto_maximo_prestamo <= config.monto_minimo_prestamo:\n raise
# HTTPException( status_code=400, detail="El monto máximo debe ser mayor al monto mínimo", ) if config.plazo_maximo_meses <=
# config.plazo_minimo_meses:\n raise HTTPException( status_code=400, detail="El plazo máximo debe ser mayor al plazo mínimo",
# ) _config_cache["limites"] = { "monto_minimo_prestamo":\n float(config.monto_minimo_prestamo), "monto_maximo_prestamo":\n
# float(config.monto_maximo_prestamo), "plazo_minimo_meses":\n config.plazo_minimo_meses, "plazo_maximo_meses":\n
# obtener_configuracion_notificaciones( current_user:\n User = Depends(get_current_user),):\n """ Obtener configuración de
# notificaciones. """ return _config_cache["notificaciones"]@router.put("/notificaciones")\ndef
# actualizar_configuracion_notificaciones( config:\n ConfiguracionNotificaciones, current_user:\n User =
# Depends(get_current_user),):\n """ Actualizar configuración de notificaciones. Solo accesible para ADMIN y GERENTE. """ if
# config.dias_mora_alerta, "email_notificaciones":\n config.email_notificaciones, "whatsapp_notificaciones":\n
# config.whatsapp_notificaciones, "sms_notificaciones":\n config.sms_notificaciones, } logger.info(f"Notificaciones
# "notificaciones":\n _config_cache["notificaciones"], }@router.put("/general")\ndef actualizar_configuracion_general(
# config:\n ConfiguracionGeneral, current_user:\n User = Depends(get_current_user),):\n """ Actualizar configuración general.
# Solo accesible para ADMIN. """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo
# administradores pueden modificar configuración general", ) _config_cache["general"] = { "nombre_empresa":\n
# config.nombre_empresa, "ruc":\n config.ruc, "direccion":\n config.direccion, "telefono":\n config.telefono, "email":\n
# config.email, "horario_atencion":\n config.horario_atencion, "zona_horaria":\n config.zona_horaria, }
# logger.info(f"Configuración general actualizada por {current_user.email}") return { "mensaje":\n "Configuración general
# obtener_configuracion_cache( current_user:\n User = Depends(get_current_user),):\n """ Obtener toda la configuración del
# sistema desde caché. """ return { "tasas":\n _config_cache["tasas"], "limites":\n _config_cache["limites"],
# "notificaciones":\n _config_cache["notificaciones"], "general":\n _config_cache["general"],
# general, todo current_user:\n User = Depends(get_current_user),):\n """ Restablecer configuración a valores por defecto.
# Solo accesible para ADMIN. """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo
# administradores pueden restablecer configuración", ) defaults = { "tasas":\n { "tasa_interes_base":\n 15.0, "tasa_mora":\n
# 2.0, "tasa_descuento_pronto_pago":\n 1.0, }, "limites":\n { "monto_minimo_prestamo":\n 100.0, "monto_maximo_prestamo":\n
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
# " f"${limites['monto_minimo_prestamo']:\n,.2f} - " f"${limites['monto_maximo_prestamo']:\n,.2f}" ), ) if ( plazo_meses <
# limites["plazo_minimo_meses"] or plazo_meses > limites["plazo_maximo_meses"] ):\n raise HTTPException( status_code=400,
# meses" ), ) # Cálculo de cuota (método francés) tasa_mensual = (tasa / 100) / 12 if tasa_mensual == 0:\n cuota = monto /
# plazo_meses else:\n cuota = ( monto * (tasa_mensual * (1 + tasa_mensual) ** plazo_meses) / ((1 + tasa_mensual) **
# plazo_meses - 1) ) total_pagar = cuota * plazo_meses total_interes = total_pagar - monto return { "monto_solicitado":\n
# monto, "plazo_meses":\n plazo_meses, "tasa_interes_anual":\n tasa, "cuota_mensual":\n round(cuota, 2), "total_pagar":\n
# round(total_pagar, 2), "total_interes":\n round(total_interes, 2), "relacion_cuota_ingreso_sugerida":\n "< 40%",
# }@router.get("/validar-limites/{cliente_id}")\ndef validar_limites_cliente( cliente_id:\n int, monto_solicitado:\n float,
# db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n try:\n # Solo admin puede validar
# límites if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden validar
# False validaciones["mensajes"].append( f"Monto mínimo permitido:\n ${limites_monto['monto_minimo_prestamo']:\n,.2f}" ) if
# monto_solicitado > limites_monto["monto_maximo_prestamo"]:\n validaciones["puede_solicitar"] = False
# validaciones["mensajes"].append( f"Monto máximo permitido:\n ${limites_monto['monto_maximo_prestamo']:\n,.2f}" ) return {
# "monto_solicitado":\n monto_solicitado, **validaciones, } except Exception as e:\n raise HTTPException( status_code=500,
# detail=f"Error validando límites:\n {str(e)}" )# ============================================# FUNCIONES AUXILIARES#
# ============================================\ndef _validar_configuracion(config, nuevo_valor):\n """Validar nuevo valor de
# configuración""" try:\n if config.tipo_dato == "INTEGER":\n int(nuevo_valor) elif config.tipo_dato == "DECIMAL":\n
# Decimal(str(nuevo_valor)) elif config.tipo_dato == "BOOLEAN":\n if nuevo_valor.lower() not in ["true", "false", "1",
# "0"]:\n return "Valor booleano inválido" elif config.tipo_dato == "EMAIL":\n if "@" not in str(nuevo_valor):\n return
# "Formato de email inválido" return None except Exception as e:\n return f"Error de validación:\n {str(e)}"\ndef
# _probar_configuracion_email(db):\n """Probar configuración de email""" return { "estado":\n "OK", "mensaje":\n
# _probar_configuracion_whatsapp(db):\n """Probar configuración de WhatsApp""" return { "estado":\n "OK", "mensaje":\n
# _probar_configuracion_ai(db):\n """Probar configuración de IA""" return { "estado":\n "OK", "mensaje":\n "Configuración de
# {servicio}", "accion":\n f"Revisar configuración de {servicio}", } ) return recomendaciones\ndef
# _generar_alertas_configuracion(db, estado_categorias):\n """Generar alertas de configuración""" alertas = [] for categoria,
# estado in estado_categorias.items():\n if estado["porcentaje_configurado"] < 80:\n alertas.append( { "tipo":\n
# "CONFIGURACION_INCOMPLETA", "categoria":\n categoria, "severidad":\n "MEDIA", "mensaje":\n "Configuración incompleta en
# {categoria}", "porcentaje":\n estado["porcentaje_configurado"], } ) return alertas
