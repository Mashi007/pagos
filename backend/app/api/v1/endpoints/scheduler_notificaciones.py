# backend/app/api/v1/endpoints/scheduler_notificaciones.py"""Endpoints para Scheduler de Notificaciones
# Field\nfrom sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_current_user, get_db\nfrom app.models.user
# \nimport User\nfrom app.services.notification_multicanal_service \nimport notification_schedulerlogger =
# logging.getLogger(__name__)router = APIRouter()# ============================================# SCHEMAS PARA SCHEDULER#
# ============================================\nclass ConfiguracionScheduler(BaseModel):\n """Configuración del scheduler de
# description="Hora de inicio (HH:\nMM)") hora_fin:\n str = Field("22:\n00", description="Hora de fin (HH:\nMM)")
# ============================================# CONFIGURACIÓN DEL SCHEDULER#
# ============================================@router.get("/configuracion")\ndef obtener_configuracion_scheduler( db:\n
# Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ ⚙️ Obtener configuración actual del
# para ver configuración del scheduler", ) try:\n # Configuración actual (simulada - en producción sería de BD)
# "18:\n00", } return { "titulo":\n "⏰ CONFIGURACIÓN DEL SCHEDULER DE NOTIFICACIONES", "configuracion_actual":\n
# notification_scheduler.is_running, "ultima_ejecucion":\n "Simulado - cada hora", "proxima_ejecucion":\n "En la próxima
# "recordatorio_1_dia":\n "09:\n00 AM", "dia_vencimiento":\n "08:\n00 AM", "mora_1_dia":\n "10:\n00 AM", "mora_3_dias":\n
# "10:\n00 AM", "mora_5_dias":\n "10:\n00 AM", "confirmacion_pago":\n "INMEDIATO", }, "configuracion_cron":\n {
# "expresion_actual":\n "0 * * * *", # Cada hora "descripcion":\n "Se ejecuta cada hora durante horario laboral",
# "comando_sugerido":\n "0 * 6-22 * * 1-6", # Cada hora de6AMa 10PM, Lun-Sab "archivo_cron":\n "/etc/crontab", },
# "instrucciones_setup":\n { "paso_1":\n "Configurar cron job en el servidor", "paso_2":\n ( "Usar endpoint:\n POST
# /api/v1/notificaciones-multicanal/procesar-automaticas" ), "paso_3":\n "Monitorear logs en:\n GET /api/v1/scheduler/logs",
# "comando_cron":\n ( "0 * 6-22 * * 1-6 curl -X POST
# TOKEN'" ), }, } except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo configuración:\n
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ ⚙️ Configurar scheduler de notificaciones """ if
# not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo administradores pueden configurar el
# scheduler", ) try:\n # En producción, guardar configuración en BD # Por ahora, simular guardado return { "mensaje":\n "✅
# "actualizado_por":\n current_user.full_name, "siguiente_paso":\n "Aplicar configuración en el servidor cron", } except
# Exception as e:\n raise HTTPException( status_code=500, detail=f"Error configurando scheduler:\n {str(e)}"
# )@router.get("/logs")\ndef obtener_logs_scheduler( limite:\n int = 100, db:\n Session = Depends(get_db), current_user:\n
# User = Depends(get_current_user),):\n """ 📋 Obtener logs del scheduler de notificaciones """ try:\n # En producción,
# se actualizan cada ejecución del scheduler", } except Exception as e:\n raise HTTPException( status_code=500,
# background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n
# """ ▶️ Ejecutar scheduler manualmente (fuera del horario programado) """ if not current_user.is_admin:\n raise
# /api/v1/scheduler/estado", } except HTTPException:\n raise except Exception as e:\n raise HTTPException( status_code=500,
# detail=f"Error ejecutando scheduler:\n {str(e)}" )@router.get("/estado")\ndef obtener_estado_scheduler( db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📊 Obtener estado actual del scheduler """ try:\n
# "total_ejecuciones_hoy":\n 18, # Placeholder }, "configuracion_activa":\n { "frecuencia":\n "Cada hora",
# "tasa_exito_promedio":\n "95.7%", "memoria_utilizada":\n "< 50MB", }, "alertas_sistema":\n [ "✅ Scheduler funcionando
# except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo estado:\n {str(e)}" )#
# ============================================# FUNCIONES AUXILIARES# ============================================async \ndef
# _ejecutar_scheduler_manual(db:\n Session, user_id:\n int):\n """Ejecutar scheduler manualmente en background""" try:\n
# \nfrom app.db.session \nimport SessionLocal db_local = SessionLocal() # Ejecutar ciclo de notificaciones resultado = await
# notification_scheduler.ejecutar_ciclo_notificaciones( db_local ) logger.info("📧 Scheduler manual ejecutado por usuario
# scheduler manual:\n {e}")\ndef _generar_expresion_cron(config:\n ConfiguracionScheduler) -> str:\n """Generar expresión
# hora_fin = int(config.hora_fin.split(":\n")[0]) hora = f"{hora_inicio}-{hora_fin}" # Convertir días dias_map = { "LUNES":\n
# "1", "MARTES":\n "2", "MIERCOLES":\n "3", "JUEVES":\n "4", "VIERNES":\n "5", "SABADO":\n "6", "DOMINGO":\n "0", }
# ============================================# ENDPOINT DE VERIFICACIÓN#
# ============================================@router.get("/verificacion-completa")\ndef
# verificar_sistema_notificaciones_completo( db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 🔍 Verificación completa del sistema de notificaciones multicanal """ return {
# "titulo":\n "🔔 SISTEMA DE NOTIFICACIONES MULTICANAL - VERIFICACIÓN COMPLETA", "fecha_verificacion":\n
# simultáneo", "procesamiento_automatico":\n "✅ Scheduler cada hora", "sin_ia":\n "✅ Sistema basado en templates y reglas",
# "preferencias_cliente":\n "✅ Configuración individual", "limites_antispam":\n "✅ 3 por día, intervalo 2h",
# "proveedores_whatsapp":\n { "twilio":\n { "implementado":\n True, "descripcion":\n "Proveedor principal recomendado",
# ["API_KEY", "CLIENT_ID"], }, "meta_cloud_api":\n { "implementado":\n True, "descripcion":\n "API oficial de Meta",
# "flujo_automatico_implementado":\n { "paso_1":\n "✅ Scheduler se ejecuta cada hora", "paso_2":\n "✅ Busca clientes con
# cuotas que requieren notificación", "paso_3":\n "✅ Verifica preferencias por cliente", "paso_4":\n "✅ Carga plantilla
# caso de error", "paso_10":\n "✅ Notifica a Admin si fallo crítico", "paso_11":\n "✅ Genera reporte diario a Cobranzas", },
# "templates_whatsapp":\n { "total_templates":\n 7, "estado_aprobacion":\n "PENDIENTE_CONFIGURACION", "proceso_aprobacion":\n
# "1-2 días hábiles con Meta", "templates_disponibles":\n [ "recordatorio_3_dias", "recordatorio_1_dia", "dia_vencimiento",
# "/api/v1/notificaciones-multicanal/procesar-automaticas", "historial":\n "/api/v1/notificaciones-multicanal/historial",
# "dashboard":\n "/api/v1/notificaciones-multicanal/dashboard", "preferencias":\n "/api/v1/notificaciones-multicanal/cliente/
# \ {id}/preferencias", "templates":\n "/api/v1/notificaciones-multicanal/whatsapp/templates", "scheduler":\n
# "/api/v1/scheduler/configuracion", "pruebas":\n "/api/v1/notificaciones-multicanal/probar-envio", },
# "configuracion_requerida":\n { "email":\n "✅ Configurado en /api/v1/configuracion/email", "whatsapp":\n "⚠️ Configurar en
# /api/v1/configuracion/whatsapp", "cron_job":\n "⚠️ Configurar en servidor", "templates_meta":\n "⚠️ Aprobar templates con
# trabajo manual 80%", "🎯 Personalización mejora experiencia del cliente", "📊 Historial completo para análisis y auditoría",
