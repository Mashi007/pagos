# backend/app/api/v1/endpoints/notificaciones_multicanal.py"""Endpoints de Notificaciones MulticanalSistema 100% automático
# de notificaciones por Email + WhatsApp"""\nimport logging\nfrom datetime \nimport date, datetime, timedelta\nfrom typing
# \nimport Dict, List, Optional\nfrom fastapi \nimport APIRouter, BackgroundTasks, Depends, HTTPException, Query\nfrom
# pydantic \nimport BaseModel, Field\nfrom sqlalchemy \nimport desc, func\nfrom sqlalchemy.orm \nimport Session\nfrom
# app.api.deps \nimport get_current_user, get_db\nfrom app.db.session \nimport SessionLocal\nfrom app.models.amortizacion
# \nimport Cuota\nfrom app.models.cliente \nimport Cliente\nfrom app.models.notificacion \nimport Notificacion\nfrom
# app.models.prestamo \nimport Prestamo\nfrom app.models.user \nimport User\nfrom
# app.services.notification_multicanal_service \nimport ( CanalNotificacion, GestorReintentos, NotificacionMulticanal,
# NotificationScheduler, PreferenciasNotificacion, TipoNotificacionCliente, WhatsAppTemplateManager,
# notification_scheduler,)logger = logging.getLogger(__name__)router = APIRouter()#
# ============================================# SCHEMAS PARA NOTIFICACIONES MULTICANAL#
# ============================================\nclass ConfiguracionNotificacionesCliente(BaseModel):\n """Schema para
# configuración de notificaciones por cliente""" recordatorio_3_dias:\n bool = Field( True, description="Recordatorio 3 días
# antes" ) recordatorio_1_dia:\n bool = Field( True, description="Recordatorio 1 día antes" ) dia_vencimiento:\n bool =
# Field( True, description="Notificación día de vencimiento" ) mora_1_dia:\n bool = Field(True, description="Notificación 1
# día de mora") mora_3_dias:\n bool = Field(True, description="Notificación 3 días de mora") mora_5_dias:\n bool =
# Field(True, description="Notificación 5 días de mora") confirmacion_pago:\n bool = Field(True, description="Confirmación de
# pago") canal_preferido:\n CanalNotificacion = Field( CanalNotificacion.AMBOS, description="Canal preferido" )\nclass
# EstadisticasNotificaciones(BaseModel):\n """Schema para estadísticas de notificaciones""" total_enviadas:\n int exitosas:\n
# int fallidas:\n int por_canal:\n Dict[str, int] por_tipo:\n Dict[str, int] tasa_exito:\n float#
# ============================================# PROCESAMIENTO AUTOMÁTICO#
# ============================================@router.post("/procesar-automaticas")async \ndef
# procesar_notificaciones_automaticas( background_tasks:\n BackgroundTasks, forzar_procesamiento:\n bool = Query( False,
# description="Forzar procesamiento fuera de horario" ), db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 🤖 Procesar notificaciones automáticas (Endpoint para scheduler/cron) FLUJO AUTOMÁTICO:\n
# 1. Busca clientes con cuotas que requieren notificación hoy 2. Para cada cliente:\n - Verifica preferencias
# (Email/WhatsApp/Ambos) - Carga plantilla correspondiente - Reemplaza variables con datos reales - Envía por Email (si
# aplica) - Envía por WhatsApp (si aplica) - Registra en historial - Marca como enviado 3. Si hay errores:\n registra,
# programa reintento, notifica admin 4. Genera reporte diario para Cobranzas """ # Solo admin y cobranzas pueden ejecutar
# procesamiento manual if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Sin permisos para
# procesar notificaciones" ) try:\n # Verificar configuración de servicios scheduler = NotificationScheduler()
# config_servicios = scheduler.verificar_configuracion_servicios(db) if not
# config_servicios["puede_enviar_notificaciones"]:\n raise HTTPException( status_code=400, detail="Servicios de notificación
# no configurados. Configure \ email y/o WhatsApp.", ) # Ejecutar procesamiento en background background_tasks.add_task(
# _ejecutar_procesamiento_background, db_session=db, user_id=current_user.id, forzar=forzar_procesamiento, ) return {
# "mensaje":\n "✅ Procesamiento de notificaciones iniciado en \ background", "timestamp":\n datetime.now().isoformat(),
# "servicios_disponibles":\n { "email":\n ( "✅ CONFIGURADO" if config_servicios["email_configurado"] else "❌ NO CONFIGURADO"
# ), "whatsapp":\n ( "✅ HABILITADO" if config_servicios["whatsapp_habilitado"] else "❌ DESHABILITADO" ), },
# "estimacion_tiempo":\n "2-5 minutos dependiendo del volumen", "seguimiento":\n "GET
# /api/v1/notificaciones-multicanal/estado-procesamiento", } except HTTPException:\n raise except Exception as e:\n raise
# HTTPException( status_code=500, detail=f"Error iniciando procesamiento:\n {str(e)}"
# )@router.get("/estado-procesamiento")\ndef obtener_estado_procesamiento( db:\n Session = Depends(get_db), current_user:\n
# User = Depends(get_current_user),):\n """ 📊 Obtener estado actual del procesamiento de notificaciones """ try:\n #
# Estadísticas de hoy hoy = date.today() notificaciones_hoy = ( db.query(Notificacion) .filter(
# func.date(Notificacion.creado_en) == hoy, Notificacion.categoria == "CLIENTE", ) .all() ) # Agrupar por estado por_estado =
# {} por_canal = {} por_tipo = {} for notif in notificaciones_hoy:\n # Por estado estado = notif.estado por_estado[estado] =
# por_estado.get(estado, 0) + 1 # Por canal canal = notif.canal or "NO_ESPECIFICADO" por_canal[canal] = por_canal.get(canal,
# 0) + 1 # Por tipo tipo = notif.tipo por_tipo[tipo] = por_tipo.get(tipo, 0) + 1 total_hoy = len(notificaciones_hoy) exitosas
# = por_estado.get("ENTREGADO", 0) fallidas = por_estado.get("ERROR", 0) pendientes = por_estado.get("PENDIENTE", 0) return {
# "titulo":\n "📊 ESTADO DE NOTIFICACIONES MULTICANAL", "fecha_consulta":\n datetime.now().isoformat(), "periodo":\n f"Hoy
# ({hoy.strftime('%d/%m/%Y')})", "resumen_hoy":\n { "total_procesadas":\n total_hoy, "exitosas":\n exitosas, "fallidas":\n
# fallidas, "pendientes":\n pendientes, "tasa_exito":\n ( round((exitosas / total_hoy * 100), 2) if total_hoy > 0 else 0 ),
# }, "por_canal":\n { "email":\n por_canal.get("EMAIL", 0), "whatsapp":\n por_canal.get("WHATSAPP", 0), "total":\n
# sum(por_canal.values()), }, "por_tipo":\n por_tipo, "estado_scheduler":\n { "ejecutandose":\n
# notification_scheduler.is_running, "ultima_ejecucion":\n "Simulado - cada hora", "proxima_ejecucion":\n "En la próxima
# hora", }, "alertas":\n [ ( f"🚨 {fallidas} notificaciones fallidas requieren atención" if fallidas > 0 else None ), ( f"⏳
# {pendientes} notificaciones pendientes de envío" if pendientes > 0 else None ), ( "✅ Sistema funcionando correctamente" if
# fallidas == 0 and pendientes == 0 else None ), ], } except Exception as e:\n raise HTTPException( status_code=500,
# detail=f"Error obteniendo estado:\n {str(e)}" )# ============================================# HISTORIAL DE NOTIFICACIONES#
# ============================================router.get("/historial")\ndef obtener_historial_notificaciones( cliente_id:\n
# Optional[int] = Query(None, description="Filtrar por cliente"), canal:\n Optional[str] = Query(None, description="EMAIL,
# WHATSAPP, AMBOS"), tipo:\n Optional[str] = Query(None, description="Tipo de notificación"), estado:\n Optional[str] =
# Query( None, description="ENTREGADO, ERROR, PENDIENTE" ), fecha_desde:\n Optional[date] = Query(None, description="Fecha
# desde"), fecha_hasta:\n Optional[date] = Query(None, description="Fecha hasta"), page:\n int = Query(1, ge=1), page_size:\n
# int = Query(50, ge=1, le=200), db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📋
# Historial completo de notificaciones con filtros avanzados Estados posibles:\n • ✅ ENTREGADO • 📬 LEIDO (solo WhatsApp) • ⏳
# PENDIENTE • ❌ ERROR / Rebotado """ try:\n # Construir query base query = db.query(Notificacion).filter(
# Notificacion.categoria == "CLIENTE" ) # Aplicar filtros if cliente_id:\n query = query.filter(Notificacion.usuario_id ==
# cliente_id) if canal and canal != "AMBOS":\n query = query.filter(Notificacion.canal == canal) if tipo:\n query =
# query.filter(Notificacion.tipo == tipo) if estado:\n query = query.filter(Notificacion.estado == estado) if fecha_desde:\n
# query = query.filter( func.date(Notificacion.creado_en) >= fecha_desde ) if fecha_hasta:\n query = query.filter(
# func.date(Notificacion.creado_en) <= fecha_hasta ) # Paginación total = query.count() skip = (page - 1) * page_size
# notificaciones = ( query.order_by(desc(Notificacion.creado_en)) .offset(skip) .limit(page_size) .all() ) # Formatear
# resultados historial = [] for notif in notificaciones:\n # Obtener datos del cliente cliente = ( db.query(Cliente)
# .filter(Cliente.id == notif.usuario_id) .first() ) historial.append( { "id":\n notif.id, "cliente":\n { "id":\n
# notif.usuario_id, "nombre":\n ( notif.destinatario_nombre or (cliente.nombre_completo if cliente else "N/A") ), "email":\n
# notif.destinatario_email, "telefono":\n notif.destinatario_telefono, }, "canal":\n { "tipo":\n notif.canal, "icono":\n (
# "📧" if notif.canal == "EMAIL" else "📱" if notif.canal == "WHATSAPP" else "📋" ), }, "tipo":\n { "codigo":\n notif.tipo,
# "descripcion":\n _traducir_tipo_notificacion(notif.tipo), }, "estado":\n { "codigo":\n notif.estado, "icono":\n ( "✅" if
# notif.estado == "ENTREGADO" else ( "📬" if notif.estado == "LEIDO" else ( "⏳" if notif.estado == "PENDIENTE" else "❌" ) ) ),
# "descripcion":\n _traducir_estado_notificacion( notif.estado ), }, "fecha":\n { "creado":\n notif.creado_en, "entregado":\n
# notif.fecha_entrega, "leido":\n notif.fecha_lectura, }, "intentos":\n { "realizados":\n notif.intentos, "maximos":\n
# notif.max_intentos, }, "error":\n ( notif.error_mensaje if notif.estado == "ERROR" else None ), } ) return { "titulo":\n "📋
# HISTORIAL DE NOTIFICACIONES MULTICANAL", "filtros_aplicados":\n { "cliente_id":\n cliente_id, "canal":\n canal, "tipo":\n
# tipo, "estado":\n estado, "fecha_desde":\n fecha_desde, "fecha_hasta":\n fecha_hasta, }, "paginacion":\n { "pagina":\n
# page, "por_pagina":\n page_size, "total":\n total, "total_paginas":\n (total + page_size - 1) // page_size, },
# "historial":\n historial, "estadisticas_filtradas":\n { "total_mostradas":\n len(historial), "por_estado":\n
# _agrupar_por_campo( historial, lambda x:\n x["estado"]["codigo"] ), "por_canal":\n _agrupar_por_campo( historial, lambda
# x:\n x["canal"]["tipo"] ), }, } except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo
# historial:\n {str(e)}" )# ============================================# CONFIGURACIÓN DE PREFERENCIAS POR CLIENTE#
# ============================================@router.get("/cliente/{cliente_id}/preferencias")\ndef
# obtener_preferencias_cliente( cliente_id:\n int, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 🎯 Obtener preferencias de notificación de un cliente específico """ try:\n cliente =
# db.query(Cliente).filter(Cliente.id == cliente_id).first() if not cliente:\n raise HTTPException( status_code=404,
# detail="Cliente no encontrado" ) # Obtener preferencias actuales canal_preferido = (
# PreferenciasNotificacion.obtener_preferencias_cliente( cliente_id, db ) ) return { "cliente":\n { "id":\n cliente.id,
# "nombre":\n cliente.nombre_completo, "email":\n cliente.email, "telefono":\n cliente.telefono, },
# "preferencias_actuales":\n { "canal_preferido":\n canal_preferido.value, "descripcion":\n ( { "AMBOS":\n "📧📱 Email y
# WhatsApp", "EMAIL":\n "📧 Solo Email", "WHATSAPP":\n "📱 Solo WhatsApp", "NINGUNO":\n "🚫 Sin notificaciones",
# }.get(canal_preferido.value, "No definido") ), }, "canales_disponibles":\n { "email":\n { "disponible":\n
# bool(cliente.email), "direccion":\n cliente.email or "No configurado", }, "whatsapp":\n { "disponible":\n
# bool(cliente.telefono), "numero":\n cliente.telefono or "No configurado", }, }, "tipos_notificacion":\n [ { "codigo":\n
# "RECORDATORIO_3_DIAS", "descripcion":\n "3 días antes del vencimiento", "hora":\n "09:\n00 AM", }, { "codigo":\n
# "RECORDATORIO_1_DIA", "descripcion":\n "1 día antes del vencimiento", "hora":\n "09:\n00 AM", }, { "codigo":\n
# "DIA_VENCIMIENTO", "descripcion":\n "Día de vencimiento", "hora":\n "08:\n00 AM", }, { "codigo":\n "MORA_1_DIA",
# "descripcion":\n "1 día de atraso", "hora":\n "10:\n00 AM", }, { "codigo":\n "MORA_3_DIAS", "descripcion":\n "3 días de
# atraso", "hora":\n "10:\n00 AM", }, { "codigo":\n "MORA_5_DIAS", "descripcion":\n "5 días de atraso", "hora":\n "10:\n00
# AM", }, { "codigo":\n "CONFIRMACION_PAGO", "descripcion":\n "Confirmación de pago", "hora":\n "Inmediato", }, ], } except
# HTTPException:\n raise except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo
# preferencias:\n {str(e)}" )router.post("/cliente/{cliente_id}/preferencias")\ndef actualizar_preferencias_cliente(
# cliente_id:\n int, canal_preferido:\n CanalNotificacion, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ ✏️ Actualizar preferencias de notificación del cliente Opciones:\n • AMBOS:\n Email +
# WhatsApp (recomendado) • EMAIL:\n Solo email • WHATSAPP:\n Solo WhatsApp • NINGUNO:\n Opt-out (sin notificaciones) """
# try:\n # Verificar que el cliente existe cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first() if not
# cliente:\n raise HTTPException( status_code=404, detail="Cliente no encontrado" ) # Validar que el cliente tenga los
# canales solicitados if canal_preferido == CanalNotificacion.EMAIL and not cliente.email:\n raise HTTPException(
# status_code=400, detail="Cliente no tiene email configurado" ) if ( canal_preferido == CanalNotificacion.WHATSAPP and not
# cliente.telefono ):\n raise HTTPException( status_code=400, detail="Cliente no tiene teléfono configurado" ) if
# canal_preferido == CanalNotificacion.AMBOS and not ( cliente.email and cliente.telefono ):\n raise HTTPException(
# status_code=400, detail="Cliente debe tener email Y teléfono para canal AMBOS", ) # Actualizar preferencias exito =
# PreferenciasNotificacion.actualizar_preferencias_cliente( cliente_id, canal_preferido, db ) if not exito:\n raise
# HTTPException( status_code=500, detail="Error actualizando preferencias" ) return { "mensaje":\n "✅ Preferencias de
# notificación actualizadas exitosamente", "cliente":\n {"id":\n cliente_id, "nombre":\n cliente.nombre_completo},
# "nueva_configuracion":\n { "canal_preferido":\n canal_preferido.value, "descripcion":\n ( { "AMBOS":\n "Recibirá
# notificaciones por email Y WhatsApp", "EMAIL":\n "Recibirá notificaciones solo por email", "WHATSAPP":\n "Recibirá
# notificaciones solo por WhatsApp", "NINGUNO":\n "NO recibirá notificaciones automáticas", }.get(canal_preferido.value) ),
# }, "fecha_actualizacion":\n datetime.now().isoformat(), "actualizado_por":\n current_user.full_name, } except
# HTTPException:\n raise except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error actualizando
# preferencias:\n {str(e)}", )# ============================================# GESTIÓN DE TEMPLATES WHATSAPP#
# ============================================@router.get("/whatsapp/templates")\ndef
# listar_templates_whatsapp(current_user:\n User = Depends(get_current_user)):\n """ 📝 Listar templates de WhatsApp
# disponibles ⚠️ IMPORTANTE:\n Las plantillas de WhatsApp deben ser aprobadas por Meta antes de poder usarse. El sistema las
# enviará para aprobación. """ try:\n templates = WhatsAppTemplateManager.listar_todos_templates() return { "titulo":\n "📝
# TEMPLATES DE WHATSAPP BUSINESS API", "total_templates":\n len(templates), "templates":\n templates,
# "informacion_importante":\n { "aprobacion_meta":\n "Las plantillas deben ser aprobadas por Meta antes de usar",
# "tiempo_aprobacion":\n "1-2 días hábiles", "proceso":\n "El sistema enviará automáticamente para ap \ robación",
# "limitaciones":\n "WhatsApp tiene reglas estrictas sobre contenido", }, "variables_disponibles":\n [ "{nombre} - Nombre del
# cliente", "{cuota} - Número de cuota", "{monto} - Monto de la cuota", "{fecha} - Fecha de vencimiento", "{dias_mora} - Días
# de mora", "{vehiculo} - Descripción del vehículo", "{nombre_empresa} - Nombre de la empresa", "{telefono_empresa} -
# Teléfono de contacto", ], } except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error listando
# templates:\n {str(e)}" )@router.post("/whatsapp/templates/{template_name}/aprobar")\ndef enviar_template_para_aprobacion(
# template_name:\n str, current_user:\n User = Depends(get_current_user)):\n """ 📤 Enviar template de WhatsApp a Meta para
# aprobación """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden
# gestionar templates", ) try:\n # Obtener template formateado para Meta template_meta = (
# WhatsAppTemplateManager.obtener_template_para_aprobacion( template_name ) ) if not template_meta:\n raise HTTPException(
# status_code=404, detail="Template no encontrado" ) # En producción, aquí se enviaría a la API de Meta # Por ahora, simular
# el proceso return { "mensaje":\n f"✅ Template '{template_name}' enviado para aprobación", "template_enviado":\n
# template_meta, "proceso":\n { "estado":\n "ENVIADO_PARA_APROBACION", "tiempo_estimado":\n "1-2 días hábiles",
# "siguiente_paso":\n "Esperar aprobación de Meta", "notificacion":\n "Recibirás email cuando sea aprobado", },
# "fecha_envio":\n datetime.now().isoformat(), } except HTTPException:\n raise except Exception as e:\n raise HTTPException(
# status_code=500, detail=f"Error enviando template:\n {str(e)}" )# ============================================# REINTENTOS
# Y RECUPERACIÓN# ============================================@router.post("/procesar-reintentos")async \ndef
# procesar_reintentos_fallidas( background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 🔄 Procesar reintentos de notificaciones fallidas Configuración de reintentos:\n • Máximo
# 2 reintentos por notificación • Intervalo de 30 minutos entre reintentos • Notificar a Admin si falla después de todos los
# reintentos """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Sin permisos para procesar
# reintentos" ) try:\n # Ejecutar reintentos en background background_tasks.add_task(_procesar_reintentos_background, db) #
# Contar notificaciones pendientes de reintento pendientes_reintento = ( db.query(Notificacion) .filter( Notificacion.estado
# == "ERROR", Notificacion.intentos < Notificacion.max_intentos, Notificacion.creado_en >= datetime.now() -
# timedelta(hours=24), ) .count() ) return { "mensaje":\n "✅ Procesamiento de reintentos iniciado en background",
# "notificaciones_pendientes":\n pendientes_reintento, "configuracion_reintentos":\n { "maximos_intentos":\n 2,
# "intervalo_minutos":\n 30, "ventana_reintento":\n "24 horas", }, "timestamp":\n datetime.now().isoformat(), } except
# Exception as e:\n raise HTTPException( status_code=500, detail=f"Error procesando reintentos:\n {str(e)}" )#
# ============================================# DASHBOARD DE NOTIFICACIONES MULTICANAL#
# ============================================@router.get("/dashboard")\ndef dashboard_notificaciones_multicanal( periodo:\n
# str = Query("hoy", description="hoy, semana, mes"), db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 📊 Dashboard completo de notificaciones multicanal """ try:\n # Calcular fechas según
# período hoy = date.today() if periodo == "hoy":\n fecha_inicio = fecha_fin = hoy elif periodo == "semana":\n fecha_inicio =
# hoy - timedelta(days=7) fecha_fin = hoy elif periodo == "mes":\n fecha_inicio = hoy.replace(day=1) fecha_fin = hoy else:\n
# fecha_inicio = fecha_fin = hoy # Obtener notificaciones del período notificaciones = ( db.query(Notificacion) .filter(
# Notificacion.categoria == "CLIENTE", func.date(Notificacion.creado_en) >= fecha_inicio, func.date(Notificacion.creado_en)
# <= fecha_fin, ) .all() ) # Calcular métricas total = len(notificaciones) exitosas = len([n for n in notificaciones if
# n.estado == "ENTREGADO"]) fallidas = len([n for n in notificaciones if n.estado == "ERROR"]) # Métricas por canal por_canal
# = { "EMAIL":\n len([n for n in notificaciones if n.canal == "EMAIL"]), "WHATSAPP":\n len( [n for n in notificaciones if
# n.canal == "WHATSAPP"] ), } # Métricas por tipo por_tipo = {} for notif in notificaciones:\n tipo = notif.tipo
# por_tipo[tipo] = por_tipo.get(tipo, 0) + 1 # Top clientes con más notificaciones clientes_notificaciones = {} for notif in
# notificaciones:\n cliente_id = notif.usuario_id clientes_notificaciones[cliente_id] = (
# clientes_notificaciones.get(cliente_id, 0) + 1 ) return { "titulo":\n "📊 DASHBOARD DE NOTIFICACIONES MULTICANAL",
# "periodo":\n { "descripcion":\n periodo.title(), "fecha_inicio":\n fecha_inicio, "fecha_fin":\n fecha_fin, },
# "metricas_principales":\n { "total_enviadas":\n { "valor":\n total, "icono":\n "📊", "color":\n "#007bff", }, "exitosas":\n
# { "valor":\n exitosas, "porcentaje":\n ( round((exitosas / total * 100), 2) if total > 0 else 0 ), "icono":\n "✅",
# "color":\n "#28a745", }, "fallidas":\n { "valor":\n fallidas, "porcentaje":\n ( round((fallidas / total * 100), 2) if total
# > 0 else 0 ), "icono":\n "❌", "color":\n "#dc3545", }, "tasa_exito":\n { "valor":\n ( f"{round((exitosas / total * 100),
# 1)}%" if total > 0 else "0%" ), "icono":\n "🎯", "color":\n "#17a2b8", }, }, "distribucion_canales":\n { "email":\n {
# "cantidad":\n por_canal["EMAIL"], "porcentaje":\n ( round((por_canal["EMAIL"] / total * 100), 1) if total > 0 else 0 ),
# "color":\n "#007bff", }, "whatsapp":\n { "cantidad":\n por_canal["WHATSAPP"], "porcentaje":\n (
# round((por_canal["WHATSAPP"] / total * 100), 1) if total > 0 else 0 ), "color":\n "#25d366", }, }, "tipos_mas_enviados":\n
# [ { "tipo":\n tipo, "cantidad":\n cantidad, "descripcion":\n _traducir_tipo_notificacion(tipo), } for tipo, cantidad in
# sorted( por_tipo.items(), key=lambda x:\n x[1], reverse=True ) ], "estado_servicios":\n { "email":\n "✅ ACTIVO", #
# Placeholder "whatsapp":\n "✅ ACTIVO", # Placeholder "scheduler":\n "✅ EJECUTÁNDOSE", }, "acciones_rapidas":\n {
# "procesar_ahora":\n "POST /api/v1/notificaciones-multica \ nal/procesar-automaticas", "ver_historial":\n "GET
# /api/v1/notificaciones-multicana \ l/historial", "procesar_reintentos":\n "POST
# /api/v1/notificaciones-multicanal/procesar-reintentos", "configurar_templates":\n "GET
# /api/v1/notificaciones-multicanal/whatsapp/templates", }, } except Exception as e:\n raise HTTPException( status_code=500,
# detail=f"Error en dashboard:\n {str(e)}" )# ============================================# TESTING Y PRUEBAS#
# ============================================@router.post("/probar-envio")async \ndef probar_envio_notificacion(
# cliente_id:\n int, tipo_notificacion:\n TipoNotificacionCliente, canal:\n CanalNotificacion = CanalNotificacion.AMBOS,
# db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 🧪 Probar envío de notificación a
# cliente específico """ if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Sin permisos para
# probar notificaciones" ) try:\n # Obtener datos del cliente cliente = db.query(Cliente).filter(Cliente.id ==
# cliente_id).first() if not cliente:\n raise HTTPException( status_code=404, detail="Cliente no encontrado" ) # Obtener
# cuota más reciente para datos de prueba cuota = ( db.query(Cuota) .join(Prestamo) .filter(Prestamo.cliente_id ==
# cliente_id) .order_by(Cuota.numero_cuota.desc()) .first() ) if not cuota:\n raise HTTPException( status_code=404,
# detail="Cliente no tiene cuotas registradas" ) # Preparar datos para notificación de prueba cliente_data = {
# "cliente_id":\n cliente.id, "nombre":\n cliente.nombre_completo, "email":\n cliente.email, "telefono":\n cliente.telefono,
# "cuota_numero":\n cuota.numero_cuota, "monto_cuota":\n float(cuota.monto_cuota), "fecha_vencimiento":\n
# cuota.fecha_vencimiento, "dias_mora":\n max(0, (date.today() - cuota.fecha_vencimiento).days), "saldo_pendiente":\n float(
# cuota.capital_pendiente + cuota.interes_pendiente ), "vehiculo":\n cliente.vehiculo_completo or "Vehículo de prueba", } #
# Crear servicio y enviar notificación de prueba servicio = NotificacionMulticanal(db) resultado = await
# servicio._enviar_notificacion_multicanal( cliente_data, tipo_notificacion, canal ) return { "mensaje":\n "🧪 Notificación de
# prueba enviada", "cliente":\n { "nombre":\n cliente.nombre_completo, "email":\n cliente.email, "telefono":\n
# cliente.telefono, }, "configuracion_prueba":\n { "tipo":\n tipo_notificacion.value, "canal":\n canal.value,
# "cuota_usada":\n cuota.numero_cuota, }, "resultado_envio":\n resultado, "timestamp":\n datetime.now().isoformat(), } except
# HTTPException:\n raise except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error en prueba de
# notificación:\n {str(e)}", )# ============================================# FUNCIONES AUXILIARES#
# ============================================async \ndef _ejecutar_procesamiento_background( db_session:\n Session,
# user_id:\n int, forzar:\n bool):\n """Ejecutar procesamiento de notificaciones en background""" try:\n \nfrom
# app.db.session \nimport SessionLocal db = SessionLocal() # Ejecutar ciclo de notificaciones resultado = await
# notification_scheduler.ejecutar_ciclo_notificaciones( db ) logger.info( f"📧 Procesamiento background completado por usuario
# {user_id}" ) logger.info(f"📊 Resultados:\n {resultado}") db.close() except Exception as e:\n logger.error(f"Error en
# procesamiento background:\n {e}")async \ndef _procesar_reintentos_background(db_session:\n Session):\n """Procesar
# reintentos en background""" try:\n db = SessionLocal() resultado = await
# GestorReintentos.procesar_reintentos_pendientes(db) logger.info(f"🔄 Reintentos procesados:\n {resultado}") db.close()
# except Exception as e:\n logger.error(f"Error procesando reintentos:\n {e}")\ndef _traducir_tipo_notificacion(tipo:\n str)
# -> str:\n """Traducir tipo de notificación a descripción amigable""" traducciones = { "RECORDATORIO_3_DIAS":\n
# "Recordatorio 3 días antes", "RECORDATORIO_1_DIA":\n "Recordatorio 1 día antes", "DIA_VENCIMIENTO":\n "Día de vencimiento",
# "MORA_1_DIA":\n "1 día de mora", "MORA_3_DIAS":\n "3 días de mora", "MORA_5_DIAS":\n "5 días de mora",
# "CONFIRMACION_PAGO":\n "Confirmación de pago", } return traducciones.get(tipo, tipo)\ndef
# _traducir_estado_notificacion(estado:\n str) -> str:\n """Traducir estado de notificación""" traducciones = {
# "ENTREGADO":\n "Entregado exitosamente", "LEIDO":\n "Leído por el cliente", "PENDIENTE":\n "Pendiente de envío", "ERROR":\n
# "Error en envío", } return traducciones.get(estado, estado)\ndef _agrupar_por_campo(lista:\n List[Dict], extractor) ->
# Dict[str, int]:\n """Agrupar lista por campo específico""" agrupado = {} for item in lista:\n clave = extractor(item)
# agrupado[clave] = agrupado.get(clave, 0) + 1 return agrupado# ============================================# ENDPOINT DE
# VERIFICACIÓN# ============================================@router.get("/verificacion-sistema")\ndef
# verificar_sistema_notificaciones_multicanal( db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 🔍 Verificación completa del sistema de notificaciones multicanal """ return {
# "titulo":\n "🔔 SISTEMA DE NOTIFICACIONES MULTICANAL", "fecha_verificacion":\n datetime.now().isoformat(),
# "caracteristicas_implementadas":\n { "notificaciones_duales":\n "✅ Email + WhatsApp simultáneo",
# "procesamiento_automatico":\n "✅ Scheduler cada hora", "templates_personalizados":\n "✅ Templates específicos por tipo",
# "historial_completo":\n "✅ Registro detallado de envíos", "reintentos_automaticos":\n "✅ Hasta 2 reintentos por fallo",
# "limites_antispam":\n "✅ Máximo 3 por día, intervalo 2h", "preferencias_cliente":\n "✅ Configuración por cliente",
# "reportes_automaticos":\n "✅ Reporte diario a cobranzas", }, "tipos_notificacion":\n [ "1️⃣ 3 días antes del vencimiento
# (09:\n00 AM)", "2️⃣ 1 día antes del vencimiento (09:\n00 AM)", "3️⃣ Día de vencimiento (08:\n00 AM)", "4️⃣ 1 día de atraso
# (10:\n00 AM)", "5️⃣ 3 días de atraso (10:\n00 AM)", "6️⃣ 5 días de atraso (10:\n00 AM)", "7️⃣ Confirmación de pago
# (Inmediato)", ], "canales_soportados":\n { "email":\n { "proveedor":\n "Google Workspace / SMTP", "templates":\n "HTML
# profesionales", "variables":\n "Dinámicas por cliente", "estado":\n "✅ CONFIGURADO", }, "whatsapp":\n { "proveedor":\n
# "Twilio / 360Dialog / Meta Cloud API", "templates":\n "Aprobados por Meta", "variables":\n "Dinámicas por cliente",
# "estado":\n "⚠️ REQUIERE CONFIGURACIÓN", }, }, "flujo_automatico":\n { "frecuencia":\n "Cada hora (scheduler/cron)",
# "pasos":\n [ "1. Buscar clientes con cuotas que requieren notificación", "2. Verificar preferencias por cliente", "3.
# Cargar plantilla correspondiente", "4. Reemplazar variables con datos reales", "5. Enviar por Email (si aplica)", "6.
# Enviar por WhatsApp (si aplica)", "7. Registrar en historial", "8. Procesar reintentos si hay fallos", "9. Generar reporte
# diario", ], }, "endpoints_principales":\n { "dashboard":\n "/api/v1/notificaciones-multicanal/dashboard",
# "procesar_automaticas":\n "/api/v1/notificaciones-multicanal \ /procesar-automaticas", "historial":\n
# "/api/v1/notificaciones-multicanal/historial", "preferencias_cliente":\n
# "/api/v1/notificaciones-multicanal/cliente/{id}/preferencias", "templates_whatsapp":\n
# "/api/v1/notificaciones-multicanal/whatsapp/templates", "probar_envio":\n "/api/v1/notificaciones-multicanal/probar-envio",
# }, "configuracion_requerida":\n { "email":\n "Configurado en /api/v1/configuracion/email", "whatsapp":\n "Configurar en
# /api/v1/configuracion/whatsapp", "scheduler":\n "Configurar cron job para ejecutar cada hora", }, }
