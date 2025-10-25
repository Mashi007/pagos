# backend/app/api/v1/endpoints/notificaciones.py"""Endpoint para gestión de notificaciones del sistema.Soporta Email y
# WhatsApp (Twilio)."""\nimport logging\nfrom datetime \nimport date, datetime, timedelta\nfrom decimal \nimport
# Decimal\nfrom typing \nimport Optional\nfrom fastapi \nimport APIRouter, BackgroundTasks, Depends, HTTPException,
# Query\nfrom pydantic \nimport BaseModel\nfrom sqlalchemy \nimport and_, func\nfrom sqlalchemy.orm \nimport Session\nfrom
# app.api.deps \nimport get_current_user, get_db\nfrom app.core.config \nimport settings\nfrom app.models.amortizacion
# \nimport Cuota\nfrom app.models.analista \nimport Analista\nfrom app.models.cliente \nimport Cliente\nfrom
# app.models.notificacion \nimport Notificacion\nfrom app.models.pago \nimport Pago\nfrom app.models.prestamo \nimport
# Prestamo\nfrom app.models.user \nimport User# Servicios de notificación\nfrom app.services.email_service \nimport
# EmailService\nfrom app.services.whatsapp_service \nimport WhatsAppServicelogger = logging.getLogger(__name__)router =
# APIRouter()# Schemas\nclass NotificacionCreate(BaseModel):\n cliente_id:\n int tipo:\n str canal:\n str # EMAIL, WHATSAPP,
# SMS asunto:\n str mensaje:\n str programada_para:\n Optional[datetime] = None\nclass NotificacionResponse(BaseModel):\n
# id:\n int cliente_id:\n int tipo:\n str categoria:\n str asunto:\n str estado:\n str enviada_en:\n Optional[datetime]
# creado_en:\n datetime \nclass Config:\n from_attributes = True\nclass EnvioMasivoRequest(BaseModel):\n tipo_cliente:\n
# Optional[str] = None # MOROSO, ACTIVO, etc. dias_mora_min:\n Optional[int] = None template:\n str canal:\n str = "EMAIL"#
# Serviciosemail_service = EmailService()whatsapp_service = WhatsAppService()@router.post("/enviar",
# response_model=NotificacionResponse)async \ndef enviar_notificacion( notificacion:\n NotificacionCreate,
# background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db),):\n """ Enviar notificación individual. """ # Obtener
# cliente cliente = ( db.query(Cliente).filter(Cliente.id == notificacion.cliente_id).first() ) if not cliente:\n raise
# HTTPException(status_code=404, detail="Cliente no encontrado") # Crear registro de notificación nueva_notif = Notificacion(
# cliente_id=notificacion.cliente_id, tipo=notificacion.canal, # EMAIL, WHATSAPP, SMS categoria="RECORDATORIO_PAGO",
# asunto=notificacion.asunto, mensaje=notificacion.mensaje, estado="PENDIENTE", programada_para=notificacion.programada_para
# or datetime.now(), ) db.add(nueva_notif) db.commit() db.refresh(nueva_notif) # Enviar en background if notificacion.canal
# == "EMAIL":\n background_tasks.add_task( email_service.send_email, to_email=cliente.email, subject=notificacion.asunto,
# body=notificacion.mensaje, notificacion_id=nueva_notif.id, ) elif notificacion.canal == "WHATSAPP":\n
# background_tasks.add_task( whatsapp_service.send_message, to_number=cliente.telefono, message=notificacion.mensaje,
# notificacion_id=nueva_notif.id, ) logger.info( f"Notificación {nueva_notif.id} programada" + f"para envío por \
# {notificacion.canal}" ) return nueva_notif@router.post("/envio-masivo")async \ndef envio_masivo_notificaciones( request:\n
# EnvioMasivoRequest, background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db),):\n """ Envío masivo de
# notificaciones según filtros. """ # Construir query de clientes según filtros query = db.query(Cliente).join(Prestamo) if
# request.tipo_cliente == "MOROSO":\n query = query.filter(Prestamo.dias_mora > 0) if request.dias_mora_min:\n query =
# query.filter(Prestamo.dias_mora >= request.dias_mora_min) clientes = query.all() # Crear notificaciones masivas
# notificaciones_creadas = [] for cliente in clientes:\n # Personalizar mensaje según template mensaje =
# _generar_mensaje_template( template=request.template, cliente=cliente, db=db ) notif = Notificacion( cliente_id=cliente.id,
# tipo=request.canal, categoria="RECORDATORIO_PAGO", asunto=f"Recordatorio de Pago - {cliente.nombres}", mensaje=mensaje,
# estado="PENDIENTE", programada_para=datetime.now(), ) db.add(notif) notificaciones_creadas.append(notif) db.commit() #
# Programar envíos en background for notif in notificaciones_creadas:\n cliente = ( db.query(Cliente).filter(Cliente.id ==
# notif.cliente_id).first() ) if request.canal == "EMAIL" and cliente.email:\n background_tasks.add_task(
# email_service.send_email, to_email=cliente.email, subject=notif.asunto, body=notif.mensaje, notificacion_id=notif.id, )
# elif request.canal == "WHATSAPP" and cliente.telefono:\n background_tasks.add_task( whatsapp_service.send_message,
# to_number=cliente.telefono, message=notif.mensaje, notificacion_id=notif.id, ) return { "total_enviados":\n
# len(notificaciones_creadas), "canal":\n request.canal, "ids":\n [n.id for n in notificaciones_creadas],
# }@router.get("/historial/{cliente_id}")\ndef historial_notificaciones(cliente_id:\n int, db:\n Session =
# Depends(get_db)):\n """ Obtener historial de notificaciones de un cliente. """ notificaciones = ( db.query(Notificacion)
# .filter(Notificacion.cliente_id == cliente_id) .order_by(Notificacion.creado_en.desc()) .all() ) return { "cliente_id":\n
# cliente_id, "total":\n len(notificaciones), "notificaciones":\n [ { "id":\n n.id, "tipo":\n n.tipo, "categoria":\n
# n.categoria, "asunto":\n n.asunto, "estado":\n n.estado, "enviada_en":\n n.enviada_en, "creado_en":\n n.creado_en, } for n
# in notificaciones ], }@router.get("/pendientes")\ndef notificaciones_pendientes(db:\n Session = Depends(get_db)):\n """
# Obtener notificaciones pendientes de envío. """ pendientes = ( db.query(Notificacion) .filter( Notificacion.estado ==
# "PENDIENTE", Notificacion.programada_para <= datetime.now(), ) .all() ) return { "total_pendientes":\n len(pendientes),
# "notificaciones":\n [ { "id":\n n.id, "cliente_id":\n n.cliente_id, "tipo":\n n.tipo, "categoria":\n n.categoria,
# "programada_para":\n n.programada_para, } for n in pendientes ], }@router.post("/recordatorios-automaticos")async \ndef
# programar_recordatorios_automaticos( background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db)):\n """ Programar
# recordatorios automáticos para cuotas próximas a vencer. """ # Préstamos con cuotas que vencen en los próximos 3 días
# fecha_limite = date.today() + timedelta(days=3) prestamos_proximos = ( db.query(Prestamo) .filter(
# Prestamo.fecha_vencimiento <= fecha_limite, Prestamo.fecha_vencimiento >= date.today(), Prestamo.estado == "ACTIVO", )
# .all() ) recordatorios = [] for prestamo in prestamos_proximos:\n mensaje = f"""Estimado/a {prestamo.cliente.nombres},Le
# recordamos que tiene una cuota próxima a vencer:\n Monto:\n {prestamo.monto_cuota:\n.2f} Fecha de vencimiento:\n
# {prestamo.fecha_vencimiento.strftime('%d/%m/%Y')} Días restantes:\n {(prestamo.fecha_vencimiento - date.today()).days}Por
# favor, realice su pago a tiempo para evitar recargos.Gracias. """ notif = Notificacion( cliente_id=prestamo.cliente_id,
# tipo="EMAIL", categoria="RECORDATORIO_PAGO", asunto="Recordatorio:\n Cuota próxima a vencer", mensaje=mensaje,
# estado="PENDIENTE", programada_para=datetime.now(), ) db.add(notif) recordatorios.append(notif) db.commit() # Enviar en
# background for notif in recordatorios:\n cliente = ( db.query(Cliente).filter(Cliente.id == notif.cliente_id).first() ) if
# cliente.email:\n background_tasks.add_task( email_service.send_email, to_email=cliente.email, subject=notif.asunto,
# body=notif.mensaje, notificacion_id=notif.id, ) return { "recordatorios_programados":\n len(recordatorios),
# "prestamos_notificados":\n [p.id for p in prestamos_proximos], }# Función helper para generar mensajes desde templates\ndef
# _generar_mensaje_template( template:\n str, cliente:\n Cliente, db:\n Session) -> str:\n """ Generar mensaje personalizado
# según template. """ prestamos = ( db.query(Prestamo) .filter(Prestamo.cliente_id == cliente.id, Prestamo.estado ==
# "ACTIVO") .all() ) if template == "RECORDATORIO_PAGO":\n total_deuda = sum(p.saldo_pendiente for p in prestamos) return
# f"""Estimado/a {cliente.nombres} {cliente.apellidos},Le recordamos que tiene un saldo pendiente de {total_deuda:\n.2f}.Por
# favor, póngase al día con sus pagos para evitar recargos.Gracias por su atención. """ elif template == "MORA":\n
# prestamos_mora = [p for p in prestamos if p.dias_mora > 0] return f"""Estimado/a {cliente.nombres},Su cuenta presenta
# {len(prestamos_mora)} préstamo(s) en mora.Por favor, comuníquese con nosotros para regularizar su situación. """ return
# "Mensaje genérico de notificación."# ============================================# NOTIFICACIONES AUTOMÁTICAS PROGRAMADAS#
# ============================================@router.post("/programar-automaticas")async \ndef
# programar_notificaciones_automaticas( background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db)):\n """
# Programar todas las notificaciones automáticas del sistema Debe ejecutarse diariamente via cron job """
# notificaciones_programadas = [] # 1. RECORDATORIOS PRE-VENCIMIENTO (3 días antes) fecha_recordatorio = date.today() +
# timedelta(days=3) cuotas_proximas = ( db.query(Cuota) .join(Prestamo) .join(Cliente) .filter( Cuota.fecha_vencimiento ==
# fecha_recordatorio, Cuota.estado.in_(["PENDIENTE", "PARCIAL"]), Cliente.email.isnot(None), Cliente.activo, ) .all() ) for
# cuota in cuotas_proximas:\n cliente = cuota.prestamo.cliente # Verificar que no se haya enviado ya ya_enviado = (
# db.query(Notificacion) .filter( Notificacion.cliente_id == cliente.id, Notificacion.categoria == "CUOTA_PROXIMA",
# func.date(Notificacion.creado_en) == date.today(), ) .first() ) if not ya_enviado:\n mensaje = f"""Estimado/a
# {cliente.nombre_completo},Le recordamos que tiene una cuota próxima a vencer:\n Cuota #:\n {cuota.numero_cuota} Monto:\n
# {float(cuota.monto_cuota):\n.2f} Fecha de vencimiento:\n {cuota.fecha_vencimiento.strftime('%d/%m/%Y')} Días restantes:\n
# 3Por favor, realice su pago a tiempo para evitar recargos por mora.Instrucciones de pago:\n Transferencia bancaria:\n
# Cuenta 123456789 Efectivo:\n En nuestras oficinas Referencia:\n CUOTA-{cuota.id}Datos de contacto:\nTeléfono:\n (021)
# 123-456Email:\n cobranzas@financiera.comGracias por su puntualidad. """ notif = Notificacion( cliente_id=cliente.id,
# tipo="EMAIL", categoria="CUOTA_PROXIMA", asunto=f"Recordatorio:\n Cuota #{cuota.numero_cuota} vence \ en 3 días",
# mensaje=mensaje, estado="PENDIENTE", programada_para=datetime.now().replace( hour=9, minute=0, second=0 ),
# prioridad="ALTA", ) db.add(notif) notificaciones_programadas.append(notif) # 2. AVISOS DE CUOTA VENCIDA (día siguiente)
# cuotas_vencidas_ayer = ( db.query(Cuota) .join(Prestamo) .join(Cliente) .filter( Cuota.fecha_vencimiento == date.today() -
# timedelta(days=1), Cuota.estado.in_(["VENCIDA", "PARCIAL"]), Cliente.email.isnot(None), Cliente.activo, ) .all() ) for
# cuota in cuotas_vencidas_ayer:\n cliente = cuota.prestamo.cliente # Calcular mora mora_calculada = cuota.calcular_mora(
# Decimal(str(settings.TASA_MORA_DIARIA)) ) mensaje = f"""Estimado/a {cliente.nombre_completo},ALERTA:\n Su cuota
# #{cuota.numero_cuota} está VENCIDA. Fecha de vencimiento:\n {cuota.fecha_vencimiento.strftime('%d/%m/%Y')} Días de mora:\n
# {(date.today() - cuota.fecha_vencimiento).days} Monto adeudado:\n {float(cuota.monto_pendiente_total):\n,.2f} Recargo por
# mora:\n {float(mora_calculada):\n,.2f}URGENTE:\n Regularice su pago inmediatamente para evitar:\n Incremento de mora diaria
# Reporte en centrales de riesgo Acciones legalesContacto inmediato:\n (021) 123-456 """ notif = Notificacion(
# cliente_id=cliente.id, tipo="EMAIL", categoria="CUOTA_VENCIDA", asunto=f"🔴 URGENTE:\n Cuota #{cuota.numero_cuota} VENCIDA",
# mensaje=mensaje, estado="PENDIENTE", programada_para=datetime.now(), prioridad="URGENTE", ) db.add(notif)
# notificaciones_programadas.append(notif) db.commit() # Programar envíos for notif in notificaciones_programadas:\n cliente
# = ( db.query(Cliente).filter(Cliente.id == notif.cliente_id).first() ) if cliente.email:\n background_tasks.add_task(
# email_service.send_template_email, to_email=cliente.email, subject=notif.asunto, template_name=( "recordatorio_pago" if
# "recordatorio" in notif.asunto.lower() else "mora" ), context={ "cliente_nombre":\n cliente.nombre_completo, "empresa":\n
# "Financiera Automotriz", "telefono":\n "(021) 123-456", "email":\n "info@financiera.com", }, notificacion_id=notif.id, )
# return { "notificaciones_programadas":\n len(notificaciones_programadas), "recordatorios_pre_vencimiento":\n len( [ n for n
# in notificaciones_programadas if n.categoria == "CUOTA_PROXIMA" ] ), "avisos_vencidas":\n len( [ n for n in
# notificaciones_programadas if n.categoria == "CUOTA_VENCIDA" ] ), }@router.post("/confirmar-pago-recibido/{pago_id}")async
# \ndef enviar_confirmacion_pago( pago_id:\n int, background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db),):\n
# """ 3. Confirmación de pago recibido (automática al registrar pago) """ # Obtener pago con joins explícitos pago = (
# db.query(Pago) .select_from(Pago) .join(Prestamo, Pago.prestamo_id == Prestamo.id) .join(Cliente, Prestamo.cliente_id ==
# Cliente.id) .filter(Pago.id == pago_id) .first() ) if not pago:\n raise HTTPException(status_code=404, detail="Pago no
# encontrado") cliente = pago.prestamo.cliente # Calcular próximo vencimiento proxima_cuota = ( db.query(Cuota) .filter(
# Cuota.prestamo_id == pago.prestamo_id, Cuota.estado.in_(["PENDIENTE", "PARCIAL"]), ) .order_by(Cuota.numero_cuota) .first()
# ) proximo_vencimiento = "No hay cuotas pendientes" if proxima_cuota:\n proximo_vencimiento = f"Cuota
# #{proxima_cuota.numero_cuota} - {proxima_cuota.fecha_vencimiento.strftime('%d/%m/%Y')}" mensaje = f"""Estimado/a
# {cliente.nombre_completo},Gracias por su pago!CONFIRMACIÓN DE PAGO RECIBIDO:\n Fecha:\n
# {pago.fecha_pago.strftime('%d/%m/%Y')} Monto:\n {float(pago.monto_pagado):\n.2f} Cuota(s) pagada(s):\n #{pago.numero_cuota}
# Método:\n {pago.metodo_pago} Referencia:\n {pago.numero_operacion or pago.comprobante or 'N/A'}DETALLE DE APLICACIÓN:\n
# Capital:\n {float(pago.monto_capital):\n.2f} Interés:\n {float(pago.monto_interes):\n.2f} Mora:\n
# {float(pago.monto_mora):\n.2f}ESTADO ACTUAL:\n Saldo pendiente:\n {float(pago.prestamo.saldo_pendiente):\n.2f} Próximo
# vencimiento:\n {proximo_vencimiento}Agradecemos su puntualidad y confianza. """ # Crear notificación notif = Notificacion(
# cliente_id=cliente.id, tipo="EMAIL", categoria="PAGO_RECIBIDO", asunto=f"✅ Confirmación:\n Pago de {float
# (pago.monto_pagado):\n.2f} recibido", mensaje=mensaje, estado="PENDIENTE", programada_para=datetime.now(),
# prioridad="NORMAL", ) db.add(notif) db.commit() db.refresh(notif) # Enviar inmediatamente if cliente.email:\n
# background_tasks.add_task( email_service.send_email, to_email=cliente.email, subject=notif.asunto, body=notif.mensaje,
# notificacion_id=notif.id, ) return { "message":\n "Confirmación de pago programada", "notificacion_id":\n notif.id,
# "cliente":\n cliente.nombre_completo, }@router.post("/estado-cuenta-mensual")async \ndef enviar_estados_cuenta_mensual(
# background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db)):\n """ 4. Estado de cuenta mensual (primer día de
# cada mes) """ # Obtener todos los clientes activos con email clientes = ( db.query(Cliente) .filter(Cliente.activo,
# Cliente.email.isnot(None)) .all() ) estados_enviados = [] for cliente in clientes:\n # Calcular resumen del mes anterior
# mes_anterior = date.today().replace(day=1) - timedelta(days=1) inicio_mes = mes_anterior.replace(day=1) fin_mes =
# mes_anterior # Pagos del mes anterior con joins explícitos pagos_mes = ( db.query(Pago) .select_from(Pago) .join(Prestamo,
# Pago.prestamo_id == Prestamo.id) .filter( Prestamo.cliente_id == cliente.id, Pago.fecha_pago >= inicio_mes, Pago.fecha_pago
# <= fin_mes, ) .all() ) # Cuotas pendientes con joins explícitos cuotas_pendientes = ( db.query(Cuota) .select_from(Cuota)
# .join(Prestamo, Cuota.prestamo_id == Prestamo.id) .filter( Prestamo.cliente_id == cliente.id,
# Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]), ) .order_by(Cuota.fecha_vencimiento) .limit(3) .all() ) # Resumen
# financiero resumen = cliente.calcular_resumen_financiero(db) mensaje = f"""Estimado/a {cliente.nombre_completo},ESTADO DE
# CUENTA - {mes_anterior.strftime('%B %Y').upper()}RESUMEN DEL MES ANTERIOR:\n Pagos realizados:\n {len(pagos_mes)} Total
# pagado:\n {sum(float(p.monto_pagado) for p in pagos_mes):\n.2f}ESTADO ACTUAL:\n Total financiado:\n
# {float(resumen['total_financiado']):\n.2f} Total pagado:\n {float(resumen['total_pagado']):\n.2f} Saldo pendiente:\n
# {float(resumen['saldo_pendiente']):\n.2f} Cuotas pagadas:\n {resumen['cuotas_pagadas']} / {resumen['cuotas_totales']} %
# Avance:\n {resumen['porcentaje_avance']}%PRÓXIMOS VENCIMIENTOS:\n""" for cuota in cuotas_pendientes:\n mensaje += ( f"•
# Cuota #{cuota.numero_cuota}:\n " f"{float(cuota.monto_cuota):\n.2f} - " f"{cuota.fecha_vencimiento.strftime('%d/%m/%Y')}\n"
# ) mensaje += "\nMantengase al día con sus pagos.\n\nSaludos cordiales." # Crear notificación notif = Notificacion(
# cliente_id=cliente.id, tipo="EMAIL", categoria="GENERAL", asunto=f"Estado de Cuenta - {mes_anterior.strftime('%B %Y')}",
# mensaje=mensaje, estado="PENDIENTE", programada_para=datetime.now().replace(hour=10, minute=0), prioridad="NORMAL", )
# db.add(notif) estados_enviados.append(notif) db.commit() # Programar envíos for notif in estados_enviados:\n cliente = (
# db.query(Cliente).filter(Cliente.id == notif.cliente_id).first() ) background_tasks.add_task( email_service.send_email,
# to_email=cliente.email, subject=notif.asunto, body=notif.mensaje, notificacion_id=notif.id, ) return {
# "estados_cuenta_programados":\n len(estados_enviados), "clientes_notificados":\n [c.id for c in clientes], }#
# ============================================# NOTIFICACIONES A USUARIOS DEL SISTEMA#
# ============================================@router.post("/usuarios/resumen-diario")async \ndef
# enviar_resumen_diario_usuarios( background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db)):\n """ Notificaciones
# diarias a usuarios - Resumen de vencimientos del día - Pagos recibidos ayer - Clientes que entraron en mora - Alertas de
# clientes críticos (>30 días mora) """ hoy = date.today() ayer = hoy - timedelta(days=1) # Obtener datos del día
# vencimientos_hoy = ( db.query(Cuota) .join(Prestamo) .join(Cliente) .filter( Cuota.fecha_vencimiento == hoy,
# Cuota.estado.in_(["PENDIENTE", "PARCIAL"]), ) .count() ) pagos_ayer = ( db.query(Pago) .filter(Pago.fecha_pago == ayer,
# Pago.estado != "ANULADO") .all() ) total_cobrado_ayer = sum(float(p.monto_pagado) for p in pagos_ayer) # Clientes que
# entraron en mora ayer nuevos_morosos = ( db.query(Cliente) .join(Prestamo) .join(Cuota) .filter( Cuota.fecha_vencimiento ==
# ayer, Cuota.estado == "VENCIDA", Cliente.activo, ) .distinct() .all() ) # Clientes críticos (>30 días mora)
# clientes_criticos = ( db.query(Cliente) .filter(Cliente.activo, Cliente.dias_mora > 30) .count() ) # Obtener usuarios para
# notificar usuarios_notificar = ( db.query(User) .filter(User.is_admin, User.is_active, User.email.isnot(None)) .all() ) for
# usuario in usuarios_notificar:\n mensaje = f"""Buenos días {usuario.full_name},RESUMEN DIARIO -
# {hoy.strftime('%d/%m/%Y')}VENCIMIENTOS HOY:\n {vencimientos_hoy} cuotasCOBRADO AYER:\n {total_cobrado_ayer} USD
# ({len(pagos_ayer)} pagos)NUEVOS MOROSOS:\n {len(nuevos_morosos)} clientesCLIENTES CRITICOS:\n {clientes_criticos} (>30 dias
# mora)ACCIONES RECOMENDADAS:\n Contactar clientes con vencimientos hoy Seguimiento a nuevos morosos Atención prioritaria a
# clientes críticosAcceder al sistema:\n https:\n//pagos-f2qf.onrender.comSaludos. """ notif = Notificacion(
# user_id=usuario.id, tipo="EMAIL", categoria="GENERAL", asunto=f"📊 Resumen Diario - {hoy.strftime('%d/%m/%Y')}",
# mensaje=mensaje, estado="PENDIENTE", programada_para=datetime.now().replace(hour=8, minute=0), prioridad="NORMAL", )
# db.add(notif) # Enviar background_tasks.add_task( email_service.send_email, to_email=usuario.email, subject=notif.asunto,
# body=notif.mensaje, notificacion_id=notif.id, ) db.commit() return { "usuarios_notificados":\n len(usuarios_notificar),
# "vencimientos_hoy":\n vencimientos_hoy, "total_cobrado_ayer":\n total_cobrado_ayer, "nuevos_morosos":\n
# len(nuevos_morosos), "clientes_criticos":\n clientes_criticos, }@router.post("/usuarios/reporte-semanal")async \ndef
# enviar_reporte_semanal_usuarios( background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db)):\n """
# Notificaciones semanales (Lunes 9:\n00 AM):\n - Reporte semanal de cobranza - Nuevos clientes de la semana - Evolución de
# la cartera - Top performers y alertas """ # Calcular semana anterior (lunes a domingo) hoy = date.today() inicio_semana =
# hoy - timedelta( days=hoy.weekday() + 7 ) # Lunes semana anterior fin_semana = inicio_semana + timedelta(days=6) # Domingo
# semana anterior # Datos de la semana pagos_semana = ( db.query(Pago) .filter( Pago.fecha_pago >= inicio_semana,
# Pago.fecha_pago <= fin_semana, Pago.estado != "ANULADO", ) .all() ) nuevos_clientes = ( db.query(Cliente) .filter(
# func.date(Cliente.fecha_registro) >= inicio_semana, func.date(Cliente.fecha_registro) <= fin_semana, ) .all() ) # Top
# analista de la semana top_analista = ( db.query( User.full_name, func.count(Cliente.id).label("nuevos_clientes") )
# .outerjoin( Cliente, and_( Analista.id == Cliente.analista_id, func.date(Cliente.fecha_registro) >= inicio_semana,
# func.date(Cliente.fecha_registro) <= fin_semana, ), ) .filter( User.is_admin, ) .group_by(User.id, User.full_name)
# .order_by(func.count(Cliente.id).desc()) .first() ) # Enviar a usuarios gerenciales usuarios_gerenciales = ( db.query(User)
# .filter(User.is_admin, User.is_active, User.email.isnot(None)) .all() ) for usuario in usuarios_gerenciales:\n mensaje =
# f"""Buenos días {usuario.full_name},REPORTE SEMANAL - {inicio_semana.strftime('%d/%m')} al
# {fin_semana.strftime('%d/%m/%Y')} COBRANZA:\n Total cobrado:\n {sum(float(p.monto_pagado) for p in pagos_semana):\n,.2f}
# Número de pagos:\n {len(pagos_semana)} Promedio por pago:\n { (sum(float(p.monto_pagado) for p in pagos_semana) /
# len(pagos_semana)):\n,.2f if pagos_semana else 0} NUEVOS CLIENTES:\n {len(nuevos_clientes)} TOP PERFORMER:\n
# {top_analista[0] if top_analista else 'N/A'} ({top_analista[1] if top_analista else 0} nuevos clientes) EVOLUCIÓN DE
# CARTERA:\n Clientes activos:\n {db.query(Cliente).filter(Cliente.activo).count()} Tasa de morosidad:\n {db.query
# (Cliente).filter(Cliente.dias_mora > 0).count() / db.query(Cliente).filter(Cliente.activo).count() * 100:\n.2f}%Revisar
# dashboard completo:\n https:\n//pagos-f2qf.onrender.comSaludos. """ notif = Notificacion( user_id=usuario.id, tipo="EMAIL",
# categoria="GENERAL", asunto=f"📈 Reporte Semanal - {inicio_semana.strftime('%d/%m')} al {fin_semana.strftime('%d/%m')}",
# mensaje=mensaje, estado="PENDIENTE", programada_para=datetime.now().replace(hour=9, minute=0), prioridad="NORMAL", )
# db.add(notif) background_tasks.add_task( email_service.send_email, to_email=usuario.email, subject=notif.asunto,
# body=notif.mensaje, notificacion_id=notif.id, ) db.commit() return { "usuarios_notificados":\n len(usuarios_gerenciales),
# "nuevos_clientes_semana":\n len(nuevos_clientes), "total_cobrado_semana":\n sum( float(p.monto_pagado) for p in
# pagos_semana ), }# ============================================# CONFIGURACIÓN DE NOTIFICACIONES#
# ============================================@router.get("/configuracion")\ndef obtener_configuracion_notificaciones( db:\n
# Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ ⚙️ Obtener configuración de
# notificaciones """ return { "notificaciones_habilitadas":\n { "recordatorios_pre_vencimiento":\n True,
# "avisos_cuota_vencida":\n True, "confirmacion_pago":\n True, "estado_cuenta_mensual":\n True, "resumen_diario_usuarios":\n
# True, "reporte_semanal":\n True, "reporte_mensual":\n True, }, "configuracion_horarios":\n { "recordatorios_clientes":\n
# "09:\n00", "resumen_diario":\n "08:\n00", "reporte_semanal":\n "09:\n00", # Lunes "reporte_mensual":\n "10:\n00", # Día 1
# }, "configuracion_frecuencias":\n { "dias_anticipacion_recordatorio":\n 3, "frecuencia_recordatorios_mora":\n 3, # cada 3
# días "max_intentos_envio":\n 3, }, "plantillas_disponibles":\n [ "recordatorio_pago", "cuota_vencida", "pago_recibido",
# "estado_cuenta", "mora", "prestamo_aprobado", ], "configuracion_smtp":\n { "host":\n settings.SMTP_HOST, "port":\n
# settings.SMTP_PORT, "habilitado":\n settings.EMAIL_ENABLED, "from_name":\n settings.FROM_NAME, },
# }@router.get("/historial-completo")\ndef historial_completo_notificaciones( fecha_desde:\n Optional[date] = Query(None),
# fecha_hasta:\n Optional[date] = Query(None), tipo:\n Optional[str] = Query(None), estado:\n Optional[str] = Query(None),
# cliente_id:\n Optional[int] = Query(None), page:\n int = Query(1, ge=1), page_size:\n int = Query(20, ge=1, le=1000), db:\n
# Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📋 Historial completo de notificaciones
# - Log completo de emails enviados - Estado:\n Enviado/Entregado/Rebotado/Error - Filtros por cliente, tipo, fecha """ query
# = ( db.query(Notificacion) .select_from(Notificacion) .outerjoin(Cliente) .outerjoin(User) ) # Aplicar filtros if
# fecha_desde:\n query = query.filter(func.date(Notificacion.creado_en) >= fecha_desde) if fecha_hasta:\n query =
# query.filter(func.date(Notificacion.creado_en) <= fecha_hasta) if tipo:\n query = query.filter(Notificacion.tipo == tipo)
# if estado:\n query = query.filter(Notificacion.estado == estado) if cliente_id:\n query =
# query.filter(Notificacion.cliente_id == cliente_id) # Paginación total = query.count() skip = (page - 1) * page_size
# notificaciones = ( query.order_by(Notificacion.creado_en.desc()) .offset(skip) .limit(page_size) .all() ) return {
# "total":\n total, "page":\n page, "page_size":\n page_size, "total_pages":\n (total + page_size - 1) // page_size,
# "notificaciones":\n [ { "id":\n n.id, "destinatario":\n ( n.cliente.nombre_completo if n.cliente else (n.user.full_name if
# n.user else "N/A") ), "tipo":\n n.tipo.value, "categoria":\n n.categoria.value, "asunto":\n n.asunto, "estado":\n
# n.estado.value, "intentos":\n n.intentos, "creado_en":\n n.creado_en, "enviada_en":\n n.enviada_en, "error_mensaje":\n
# n.error_mensaje, "puede_reenviar":\n n.puede_reintentar, } for n in notificaciones ], "estadisticas":\n {
# "total_enviadas":\n ( db.query(Notificacion) .filter(Notificacion.estado == "ENVIADA") .count() ), "total_fallidas":\n (
# db.query(Notificacion) .filter(Notificacion.estado == "FALLIDA") .count() ), "total_pendientes":\n ( db.query(Notificacion)
# .filter(Notificacion.estado == "PENDIENTE") .count() ), }, }@router.post("/reenviar/{notificacion_id}")async \ndef
# reenviar_notificacion( notificacion_id:\n int, background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ Reenvío manual de notificación fallida """ notif = (
# db.query(Notificacion) .filter(Notificacion.id == notificacion_id) .first() ) if not notif:\n raise HTTPException(
# status_code=404, detail="Notificación no encontrada" ) if not notif.puede_reintentar:\n raise HTTPException(
# status_code=400, detail="No se puede reenviar:\n máximo de intentos alcanzado o estado inválido", ) # Resetear estado
# notif.estado = "PENDIENTE" notif.programada_para = datetime.now() # Obtener destinatario if notif.cliente_id:\n cliente = (
# db.query(Cliente).filter(Cliente.id == notif.cliente_id).first() ) email_destino = cliente.email elif notif.user_id:\n
# usuario = db.query(User).filter(User.id == notif.user_id).first() email_destino = usuario.email else:\n email_destino =
# notif.destinatario_email if not email_destino:\n raise HTTPException(status_code=400, detail="No hay email de destino") #
# Reenviar background_tasks.add_task( email_service.send_email, to_email=email_destino, subject=notif.asunto,
# body=notif.mensaje, notificacion_id=notif.id, ) db.commit() return { "message":\n "Notificación reenviada",
# "notificacion_id":\n notificacion_id, "destinatario":\n email_destino, }
