# backend/app/services/notification_multicanal_service.py"""Servicio de Notificaciones MulticanalSistema 100% automático de
# sqlalchemy.orm import Sessionfrom app.models.amortizacion import Cuotafrom app.models.cliente import Clientefrom
# app.models.notificacion import Notificacionfrom app.models.prestamo import Prestamofrom app.models.user import Userfrom
# app.services.email_service import EmailServicefrom app.services.whatsapp_service import WhatsAppServicelogger =
# RECORDATORIO_3_DIAS = "RECORDATORIO_3_DIAS" RECORDATORIO_1_DIA = "RECORDATORIO_1_DIA" DIA_VENCIMIENTO = "DIA_VENCIMIENTO"
# MORA_1_DIA = "MORA_1_DIA" MORA_3_DIAS = "MORA_3_DIAS" MORA_5_DIAS = "MORA_5_DIAS" CONFIRMACION_PAGO =
# "CONFIRMACION_PAGO"class CanalNotificacion(str, Enum): """Canales de notificación disponibles""" EMAIL = "EMAIL" WHATSAPP =
# "WHATSAPP" AMBOS = "AMBOS" NINGUNO = "NINGUNO"class PreferenciasNotificacion: """Gestión de preferencias de notificación
# por cliente""" @staticmethod def obtener_preferencias_cliente( cliente_id: int, db: Session ) -> CanalNotificacion: """
# tabla de preferencias por cliente # Por ahora, usar lógica por defecto cliente = db.query(Cliente).filter(Cliente.id ==
# cliente_id).first() if not cliente: return CanalNotificacion.NINGUNO # Lógica por defecto tiene_email = bool(cliente.email)
# tiene_telefono = bool(cliente.telefono) if tiene_email and tiene_telefono: return CanalNotificacion.AMBOS elif tiene_email:
# return CanalNotificacion.EMAIL elif tiene_telefono: return CanalNotificacion.WHATSAPP else: return
# CanalNotificacion.NINGUNO @staticmethod def actualizar_preferencias_cliente( cliente_id: int, canal_preferido:
# CanalNotificacion, db: Session ) -> bool: """Actualizar preferencias de notificación del cliente""" try: # TODO:
# Implementar tabla de preferencias # Por ahora, guardar en observaciones del cliente cliente = (
# db.query(Cliente).filter(Cliente.id == cliente_id).first() ) if cliente: cliente.observaciones = (
# f"PREFERENCIA_NOTIFICACION: {canal_preferido.value}" ) db.commit() return True return False except Exception as e:
# logger.error(f"Error actualizando preferencias: {e}") return Falseclass NotificacionMulticanal: """ 🔔 Servicio principal de
# notificaciones multicanal """ def __init__(self, db: Session): self.db = db self.email_service = EmailService()
# TipoNotificacionCliente.RECORDATORIO_3_DIAS: "09:00", TipoNotificacionCliente.RECORDATORIO_1_DIA: "09:00",
# TipoNotificacionCliente.DIA_VENCIMIENTO: "08:00", TipoNotificacionCliente.MORA_1_DIA: "10:00",
# TipoNotificacionCliente.MORA_3_DIAS: "10:00", TipoNotificacionCliente.MORA_5_DIAS: "10:00",
# TipoNotificacionCliente.CONFIRMACION_PAGO: "INMEDIATO", } # Límites anti-spam self.LIMITE_NOTIFICACIONES_DIA = 3
# self.INTERVALO_MINIMO_HORAS = 2 self.REINTENTOS_MAXIMOS = 2 self.INTERVALO_REINTENTO_MINUTOS = 30 async def
# procesar_notificaciones_automaticas(self) -> Dict[str, Any]: """ 🤖 Procesamiento automático de todas las notificaciones Se
# ejecuta cada hora via scheduler/cron """ try: logger.info( "🔔 Iniciando procesamiento automático de notificaciones" )
# "fallidas": 0, "por_tipo": {}, "errores": [], } # Procesar cada tipo de notificación for tipo_notif in
# TipoNotificacionCliente: try: resultado_tipo = await self._procesar_tipo_notificacion( tipo_notif )
# Exception as e: error_msg = ( f"Error procesando {tipo_notif.value}: {str(e)}" ) logger.error(error_msg)
# procesamiento automático: {e}") return {"error": str(e)} async def _procesar_tipo_notificacion( self, tipo:
# TipoNotificacionCliente ) -> Dict: """Procesar un tipo específico de notificación""" try: # Obtener clientes que requieren
# esta notificación clientes_objetivo = self._obtener_clientes_para_notificacion(tipo) resultado = { "tipo": tipo.value,
# try: # Verificar límites anti-spam if not self._puede_enviar_notificacion( cliente_data["cliente_id"] ): continue # Obtener
# preferencias del cliente preferencias = ( PreferenciasNotificacion.obtener_preferencias_cliente(
# cliente_data["cliente_id"], self.db ) ) if preferencias == CanalNotificacion.NINGUNO: continue # Enviar por canales según
# preferencias resultado_envio = ( await self._enviar_notificacion_multicanal( cliente_data, tipo, preferencias ) ) if
# resultado["detalles"].append(resultado_envio) except Exception as e: logger.error( "Error enviando notificación" + "a
# cliente {cliente_data.get('cliente_id')}: {e}" ) resultado["fallidas"] += 1 return resultado except Exception as e:
# "fallidas": 0, "error": str(e), } def _obtener_clientes_para_notificacion( self, tipo: TipoNotificacionCliente ) ->
# List[Dict]: """Obtener clientes que requieren notificación específica""" try: hoy = date.today() clientes_objetivo = [] if
# cuotas = ( self.db.query(Cuota) .join(Prestamo) .join(Cliente) .filter( Cuota.fecha_vencimiento == fecha_objetivo,
# Cuota.estado.in_(["PENDIENTE", "PARCIAL"]), Cliente.activo, ) .all() ) elif tipo ==
# self.db.query(Cuota) .join(Prestamo) .join(Cliente) .filter( Cuota.fecha_vencimiento == fecha_objetivo,
# Cuota.estado.in_(["PENDIENTE", "PARCIAL"]), Cliente.activo, ) .all() ) elif tipo ==
# TipoNotificacionCliente.DIA_VENCIMIENTO: # Cuotas que vencen hoy cuotas = ( self.db.query(Cuota) .join(Prestamo)
# .join(Cliente) .filter( Cuota.fecha_vencimiento == hoy, Cuota.estado.in_(["PENDIENTE", "PARCIAL"]), Cliente.activo, )
# .all() ) elif tipo == TipoNotificacionCliente.MORA_1_DIA: # Cuotas con 1 día de mora fecha_vencida = hoy -
# fecha_vencida, Cuota.estado.in_(["PENDIENTE", "PARCIAL", "VENCIDA"]), Cliente.activo, ) .all() ) elif tipo ==
# self.db.query(Cuota) .join(Prestamo) .join(Cliente) .filter( Cuota.fecha_vencimiento == fecha_vencida,
# Cuota.estado.in_(["PENDIENTE", "PARCIAL", "VENCIDA"]), Cliente.activo, ) .all() ) elif tipo ==
# self.db.query(Cuota) .join(Prestamo) .join(Cliente) .filter( Cuota.fecha_vencimiento == fecha_vencida,
# Cuota.estado.in_(["PENDIENTE", "PARCIAL", "VENCIDA"]), Cliente.activo, ) .all() ) else: cuotas = [] # Convertir cuotas a
# cliente.id, "nombre": cliente.nombre_completo, "email": cliente.email, "telefono": cliente.telefono, "cuota_numero":
# cuota.numero_cuota, "monto_cuota": float(cuota.monto_cuota), "fecha_vencimiento": cuota.fecha_vencimiento, "dias_mora": (
# (hoy - cuota.fecha_vencimiento).days if cuota.fecha_vencimiento < hoy else 0 ), "saldo_pendiente": float(
# cuota.capital_pendiente + cuota.interes_pendiente ), "vehiculo": cliente.vehiculo_completo or "Vehículo", } ) return
# clientes_objetivo except Exception as e: logger.error(f"Error obteniendo clientes para {tipo.value}: {e}") return [] async
# def _enviar_notificacion_multicanal( self, cliente_data: Dict, tipo: TipoNotificacionCliente, preferencias:
# CanalNotificacion, ) -> Dict[str, Any]: """ 📧📱 Enviar notificación por múltiples canales """ try: resultado = {
# "cliente_id": cliente_data["cliente_id"], "cliente_nombre": cliente_data["nombre"], "tipo_notificacion": tipo.value,
# CanalNotificacion.AMBOS, ]: if cliente_data["email"]: canales_envio.append("EMAIL") if preferencias in [
# CanalNotificacion.WHATSAPP, CanalNotificacion.AMBOS, ]: if cliente_data["telefono"]: canales_envio.append("WHATSAPP") #
# exito_email = await self._enviar_email_cliente( cliente_data, tipo ) if exito_email:
# exito_whatsapp = await self._enviar_whatsapp_cliente( cliente_data, tipo ) if exito_whatsapp:
# self._registrar_en_historial(cliente_data, tipo, resultado) return resultado except Exception as e: logger.error("Error en
# _enviar_email_cliente( self, cliente_data: Dict, tipo: TipoNotificacionCliente ) -> bool: """Enviar notificación por
# email""" try: # Obtener template de email template_email = self._obtener_template_email(tipo, cliente_data) # Enviar email
# resultado = await self.email_service.send_email( to_email=cliente_data["email"], subject=template_email["asunto"],
# logger.error(f"Error enviando email: {e}") return False async def _enviar_whatsapp_cliente( self, cliente_data: Dict, tipo:
# TipoNotificacionCliente ) -> bool: """Enviar notificación por WhatsApp""" try: # Obtener template de WhatsApp
# template_whatsapp = self._obtener_template_whatsapp( tipo, cliente_data ) # Enviar WhatsApp resultado = await
# self.whatsapp_service.send_message( to_phone=cliente_data["telefono"], message=template_whatsapp["mensaje"], ) return
# _obtener_template_email( self, tipo: TipoNotificacionCliente, cliente_data: Dict ) -> Dict[str, str]: """Obtener template
# de email según tipo de notificación""" # Variables comunes variables = { "nombre": cliente_data["nombre"].split()[0], #
# Primer nombre "nombre_completo": cliente_data["nombre"], "cuota": cliente_data["cuota_numero"], "monto":
# cliente_data["dias_mora"], "saldo_pendiente": f"${cliente_data['saldo_pendiente']:,.0f}", "vehiculo":
# cliente_data["vehiculo"], "nombre_empresa": "Financiamiento Automotriz", "telefono_empresa": "809-XXX-XXXX", } templates =
# { TipoNotificacionCliente.RECORDATORIO_3_DIAS: { "asunto": f"🚗 Recordatorio: Tu cuota #{variables['cuota']} vence en 3
# días", "cuerpo_html": ( """ <div style="font-family: Arial, sans-serif; max-width: \ 600px; margin: 0 auto;"> <div
# style="background: #007bff; color: white; padding: 20px; text-align: center;"> <h1>🚗 Recordatorio de Pago</h1> <p
# style="margin: 0;">Tu cuota vence en 3 días</p> </div> <div style="padding: 20px; background: #f8f9fa;"> <div
# cuota #{variables['cuota']} de tu <strong>{variables['vehiculo']}</strong> vence el
# <strong>{variables['fecha']}</strong>.</p> <div style="background: #e3f2fd; padding: 15px; \ border-radius: 5px; margin:
# 20px 0;"> <h3 style="margin-top: 0;">💰 Detalles del \ Pago:</h3> <p><strong>Monto:</strong> {variables[ \ 'monto']}</p>
# <p><strong>Fecha de vencimiento:</strong> {variables['fecha']}</p> <p><strong>Cuota #:</strong> {variables['cuota']}</p>
# </div> <p>Puedes realizar tu pago por:</p> <ul> <li>🏦 Transferencia bancaria</li> <li>🏢 Nuestras oficinas</li> <li>📱 App
# móvil</li> </ul> <p>¡Gracias por tu puntualidad!</p> <div style="text-align: center; margin-top: 30px;"> <p style="color:
# #666;"> {variables['nombre_empresa']}<br> 📞 {variables['telefono_empresa']} </p> </div> </div> </div> </div> """ ), },
# TipoNotificacionCliente.MORA_1_DIA: { "asunto": f"⚠️ Tu cuota #{variables['cuota']} está" + f"vencida - 1 día de atraso",
# "cuerpo_html": ( """ <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;"> <div
# style="background: #ffc107; color: #212529; padding: 20px; text-align: center;"> <h1>⚠️ Cuota Vencida</h1> <p
# style="margin: 0;">1 día de atraso</p> </div> <div style="padding: 20px; background: #f8f9fa;"> <div style="background:
# white; padding: 20px; \ border-radius: 8px;"> <h2>Estimado/a {variables['nombre']},</h2> <div style="background: #fff3cd;
# border: 1px \ solid #ffeaa7; padding: 15px; border-radius: 5px; \ margin: 20px 0;"> <p><strong>⚠️ Tu cuota
# #{variables['cuota']} \ está vencida desde ayer.</strong></p> </div> <div style="background: #f8d7da; padding: 15px; \
# border-radius: 5px; margin: 20px 0;"> <h3 style="margin-top: 0;">💰 Información \ del Pago:</h3>
# <p><strong>Vehículo:</strong> {variables['vehiculo']}</p> <p><strong>Monto:</strong> {variables['monto']}</p>
# <p><strong>Fecha de vencimiento:</strong> \ {variables['fecha']}</p> <p><strong>Días de atraso:</strong> {variables \
# margin-top: 30px;"> <p style="color: #666;"> {variables['nombre_empresa']}<br> 📞 {variables['telefono_empresa']} </p>
# </div> </div> </div> </div> """ ), }, TipoNotificacionCliente.CONFIRMACION_PAGO: { "asunto": f"✅ Pago recibido - Cuota
# #{variables['cuota']}", "cuerpo_html": ( f""" <div style="font-family: Arial, sans-serif; max-width: \ 600px; margin: 0
# auto;"> <div style="background: #28a745; color: white; padding: \ 20px; text-align: center;"> <h1>✅ Pago Confirmado</h1> <p
# style="margin: 0;">¡Gracias por tu pago!</p> </div> <div style="padding: 20px; background: #f8f9fa;"> <div
# style="background: white; padding: 20px; \ border-radius: 8px;"> <h2>¡Gracias {variables['nombre']}!</h2> <div
# style="background: #d4edda; border: 1px \ solid #c3e6cb; padding: 15px; border-radius: 5px; \ margin: 20px 0;">
# #e3f2fd; padding: 15px; \ border-radius: 5px; margin: 20px 0;"> <h3 style="margin-top: 0;">💰 Detalles del Pago:</h3>
# <p><strong>Vehículo:</strong> {variables['vehiculo']}</p> <p><strong>Monto pagado:</strong> {variables['monto']}</p>
# <p><strong>Cuota #:</strong> {variables['cuota']}</p> <p><strong>Estado:</strong> ✅ Pagada</p> </div> <p>Tu cuenta está al
# día. ¡Gracias por tu puntualidad!</p> <div style="text-align: center; margin-top: 30px;"> <p style="color: #666;">
# {variables['nombre_empresa']}<br> 📞 {variables['telefono_empresa']} </p> </div> </div> </div> </div> """ ), }, } return
# templates.get( tipo, { "asunto": "Notificación del sistema", "cuerpo_html": "<p>Notificación automática del sistema.</p>",
# }, ) def _obtener_template_whatsapp( self, tipo: TipoNotificacionCliente, cliente_data: Dict ) -> Dict[str, str]:
# cliente_data["nombre"].split()[0] cuota = cliente_data["cuota_numero"] monto = f"${cliente_data['monto_cuota']:,.0f}" fecha
# cliente_data["vehiculo"] templates = { TipoNotificacionCliente.RECORDATORIO_3_DIAS: { "mensaje": ( f"""👋 Hola {nombre}, Te
# 💳Dudas? Responde este mensaje.Gracias,Financiamiento Automotriz""" ) }, TipoNotificacionCliente.RECORDATORIO_1_DIA: {
# "mensaje": ( f"""⏰ {nombre}, tu cuota vence MAÑANA Vehículo: {vehiculo} Monto: {monto} Vence: {fecha}No olvides realizar tu
# pago!Financiamiento Automotriz""" ) }, TipoNotificacionCliente.DIA_VENCIMIENTO: { "mensaje": ( f"""📅 {nombre}, tu cuota
# vence HOY {vehiculo} {monto} Vence: HOYRealiza tu pago antes de las 6:00 PM para evitar mora.Financiamiento Automotriz""" )
# }, TipoNotificacionCliente.MORA_1_DIA: { "mensaje": ( f"""⚠️ {nombre}, tu cuota está vencida {vehiculo} {monto} Días de
# Automotriz""" ) }, TipoNotificacionCliente.MORA_3_DIAS: { "mensaje": ( f"""🚨 {nombre}, URGENTE - 3 días de atraso
# {vehiculo} {monto} + mora Atraso: {dias_mora} díasContacta inmediatamente para evitar acciones legales.Responde AHORA o
# llama: 809-XXX-XXXXFinanciamiento Automotriz""" ) }, TipoNotificacionCliente.MORA_5_DIAS: { "mensaje": ( f"""🚨 {nombre},
# CRÍTICO - 5 días de atraso {vehiculo} {monto} + mora acumulada Atraso: {dias_mora} díasLTIMA OPORTUNIDAD antes de proceso
# legal.LLAMA AHORA: 809-XXX-XXXXFinanciamiento Automotriz""" ) }, TipoNotificacionCliente.CONFIRMACION_PAGO: { "mensaje": (
# f"""✅ ¡Pago confirmado!Gracias {nombre} por tu pago de {monto}. {vehiculo} Cuota #{cuota}: ✅ PAGADATu cuenta está al
# día!Financiamiento Automotriz""" ) }, } return templates.get(tipo, {"mensaje": "Notificación del sistema."}) def
# _puede_enviar_notificacion(self, cliente_id: int) -> bool: """Verificar límites anti-spam""" try: hoy = date.today() #
# Contar notificaciones enviadas hoy al cliente notificaciones_hoy = ( self.db.query(Notificacion) .filter(
# Notificacion.usuario_id == cliente_id, # Asumiendo que cliente_id = usuario_id func.date(Notificacion.creado_en) == hoy, )
# .count() ) if notificaciones_hoy >= self.LIMITE_NOTIFICACIONES_DIA: logger.warning( f"Cliente {cliente_id} alcanzó límite "
# "diario de notificaciones" ) return False # Verificar intervalo mínimo ultima_notificacion = ( self.db.query(Notificacion)
# .filter(Notificacion.usuario_id == cliente_id) .order_by(Notificacion.creado_en.desc()) .first() ) if ultima_notificacion:
# self.INTERVALO_MINIMO_HORAS * 3600 ): logger.warning( f"Cliente {cliente_id} no cumple intervalo mínimo" ) return False
# return True except Exception as e: logger.error(f"Error verificando límites: {e}") return True # En caso de error, permitir
# envío async def _registrar_en_historial( self, cliente_data: Dict, tipo: TipoNotificacionCliente, resultado: Dict, ):
# """Registrar notificación en historial completo""" try: # Registrar para cada canal intentado for canal in
# notificacion = Notificacion( usuario_id=cliente_data[ "cliente_id" ], # Asumiendo cliente_id = usuario_id tipo=tipo.value,
# categoria="CLIENTE", prioridad="NORMAL", titulo=f"Notificación {tipo.value} - {canal}", mensaje=f"Notificación enviada por
# {canal} " f"al cliente {cliente_data["nombre']}", canal=canal, estado=estado, destinatario_email=( cliente_data["email"] if
# canal == "EMAIL" else None ), destinatario_telefono=( cliente_data["telefono"] if canal == "WHATSAPP" else None ),
# destinatario_nombre=cliente_data["nombre"], extra_data=str( { "cuota_numero": cliente_data["cuota_numero"], "monto_cuota":
# cliente_data["monto_cuota"], "fecha_vencimiento": cliente_data[ "fecha_vencimiento" ].isoformat(), "tipo_notificacion":
# tipo.value, } ), ) self.db.add(notificacion) self.db.commit() except Exception as e: logger.error(f"Error registrando en
# historial: {e}") def _es_hora_reporte_diario(self) -> bool: """Verificar si es hora del reporte diario""" ahora =
# is_admin User.is_active, User.email.isnot(None), ) .all() ) # Crear reporte reporte_html = """ <h2>📊 Reporte Diario de
# reporte_html += f"<li>{error}</li>" reporte_html += "</ul>" # Enviar reporte a equipo de cobranzas for usuario in
# al equipo de cobranzas") except Exception as e: logger.error(f"Error generando reporte diario: {e}")#
# ============================================# SCHEDULER DE NOTIFICACIONES#
# ============================================class NotificationScheduler: """ ⏰ Scheduler automático de notificaciones Se
# ejecuta cada hora para procesar notificaciones pendientes """ def __init__(self): self.is_running = False async def
# ejecutar_ciclo_notificaciones( self, db: Session ) -> Dict[str, Any]: """ 🔄 Ejecutar ciclo completo de notificaciones
# Método principal que se llama desde cron/scheduler """ if self.is_running: logger.warning("⚠️ Ciclo de notificaciones ya
# automático de notificaciones") # Crear servicio de notificaciones servicio_notif = NotificacionMulticanal(db) # Procesar
# ConfigHelper return { "email_configurado": ConfigHelper.is_email_configured(db), "whatsapp_habilitado":
# Exception as e: logger.error(f"Error verificando configuración: {e}") return { "email_configurado": False,
# "whatsapp_habilitado": False, "puede_enviar_notificaciones": False, }# ============================================#
# to_email=notificacion.destinatario_email, subject=notificacion.titulo, html_content=notificacion.mensaje, ) return
# @staticmethod async def _reintentar_whatsapp(notificacion: Notificacion) -> bool: """Reintentar envío de WhatsApp""" try: #
# whatsapp_service.send_message( to_phone=notificacion.destinatario_telefono, message=notificacion.mensaje, ) return
# @staticmethod async def _notificar_admin_fallo_critico( notificacion: Notificacion, db: Session ): """Notificar a admin
# sobre fallo crítico en notificaciones""" try: # Obtener administradores admins = ( db.query(User) .filter( User.is_admin, #
# Cambio clave: rol → is_admin User.is_active, User.email.isnot(None), ) .all() ) # Crear notificación de fallo crítico for
# admin in admins: notif_admin = Notificacion( usuario_id=admin.id, tipo="FALLO_CRITICO_NOTIFICACION", categoria="SISTEMA",
# prioridad="ALTA", titulo="🚨 Fallo crítico en notificaciones", mensaje="""Fallo crítico en sistema de
# fallo crítico" ) except Exception as e: logger.error(f"Error notificando fallo crítico: {e}")#
# ============================================# CONFIGURACIÓN DE TEMPLATES WHATSAPP#
# ============================================class WhatsAppTemplateManager: """ 📝 Gestor de templates de WhatsApp Business
# API """ TEMPLATES_WHATSAPP = { "recordatorio_3_dias": { "nombre": "recordatorio_3_dias", "categoria": "MARKETING",
# "idioma": "es", "componentes": [ { "tipo": "HEADER", "formato": "TEXT", "texto": "Recordatorio de Pago", }, { "tipo":
# {{5}}\n\nPor favor realiza tu pago a tiempo. " "💳\n\n¿Dudas? Responde este mensaje." ), }, {"tipo": "FOOTER", "texto":
# "Financiamiento Automotriz"}, ], "variables": ["nombre", "cuota", "vehiculo", "fecha", "monto"], }, "mora_1_dia": {
# "nombre": "mora_1_dia", "categoria": "UTILITY", "idioma": "es", "componentes": [ { "tipo": "HEADER", "formato": "TEXT",
# "texto": "⚠️ Cuota Vencida", }, { "tipo": "BODY", "texto": ( "{{1}}, tu cuota #{{2}} está vencida.\n\n" "🚗 Vehículo:
# ayuda? Responde este mensaje." ), }, {"tipo": "FOOTER", "texto": "Financiamiento Automotriz"}, ], "variables": ["nombre",
# "cuota", "vehiculo", "monto", "dias_mora"], }, "confirmacion_pago": { "nombre": "confirmacion_pago", "categoria":
# "UTILITY", "idioma": "es", "componentes": [ { "tipo": "HEADER", "formato": "TEXT", "texto": "✅ Pago Confirmado", }, {
# PAGADA\n\n¡Tu cuenta está al día!" ), }, {"tipo": "FOOTER", "texto": "Financiamiento Automotriz"}, ], "variables":
# ["nombre", "monto", "vehiculo", "cuota"], }, } @staticmethod def obtener_template_para_aprobacion(template_name: str) ->
# Dict: """ Obtener template formateado para envío a Meta para aprobación """ template =
# WhatsAppTemplateManager.TEMPLATES_WHATSAPP.get( template_name ) if not template: return {} return { "name":
# template["nombre"], "category": template["categoria"], "language": template["idioma"], "components":
# template["componentes"], "status": "PENDING_APPROVAL", "descripcion": f"Template para {template_name.replace( '_', '
# return [ { "nombre": nombre, "descripcion": template["categoria"], "variables": template["variables"], "estado":
# "PENDIENTE_APROBACION", # En producción sería dinámico } for nombre, template in
# WhatsAppTemplateManager.TEMPLATES_WHATSAPP.items() ]# ============================================# INSTANCIA GLOBAL DEL
# SCHEDULER# ============================================notification_scheduler = NotificationScheduler()
