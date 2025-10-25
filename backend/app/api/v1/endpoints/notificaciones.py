# backend/app/api/v1/endpoints/notificaciones.py"""Endpoint para gestión de notificaciones del sistema.Soporta Email y
# Decimal\nfrom typing \nimport Optional\nfrom fastapi \nimport APIRouter, BackgroundTasks, Depends, HTTPException,
# Query\nfrom pydantic \nimport BaseModel\nfrom sqlalchemy \nimport and_, func\nfrom sqlalchemy.orm \nimport Session\nfrom
# app.api.deps \nimport get_current_user, get_db\nfrom app.core.config \nimport settings\nfrom app.models.amortizacion
# \nimport Cuota\nfrom app.models.analista \nimport Analista\nfrom app.models.cliente \nimport Cliente\nfrom
# app.models.notificacion \nimport Notificacion\nfrom app.models.pago \nimport Pago\nfrom app.models.prestamo \nimport
# EmailService\nfrom app.services.whatsapp_service \nimport WhatsAppServicelogger = logging.getLogger(__name__)router =
# APIRouter()# Schemas\nclass NotificacionCreate(BaseModel):\n cliente_id:\n int tipo:\n str canal:\n str # EMAIL, WHATSAPP,
# Optional[str] = None # MOROSO, ACTIVO, etc. dias_mora_min:\n Optional[int] = None template:\n str canal:\n str = "EMAIL"#
# response_model=NotificacionResponse)async \ndef enviar_notificacion( notificacion:\n NotificacionCreate,
# background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db),):\n """ Enviar notificación individual. """ # Obtener
# cliente cliente = ( db.query(Cliente).filter(Cliente.id == notificacion.cliente_id).first() ) if not cliente:\n raise
# HTTPException(status_code=404, detail="Cliente no encontrado") # Crear registro de notificación nueva_notif = Notificacion(
# cliente_id=notificacion.cliente_id, tipo=notificacion.canal, # EMAIL, WHATSAPP, SMS categoria="RECORDATORIO_PAGO",
# asunto=notificacion.asunto, mensaje=notificacion.mensaje, estado="PENDIENTE", programada_para=notificacion.programada_para
# == "EMAIL":\n background_tasks.add_task( email_service.send_email, to_email=cliente.email, subject=notificacion.asunto,
# body=notificacion.mensaje, notificacion_id=nueva_notif.id, ) elif notificacion.canal == "WHATSAPP":\n
# background_tasks.add_task( whatsapp_service.send_message, to_number=cliente.telefono, message=notificacion.mensaje,
# notificacion_id=nueva_notif.id, ) logger.info( f"Notificación {nueva_notif.id} programada" + f"para envío por \
# EnvioMasivoRequest, background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db),):\n """ Envío masivo de
# request.tipo_cliente == "MOROSO":\n query = query.filter(Prestamo.dias_mora > 0) if request.dias_mora_min:\n query =
# query.filter(Prestamo.dias_mora >= request.dias_mora_min) clientes = query.all() # Crear notificaciones masivas
# notificaciones_creadas = [] for cliente in clientes:\n # Personalizar mensaje según template mensaje =
# _generar_mensaje_template( template=request.template, cliente=cliente, db=db ) notif = Notificacion( cliente_id=cliente.id,
# tipo=request.canal, categoria="RECORDATORIO_PAGO", asunto=f"Recordatorio de Pago - {cliente.nombres}", mensaje=mensaje,
# notif.cliente_id).first() ) if request.canal == "EMAIL" and cliente.email:\n background_tasks.add_task(
# email_service.send_email, to_email=cliente.email, subject=notif.asunto, body=notif.mensaje, notificacion_id=notif.id, )
# elif request.canal == "WHATSAPP" and cliente.telefono:\n background_tasks.add_task( whatsapp_service.send_message,
# len(notificaciones_creadas), "canal":\n request.canal, "ids":\n [n.id for n in notificaciones_creadas],
# }@router.get("/historial/{cliente_id}")\ndef historial_notificaciones(cliente_id:\n int, db:\n Session =
# Depends(get_db)):\n """ Obtener historial de notificaciones de un cliente. """ notificaciones = ( db.query(Notificacion)
# .filter(Notificacion.cliente_id == cliente_id) .order_by(Notificacion.creado_en.desc()) .all() ) return { "cliente_id":\n
# cliente_id, "total":\n len(notificaciones), "notificaciones":\n [ { "id":\n n.id, "tipo":\n n.tipo, "categoria":\n
# n.categoria, "asunto":\n n.asunto, "estado":\n n.estado, "enviada_en":\n n.enviada_en, "creado_en":\n n.creado_en, } for n
# in notificaciones ], }@router.get("/pendientes")\ndef notificaciones_pendientes(db:\n Session = Depends(get_db)):\n """
# Obtener notificaciones pendientes de envío. """ pendientes = ( db.query(Notificacion) .filter( Notificacion.estado ==
# "notificaciones":\n [ { "id":\n n.id, "cliente_id":\n n.cliente_id, "tipo":\n n.tipo, "categoria":\n n.categoria,
# Prestamo.fecha_vencimiento <= fecha_limite, Prestamo.fecha_vencimiento >= date.today(), Prestamo.estado == "ACTIVO", )
# tipo="EMAIL", categoria="RECORDATORIO_PAGO", asunto="Recordatorio:\n Cuota próxima a vencer", mensaje=mensaje,
# cliente.email:\n background_tasks.add_task( email_service.send_email, to_email=cliente.email, subject=notif.asunto,
# _generar_mensaje_template( template:\n str, cliente:\n Cliente, db:\n Session) -> str:\n """ Generar mensaje personalizado
# "Mensaje genérico de notificación."# ============================================# NOTIFICACIONES AUTOMÁTICAS PROGRAMADAS#
# programar_notificaciones_automaticas( background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db)):\n """
# Programar todas las notificaciones automáticas del sistema Debe ejecutarse diariamente via cron job """
# notificaciones_programadas = [] # 1. RECORDATORIOS PRE-VENCIMIENTO (3 días antes) fecha_recordatorio = date.today() +
# fecha_recordatorio, Cuota.estado.in_(["PENDIENTE", "PARCIAL"]), Cliente.email.isnot(None), Cliente.activo, ) .all() ) for
# cuota in cuotas_proximas:\n cliente = cuota.prestamo.cliente # Verificar que no se haya enviado ya ya_enviado = (
# db.query(Notificacion) .filter( Notificacion.cliente_id == cliente.id, Notificacion.categoria == "CUOTA_PROXIMA",
# func.date(Notificacion.creado_en) == date.today(), ) .first() ) if not ya_enviado:\n mensaje = """Estimado/a
# 123-456Email:\n cobranzas@financiera.comGracias por su puntualidad. """ notif = Notificacion( cliente_id=cliente.id,
# tipo="EMAIL", categoria="CUOTA_PROXIMA", asunto=f"Recordatorio:\n Cuota #{cuota.numero_cuota} vence \ en 3 días",
# prioridad="ALTA", ) db.add(notif) notificaciones_programadas.append(notif) # 2. AVISOS DE CUOTA VENCIDA (día siguiente)
# cuotas_vencidas_ayer = ( db.query(Cuota) .join(Prestamo) .join(Cliente) .filter( Cuota.fecha_vencimiento == date.today() -
# cuota in cuotas_vencidas_ayer:\n cliente = cuota.prestamo.cliente # Calcular mora mora_calculada = cuota.calcular_mora(
# Decimal(str(settings.TASA_MORA_DIARIA)) ) mensaje = f"""Estimado/a {cliente.nombre_completo},ALERTA:\n Su cuota
# {(date.today() - cuota.fecha_vencimiento).days} Monto adeudado:\n {float(cuota.monto_pendiente_total):\n,.2f} Recargo por
# mora:\n {float(mora_calculada):\n,.2f}URGENTE:\n Regularice su pago inmediatamente para evitar:\n Incremento de mora diaria
# Reporte en centrales de riesgo Acciones legalesContacto inmediato:\n (021) 123-456 """ notif = Notificacion(
# cliente_id=cliente.id, tipo="EMAIL", categoria="CUOTA_VENCIDA", asunto=f"🔴 URGENTE:\n Cuota #{cuota.numero_cuota} VENCIDA",
# = ( db.query(Cliente).filter(Cliente.id == notif.cliente_id).first() ) if cliente.email:\n background_tasks.add_task(
# email_service.send_template_email, to_email=cliente.email, subject=notif.asunto, template_name=( "recordatorio_pago" if
# "recordatorio" in notif.asunto.lower() else "mora" ), context={ "cliente_nombre":\n cliente.nombre_completo, "empresa":\n
# "Financiera Automotriz", "telefono":\n "(021) 123-456", "email":\n "info@financiera.com", }, notificacion_id=notif.id, )
# \ndef enviar_confirmacion_pago( pago_id:\n int, background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db),):\n
# db.query(Pago) .select_from(Pago) .join(Prestamo, Pago.prestamo_id == Prestamo.id) .join(Cliente, Prestamo.cliente_id ==
# Cliente.id) .filter(Pago.id == pago_id) .first() ) if not pago:\n raise HTTPException(status_code=404, detail="Pago no
# encontrado") cliente = pago.prestamo.cliente # Calcular próximo vencimiento proxima_cuota = ( db.query(Cuota) .filter(
# Cuota.prestamo_id == pago.prestamo_id, Cuota.estado.in_(["PENDIENTE", "PARCIAL"]), ) .order_by(Cuota.numero_cuota) .first()
# ) proximo_vencimiento = "No hay cuotas pendientes" if proxima_cuota:\n proximo_vencimiento = "Cuota
# {cliente.nombre_completo},Gracias por su pago!CONFIRMACIÓN DE PAGO RECIBIDO:\n Fecha:\n
# Método:\n {pago.metodo_pago} Referencia:\n {pago.numero_operacion or pago.comprobante or 'N/A'}DETALLE DE APLICACIÓN:\n
# Capital:\n {float(pago.monto_capital):\n.2f} Interés:\n {float(pago.monto_interes):\n.2f} Mora:\n
# {float(pago.monto_mora):\n.2f}ESTADO ACTUAL:\n Saldo pendiente:\n {float(pago.prestamo.saldo_pendiente):\n.2f} Próximo
# cliente_id=cliente.id, tipo="EMAIL", categoria="PAGO_RECIBIDO", asunto=f"✅ Confirmación:\n Pago de {float
# prioridad="NORMAL", ) db.add(notif) db.commit() db.refresh(notif) # Enviar inmediatamente if cliente.email:\n
# background_tasks.add_task( email_service.send_email, to_email=cliente.email, subject=notif.asunto, body=notif.mensaje,
# notificacion_id=notif.id, ) return { "message":\n "Confirmación de pago programada", "notificacion_id":\n notif.id,
# background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db)):\n """ 4. Estado de cuenta mensual (primer día de
# Pago.prestamo_id == Prestamo.id) .filter( Prestamo.cliente_id == cliente.id, Pago.fecha_pago >= inicio_mes, Pago.fecha_pago
# .join(Prestamo, Cuota.prestamo_id == Prestamo.id) .filter( Prestamo.cliente_id == cliente.id,
# Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]), ) .order_by(Cuota.fecha_vencimiento) .limit(3) .all() ) # Resumen
# financiero resumen = cliente.calcular_resumen_financiero(db) mensaje = f"""Estimado/a {cliente.nombre_completo},ESTADO DE
# {float(resumen['total_financiado']):\n.2f} Total pagado:\n {float(resumen['total_pagado']):\n.2f} Saldo pendiente:\n
# {float(resumen['saldo_pendiente']):\n.2f} Cuotas pagadas:\n {resumen['cuotas_pagadas']} / {resumen['cuotas_totales']} %
# Avance:\n {resumen['porcentaje_avance']}%PRÓXIMOS VENCIMIENTOS:\n""" for cuota in cuotas_pendientes:\n mensaje += ( f"•
# db.query(Cliente).filter(Cliente.id == notif.cliente_id).first() ) background_tasks.add_task( email_service.send_email,
# to_email=cliente.email, subject=notif.asunto, body=notif.mensaje, notificacion_id=notif.id, ) return {
# ============================================# NOTIFICACIONES A USUARIOS DEL SISTEMA#
# db.add(notif) # Enviar background_tasks.add_task( email_service.send_email, to_email=usuario.email, subject=notif.asunto,
# la cartera - Top performers y alertas """ # Calcular semana anterior (lunes a domingo) hoy = date.today() inicio_semana =
# func.date(Cliente.fecha_registro) >= inicio_semana, func.date(Cliente.fecha_registro) <= fin_semana, ) .all() ) # Top
# .outerjoin( Cliente, and_( Analista.id == Cliente.analista_id, func.date(Cliente.fecha_registro) >= inicio_semana,
# func.date(Cliente.fecha_registro) <= fin_semana, ), ) .filter( User.is_admin, ) .group_by(User.id, User.full_name)
# (Cliente).filter(Cliente.dias_mora > 0).count() / db.query(Cliente).filter(Cliente.activo).count() * 100:\n.2f}%Revisar
# db.add(notif) background_tasks.add_task( email_service.send_email, to_email=usuario.email, subject=notif.asunto,
# ============================================@router.get("/configuracion")\ndef obtener_configuracion_notificaciones( db:\n
# Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ ⚙️ Obtener configuración de
# "09:\n00", "resumen_diario":\n "08:\n00", "reporte_semanal":\n "09:\n00", # Lunes "reporte_mensual":\n "10:\n00", # Día 1
# settings.SMTP_PORT, "habilitado":\n settings.EMAIL_ENABLED, "from_name":\n settings.FROM_NAME, },
# }@router.get("/historial-completo")\ndef historial_completo_notificaciones( fecha_desde:\n Optional[date] = Query(None),
# fecha_hasta:\n Optional[date] = Query(None), tipo:\n Optional[str] = Query(None), estado:\n Optional[str] = Query(None),
# cliente_id:\n Optional[int] = Query(None), page:\n int = Query(1, ge=1), page_size:\n int = Query(20, ge=1, le=1000), db:\n
# Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📋 Historial completo de notificaciones
# fecha_desde:\n query = query.filter(func.date(Notificacion.creado_en) >= fecha_desde) if fecha_hasta:\n query =
# query.filter(func.date(Notificacion.creado_en) <= fecha_hasta) if tipo:\n query = query.filter(Notificacion.tipo == tipo)
# if estado:\n query = query.filter(Notificacion.estado == estado) if cliente_id:\n query =
# query.filter(Notificacion.cliente_id == cliente_id) # Paginación total = query.count() skip = (page - 1) * page_size
# notificaciones = ( query.order_by(Notificacion.creado_en.desc()) .offset(skip) .limit(page_size) .all() ) return {
# "total":\n total, "page":\n page, "page_size":\n page_size, "total_pages":\n (total + page_size - 1) // page_size,
# "notificaciones":\n [ { "id":\n n.id, "destinatario":\n ( n.cliente.nombre_completo if n.cliente else (n.user.full_name if
# n.user else "N/A") ), "tipo":\n n.tipo.value, "categoria":\n n.categoria.value, "asunto":\n n.asunto, "estado":\n
# n.error_mensaje, "puede_reenviar":\n n.puede_reintentar, } for n in notificaciones ], "estadisticas":\n {
# "total_enviadas":\n ( db.query(Notificacion) .filter(Notificacion.estado == "ENVIADA") .count() ), "total_fallidas":\n (
# db.query(Notificacion) .filter(Notificacion.estado == "FALLIDA") .count() ), "total_pendientes":\n ( db.query(Notificacion)
# reenviar_notificacion( notificacion_id:\n int, background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ Reenvío manual de notificación fallida """ notif = (
# db.query(Notificacion) .filter(Notificacion.id == notificacion_id) .first() ) if not notif:\n raise HTTPException(
# status_code=404, detail="Notificación no encontrada" ) if not notif.puede_reintentar:\n raise HTTPException(
# db.query(Cliente).filter(Cliente.id == notif.cliente_id).first() ) email_destino = cliente.email elif notif.user_id:\n
# usuario = db.query(User).filter(User.id == notif.user_id).first() email_destino = usuario.email else:\n email_destino =
# notif.destinatario_email if not email_destino:\n raise HTTPException(status_code=400, detail="No hay email de destino") #
# Reenviar background_tasks.add_task( email_service.send_email, to_email=email_destino, subject=notif.asunto,
# body=notif.mensaje, notificacion_id=notif.id, ) db.commit() return { "message":\n "Notificación reenviada",
# "notificacion_id":\n notificacion_id, "destinatario":\n email_destino, }
