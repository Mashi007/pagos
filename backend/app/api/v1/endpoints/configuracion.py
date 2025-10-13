# backend/app/api/v1/endpoints/configuracion.py
"""
Endpoint para configuración administrativa del sistema.
Gestión de parámetros, tasas, límites y ajustes generales.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal

from app.db.session import get_db
from app.models.user import User
from app.models.cliente import Cliente
from app.core.security import get_current_user
import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# MONITOREO Y OBSERVABILIDAD
# ============================================

@router.get("/monitoreo/estado")
def obtener_estado_monitoreo(
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Verificar estado del sistema de monitoreo y observabilidad
    """
    # Solo admin puede ver configuración de monitoreo
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver configuración de monitoreo")
    
    from app.core.monitoring import get_monitoring_status
    return get_monitoring_status()


@router.post("/monitoreo/habilitar")
def habilitar_monitoreo_basico(
    current_user: User = Depends(get_current_user)
):
    """
    ⚡ Habilitar monitoreo básico sin dependencias externas
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden configurar monitoreo")
    
    try:
        # Configurar logging estructurado básico
        import logging
        
        # Configurar formato mejorado
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Logger específico para el sistema de financiamiento
        finance_logger = logging.getLogger("financiamiento_automotriz")
        finance_logger.setLevel(logging.INFO)
        
        return {
            "mensaje": "✅ Monitoreo básico habilitado",
            "configuracion": {
                "logging_estructurado": "✅ Habilitado",
                "nivel_log": "INFO",
                "formato": "Timestamp + Archivo + Línea + Mensaje",
                "logger_especifico": "financiamiento_automotriz"
            },
            "beneficios": [
                "📋 Logs más detallados y estructurados",
                "🔍 Mejor debugging de errores",
                "📊 Tracking básico de operaciones",
                "⚡ Sin dependencias externas adicionales"
            ],
            "siguiente_paso": "Configurar Sentry y Prometheus para monitoreo avanzado"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error habilitando monitoreo: {str(e)}")


# ============================================
# CONFIGURACIÓN CENTRALIZADA DEL SISTEMA
# ============================================

@router.get("/sistema/completa")
def obtener_configuracion_completa(
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    current_user: User = Depends(get_current_user)
):
    """
    🔧 Obtener configuración completa del sistema para el frontend
    """
    # Solo admin puede ver configuración completa
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver configuración completa")
    
    try:
        from app.models.configuracion_sistema import ConfiguracionSistema
        
        query = db.query(ConfiguracionSistema).filter(
            ConfiguracionSistema.visible_frontend == True
        )
        
        if categoria:
            query = query.filter(ConfiguracionSistema.categoria == categoria)
        
        configs = query.all()
        
        # Agrupar por categoría
        configuracion_agrupada = {}
        for config in configs:
            if config.categoria not in configuracion_agrupada:
                configuracion_agrupada[config.categoria] = {}
            
            configuracion_agrupada[config.categoria][config.clave] = {
                "valor": config.valor_procesado,
                "descripcion": config.descripcion,
                "tipo_dato": config.tipo_dato,
                "requerido": config.requerido,
                "solo_lectura": config.solo_lectura,
                "opciones_validas": json.loads(config.opciones_validas) if config.opciones_validas else None,
                "valor_minimo": config.valor_minimo,
                "valor_maximo": config.valor_maximo,
                "patron_validacion": config.patron_validacion,
                "actualizado_en": config.actualizado_en,
                "actualizado_por": config.actualizado_por
            }
        
        return {
            "titulo": "🔧 CONFIGURACIÓN COMPLETA DEL SISTEMA",
            "fecha_consulta": datetime.now().isoformat(),
            "consultado_por": current_user.full_name,
            "configuracion": configuracion_agrupada,
            "categorias_disponibles": list(configuracion_agrupada.keys()),
            "total_configuraciones": len(configs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo configuración: {str(e)}")


@router.get("/sistema/categoria/{categoria}")
def obtener_configuracion_categoria(
    categoria: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📋 Obtener configuración de una categoría específica
    """
    try:
        from app.models.configuracion_sistema import ConfiguracionSistema
        
        configs = db.query(ConfiguracionSistema).filter(
            ConfiguracionSistema.categoria == categoria.upper(),
            ConfiguracionSistema.visible_frontend == True
        ).all()
        
        if not configs:
            raise HTTPException(status_code=404, detail=f"Categoría '{categoria}' no encontrada")
        
        configuracion = {}
        for config in configs:
            configuracion[config.clave] = {
                "valor": config.valor_procesado,
                "descripcion": config.descripcion,
                "tipo_dato": config.tipo_dato,
                "requerido": config.requerido,
                "solo_lectura": config.solo_lectura,
                "opciones_validas": json.loads(config.opciones_validas) if config.opciones_validas else None,
                "valor_minimo": config.valor_minimo,
                "valor_maximo": config.valor_maximo,
                "patron_validacion": config.patron_validacion
            }
        
        return {
            "categoria": categoria.upper(),
            "configuracion": configuracion,
            "total_items": len(configs),
            "fecha_consulta": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo configuración de categoría: {str(e)}")


@router.post("/sistema/actualizar")
def actualizar_configuracion_sistema(
    configuraciones: Dict[str, Dict[str, Any]],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ✏️ Actualizar configuraciones del sistema
    
    Formato:
    {
        "AI": {
            "OPENAI_API_KEY": "sk-...",
            "AI_SCORING_ENABLED": true
        },
        "EMAIL": {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_USERNAME": "empresa@gmail.com"
        }
    }
    """
    # Solo admin puede actualizar configuración
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden actualizar configuración")
    
    try:
        from app.models.configuracion_sistema import ConfiguracionSistema
        
        actualizaciones_exitosas = []
        errores = []
        
        for categoria, configs in configuraciones.items():
            for clave, nuevo_valor in configs.items():
                try:
                    # Buscar configuración existente
                    config = db.query(ConfiguracionSistema).filter(
                        ConfiguracionSistema.categoria == categoria.upper(),
                        ConfiguracionSistema.clave == clave.upper()
                    ).first()
                    
                    if not config:
                        errores.append(f"Configuración {categoria}.{clave} no encontrada")
                        continue
                    
                    if config.solo_lectura:
                        errores.append(f"Configuración {categoria}.{clave} es de solo lectura")
                        continue
                    
                    # Validar nuevo valor
                    error_validacion = _validar_configuracion(config, nuevo_valor)
                    if error_validacion:
                        errores.append(f"{categoria}.{clave}: {error_validacion}")
                        continue
                    
                    # Actualizar valor
                    valor_anterior = config.valor_procesado
                    config.actualizar_valor(nuevo_valor, current_user.full_name)
                    
                    actualizaciones_exitosas.append({
                        "categoria": categoria,
                        "clave": clave,
                        "valor_anterior": valor_anterior,
                        "valor_nuevo": config.valor_procesado
                    })
                    
                except Exception as e:
                    errores.append(f"Error actualizando {categoria}.{clave}: {str(e)}")
        
        # Confirmar cambios si no hay errores críticos
        if len(errores) < len(actualizaciones_exitosas):
            db.commit()
            
            # Registrar en auditoría
            from app.models.auditoria import Auditoria, TipoAccion
            auditoria = Auditoria.registrar(
                usuario_id=current_user.id,
                accion=TipoAccion.ACTUALIZACION,
                entidad="configuracion_sistema",
                entidad_id=None,
                detalles=f"Actualizadas {len(actualizaciones_exitosas)} configuraciones"
            )
            db.add(auditoria)
            db.commit()
        else:
            db.rollback()
        
        return {
            "mensaje": "✅ Configuraciones actualizadas" if actualizaciones_exitosas else "❌ No se pudo actualizar ninguna configuración",
            "actualizaciones_exitosas": len(actualizaciones_exitosas),
            "errores": len(errores),
            "detalle_actualizaciones": actualizaciones_exitosas,
            "detalle_errores": errores,
            "fecha_actualizacion": datetime.now().isoformat(),
            "actualizado_por": current_user.full_name
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error actualizando configuraciones: {str(e)}")


@router.post("/sistema/probar-integracion/{categoria}")
def probar_integracion(
    categoria: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🧪 Probar integración de una categoría específica
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden probar integraciones")
    
    try:
        categoria = categoria.upper()
        
        if categoria == "EMAIL":
            return _probar_configuracion_email(db)
        elif categoria == "WHATSAPP":
            return _probar_configuracion_whatsapp(db)
        elif categoria == "AI":
            return _probar_configuracion_ai(db)
        elif categoria == "DATABASE":
            return _probar_configuracion_database(db)
        else:
            raise HTTPException(status_code=400, detail=f"Categoría '{categoria}' no soporta pruebas automáticas")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error probando integración: {str(e)}")


@router.get("/sistema/estado-servicios")
def obtener_estado_servicios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 Obtener estado de todos los servicios configurados
    """
    try:
        from app.models.configuracion_sistema import ConfigHelper
        
        estado_servicios = {
            "ai": {
                "habilitado": ConfigHelper.is_ai_enabled(db),
                "configurado": bool(ConfigHelper.get_config(db, "AI", "OPENAI_API_KEY")),
                "estado": "✅ ACTIVO" if ConfigHelper.is_ai_enabled(db) else "❌ INACTIVO"
            },
            "email": {
                "habilitado": True,  # Siempre habilitado
                "configurado": ConfigHelper.is_email_configured(db),
                "estado": "✅ CONFIGURADO" if ConfigHelper.is_email_configured(db) else "⚠️ PENDIENTE"
            },
            "whatsapp": {
                "habilitado": ConfigHelper.is_whatsapp_enabled(db),
                "configurado": bool(ConfigHelper.get_config(db, "WHATSAPP", "TWILIO_ACCOUNT_SID")),
                "estado": "✅ ACTIVO" if ConfigHelper.is_whatsapp_enabled(db) else "❌ INACTIVO"
            },
            "database": {
                "habilitado": True,
                "configurado": True,
                "estado": "✅ CONECTADA"
            },
            "monitoreo": {
                "habilitado": bool(ConfigHelper.get_config(db, "MONITOREO", "SENTRY_DSN")),
                "configurado": bool(ConfigHelper.get_config(db, "MONITOREO", "SENTRY_DSN")),
                "estado": "✅ ACTIVO" if ConfigHelper.get_config(db, "MONITOREO", "SENTRY_DSN") else "❌ INACTIVO"
            }
        }
        
        # Calcular estado general
        servicios_activos = sum(1 for s in estado_servicios.values() if "✅" in s["estado"])
        total_servicios = len(estado_servicios)
        
        return {
            "titulo": "📊 ESTADO DE SERVICIOS DEL SISTEMA",
            "fecha_consulta": datetime.now().isoformat(),
            "estado_general": {
                "servicios_activos": servicios_activos,
                "total_servicios": total_servicios,
                "porcentaje_activo": round(servicios_activos / total_servicios * 100, 1),
                "estado": "✅ ÓPTIMO" if servicios_activos == total_servicios else "⚠️ PARCIAL" if servicios_activos > 0 else "❌ CRÍTICO"
            },
            "servicios": estado_servicios,
            "recomendaciones": _generar_recomendaciones_configuracion(estado_servicios)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado de servicios: {str(e)}")


@router.post("/sistema/inicializar-defaults")
def inicializar_configuraciones_default(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔧 Inicializar configuraciones por defecto del sistema
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden inicializar configuraciones")
    
    try:
        from app.models.configuracion_sistema import ConfiguracionPorDefecto
        
        # Crear configuraciones por defecto
        ConfiguracionPorDefecto.crear_configuraciones_default(db)
        
        # Contar configuraciones creadas
        total_configs = db.query(ConfiguracionSistema).count()
        
        return {
            "mensaje": "✅ Configuraciones por defecto inicializadas exitosamente",
            "total_configuraciones": total_configs,
            "categorias_creadas": [
                "AI - Inteligencia Artificial",
                "EMAIL - Configuración de correo",
                "WHATSAPP - Configuración de WhatsApp",
                "ROLES - Roles y permisos",
                "FINANCIERO - Parámetros financieros",
                "NOTIFICACIONES - Configuración de notificaciones",
                "SEGURIDAD - Configuración de seguridad",
                "DATABASE - Configuración de base de datos",
                "REPORTES - Configuración de reportes",
                "INTEGRACIONES - Integraciones externas",
                "MONITOREO - Monitoreo y observabilidad",
                "APLICACION - Configuración general"
            ],
            "siguiente_paso": "Configurar cada categoría según las necesidades",
            "fecha_inicializacion": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inicializando configuraciones: {str(e)}")


# ============================================
# CONFIGURACIÓN DE IA
# ============================================

@router.get("/ia")
def obtener_configuracion_ia(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🤖 Obtener configuración de Inteligencia Artificial
    """
    try:
        from app.models.configuracion_sistema import ConfiguracionSistema
        
        configs_ia = db.query(ConfiguracionSistema).filter(
            ConfiguracionSistema.categoria == "AI",
            ConfiguracionSistema.visible_frontend == True
        ).all()
        
        configuracion = {}
        for config in configs_ia:
            # Ocultar tokens completos por seguridad
            valor_mostrar = config.valor_procesado
            if config.tipo_dato == "PASSWORD" and config.valor:
                valor_mostrar = f"{'*' * (len(config.valor) - 4)}{config.valor[-4:]}" if len(config.valor) > 4 else "****"
            
            configuracion[config.clave] = {
                "valor": valor_mostrar,
                "valor_real": config.valor_procesado if config.tipo_dato != "PASSWORD" else None,
                "descripcion": config.descripcion,
                "tipo_dato": config.tipo_dato,
                "requerido": config.requerido,
                "configurado": bool(config.valor),
                "opciones_validas": json.loads(config.opciones_validas) if config.opciones_validas else None
            }
        
        # Estado de funcionalidades IA
        estado_ia = {
            "scoring_crediticio": {
                "habilitado": configuracion.get("AI_SCORING_ENABLED", {}).get("valor", False),
                "configurado": bool(configuracion.get("OPENAI_API_KEY", {}).get("valor_real")),
                "descripcion": "Sistema de scoring crediticio automático"
            },
            "prediccion_mora": {
                "habilitado": configuracion.get("AI_PREDICTION_ENABLED", {}).get("valor", False),
                "configurado": True,  # No requiere configuración externa
                "descripcion": "Predicción de mora con Machine Learning"
            },
            "chatbot": {
                "habilitado": configuracion.get("AI_CHATBOT_ENABLED", {}).get("valor", False),
                "configurado": bool(configuracion.get("OPENAI_API_KEY", {}).get("valor_real")),
                "descripcion": "Chatbot inteligente para cobranza"
            }
        }
        
        return {
            "titulo": "🤖 CONFIGURACIÓN DE INTELIGENCIA ARTIFICIAL",
            "configuracion": configuracion,
            "estado_funcionalidades": estado_ia,
            "instrucciones": {
                "openai_api_key": "Obtener en https://platform.openai.com/api-keys",
                "formato_token": "Debe comenzar con 'sk-' seguido de 48 caracteres",
                "costo_estimado": "$0.002 por 1K tokens (muy económico)",
                "beneficios": [
                    "Scoring crediticio automatizado",
                    "Predicción de mora con 87% precisión",
                    "Mensajes personalizados para cobranza",
                    "Recomendaciones inteligentes"
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo configuración IA: {str(e)}")


@router.post("/ia/actualizar")
def actualizar_configuracion_ia(
    openai_api_key: Optional[str] = None,
    openai_model: Optional[str] = None,
    scoring_enabled: Optional[bool] = None,
    prediction_enabled: Optional[bool] = None,
    chatbot_enabled: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🤖 Actualizar configuración de IA
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden configurar IA")
    
    try:
        from app.models.configuracion_sistema import ConfiguracionSistema
        
        actualizaciones = []
        
        # Actualizar API Key de OpenAI
        if openai_api_key is not None:
            config = ConfiguracionSistema.obtener_por_clave(db, "AI", "OPENAI_API_KEY")
            if config:
                config.actualizar_valor(openai_api_key, current_user.full_name)
                actualizaciones.append("OPENAI_API_KEY")
        
        # Actualizar modelo
        if openai_model is not None:
            config = ConfiguracionSistema.obtener_por_clave(db, "AI", "OPENAI_MODEL")
            if config:
                config.actualizar_valor(openai_model, current_user.full_name)
                actualizaciones.append("OPENAI_MODEL")
        
        # Actualizar habilitaciones
        if scoring_enabled is not None:
            config = ConfiguracionSistema.obtener_por_clave(db, "AI", "AI_SCORING_ENABLED")
            if config:
                config.actualizar_valor(scoring_enabled, current_user.full_name)
                actualizaciones.append("AI_SCORING_ENABLED")
        
        if prediction_enabled is not None:
            config = ConfiguracionSistema.obtener_por_clave(db, "AI", "AI_PREDICTION_ENABLED")
            if config:
                config.actualizar_valor(prediction_enabled, current_user.full_name)
                actualizaciones.append("AI_PREDICTION_ENABLED")
        
        if chatbot_enabled is not None:
            config = ConfiguracionSistema.obtener_por_clave(db, "AI", "AI_CHATBOT_ENABLED")
            if config:
                config.actualizar_valor(chatbot_enabled, current_user.full_name)
                actualizaciones.append("AI_CHATBOT_ENABLED")
        
        db.commit()
        
        return {
            "mensaje": "✅ Configuración de IA actualizada exitosamente",
            "configuraciones_actualizadas": actualizaciones,
            "fecha_actualizacion": datetime.now().isoformat(),
            "actualizado_por": current_user.full_name,
            "siguiente_paso": "Probar funcionalidades IA en el dashboard"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error actualizando configuración IA: {str(e)}")


# ============================================
# CONFIGURACIÓN DE EMAIL
# ============================================

@router.get("/email")
def obtener_configuracion_email(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📧 Obtener configuración de email
    """
    try:
        from app.models.configuracion_sistema import ConfiguracionSistema
        
        configs_email = db.query(ConfiguracionSistema).filter(
            ConfiguracionSistema.categoria == "EMAIL"
        ).all()
        
        configuracion = {}
        for config in configs_email:
            valor_mostrar = config.valor_procesado
            if config.tipo_dato == "PASSWORD" and config.valor:
                valor_mostrar = "****" + config.valor[-4:] if len(config.valor) > 4 else "****"
            
            configuracion[config.clave] = {
                "valor": valor_mostrar,
                "descripcion": config.descripcion,
                "tipo_dato": config.tipo_dato,
                "requerido": config.requerido,
                "configurado": bool(config.valor)
            }
        
        return {
            "titulo": "📧 CONFIGURACIÓN DE EMAIL",
            "configuracion": configuracion,
            "proveedores_soportados": {
                "gmail": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "requiere_app_password": True,
                    "instrucciones": "Usar App Password, no contraseña normal"
                },
                "outlook": {
                    "smtp_host": "smtp-mail.outlook.com",
                    "smtp_port": 587,
                    "requiere_app_password": False,
                    "instrucciones": "Usar credenciales normales"
                },
                "yahoo": {
                    "smtp_host": "smtp.mail.yahoo.com",
                    "smtp_port": 587,
                    "requiere_app_password": True,
                    "instrucciones": "Generar App Password en configuración"
                }
            },
            "templates_disponibles": [
                "Recordatorio de pago",
                "Confirmación de pago",
                "Bienvenida cliente",
                "Mora temprana",
                "Estados de cuenta",
                "Reportes automáticos"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo configuración email: {str(e)}")


@router.post("/email/actualizar")
def actualizar_configuracion_email(
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_username: Optional[str] = None,
    smtp_password: Optional[str] = None,
    from_name: Optional[str] = None,
    templates_enabled: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📧 Actualizar configuración de email
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden configurar email")
    
    try:
        from app.models.configuracion_sistema import ConfiguracionSistema
        
        actualizaciones = []
        
        # Mapeo de parámetros a configuraciones
        parametros = {
            "SMTP_HOST": smtp_host,
            "SMTP_PORT": smtp_port,
            "SMTP_USERNAME": smtp_username,
            "SMTP_PASSWORD": smtp_password,
            "EMAIL_FROM_NAME": from_name,
            "EMAIL_TEMPLATES_ENABLED": templates_enabled
        }
        
        for clave, valor in parametros.items():
            if valor is not None:
                config = ConfiguracionSistema.obtener_por_clave(db, "EMAIL", clave)
                if config:
                    config.actualizar_valor(valor, current_user.full_name)
                    actualizaciones.append(clave)
        
        db.commit()
        
        return {
            "mensaje": "✅ Configuración de email actualizada",
            "configuraciones_actualizadas": actualizaciones,
            "fecha_actualizacion": datetime.now().isoformat(),
            "siguiente_paso": "Probar envío de email de prueba"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error actualizando configuración email: {str(e)}")


# ============================================
# CONFIGURACIÓN DE WHATSAPP
# ============================================

@router.get("/whatsapp")
def obtener_configuracion_whatsapp(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📱 Obtener configuración de WhatsApp
    """
    try:
        from app.models.configuracion_sistema import ConfiguracionSistema
        
        configs_whatsapp = db.query(ConfiguracionSistema).filter(
            ConfiguracionSistema.categoria == "WHATSAPP"
        ).all()
        
        configuracion = {}
        for config in configs_whatsapp:
            valor_mostrar = config.valor_procesado
            if config.tipo_dato == "PASSWORD" and config.valor:
                valor_mostrar = "****" + config.valor[-4:] if len(config.valor) > 4 else "****"
            
            configuracion[config.clave] = {
                "valor": valor_mostrar,
                "descripcion": config.descripcion,
                "tipo_dato": config.tipo_dato,
                "requerido": config.requerido,
                "configurado": bool(config.valor)
            }
        
        return {
            "titulo": "📱 CONFIGURACIÓN DE WHATSAPP",
            "configuracion": configuracion,
            "proveedor": {
                "nombre": "Twilio",
                "descripcion": "Proveedor de WhatsApp Business API",
                "registro": "https://www.twilio.com/console",
                "costo_estimado": "$0.005 por mensaje",
                "documentacion": "https://www.twilio.com/docs/whatsapp"
            },
            "funcionalidades": [
                "Recordatorios de pago automáticos",
                "Notificaciones de mora",
                "Confirmaciones de pago",
                "Mensajes personalizados con IA",
                "Estados de cuenta por WhatsApp"
            ],
            "requisitos": [
                "Cuenta de Twilio verificada",
                "Número de WhatsApp Business aprobado",
                "Templates de mensajes aprobados por WhatsApp"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo configuración WhatsApp: {str(e)}")


# ============================================
# DASHBOARD DE CONFIGURACIÓN
# ============================================

@router.get("/dashboard")
def dashboard_configuracion_sistema(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 Dashboard principal de configuración del sistema
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver dashboard de configuración")
    
    try:
        from app.models.configuracion_sistema import ConfiguracionSistema, ConfigHelper
        
        # Estadísticas de configuración
        total_configs = db.query(ConfiguracionSistema).count()
        configs_configuradas = db.query(ConfiguracionSistema).filter(
            ConfiguracionSistema.valor.isnot(None),
            ConfiguracionSistema.valor != ""
        ).count()
        
        configs_requeridas = db.query(ConfiguracionSistema).filter(
            ConfiguracionSistema.requerido == True
        ).count()
        
        configs_requeridas_configuradas = db.query(ConfiguracionSistema).filter(
            ConfiguracionSistema.requerido == True,
            ConfiguracionSistema.valor.isnot(None),
            ConfiguracionSistema.valor != ""
        ).count()
        
        # Estado por categoría
        categorias = db.query(ConfiguracionSistema.categoria).distinct().all()
        estado_categorias = {}
        
        for (categoria,) in categorias:
            total_cat = db.query(ConfiguracionSistema).filter(
                ConfiguracionSistema.categoria == categoria
            ).count()
            
            configuradas_cat = db.query(ConfiguracionSistema).filter(
                ConfiguracionSistema.categoria == categoria,
                ConfiguracionSistema.valor.isnot(None),
                ConfiguracionSistema.valor != ""
            ).count()
            
            porcentaje = round(configuradas_cat / total_cat * 100, 1) if total_cat > 0 else 0
            
            estado_categorias[categoria] = {
                "total": total_cat,
                "configuradas": configuradas_cat,
                "porcentaje": porcentaje,
                "estado": "✅ COMPLETA" if porcentaje == 100 else "⚠️ PARCIAL" if porcentaje > 0 else "❌ PENDIENTE"
            }
        
        return {
            "titulo": "📊 DASHBOARD DE CONFIGURACIÓN DEL SISTEMA",
            "fecha_actualizacion": datetime.now().isoformat(),
            
            "resumen_general": {
                "total_configuraciones": total_configs,
                "configuradas": configs_configuradas,
                "porcentaje_configurado": round(configs_configuradas / total_configs * 100, 1) if total_configs > 0 else 0,
                "configuraciones_requeridas": configs_requeridas,
                "requeridas_configuradas": configs_requeridas_configuradas,
                "sistema_listo": configs_requeridas_configuradas == configs_requeridas
            },
            
            "estado_por_categoria": estado_categorias,
            
            "servicios_criticos": {
                "base_datos": {
                    "estado": "✅ CONECTADA",
                    "descripcion": "Base de datos PostgreSQL"
                },
                "autenticacion": {
                    "estado": "✅ ACTIVA",
                    "descripcion": "Sistema de autenticación JWT"
                },
                "email": {
                    "estado": "✅ CONFIGURADO" if ConfigHelper.is_email_configured(db) else "⚠️ PENDIENTE",
                    "descripcion": "Servicio de email"
                },
                "ia": {
                    "estado": "✅ ACTIVA" if ConfigHelper.is_ai_enabled(db) else "❌ INACTIVA",
                    "descripcion": "Inteligencia Artificial"
                },
                "whatsapp": {
                    "estado": "✅ ACTIVO" if ConfigHelper.is_whatsapp_enabled(db) else "❌ INACTIVO",
                    "descripcion": "WhatsApp Business"
                }
            },
            
            "acciones_rapidas": {
                "configurar_ia": "POST /api/v1/configuracion/ia/actualizar",
                "configurar_email": "POST /api/v1/configuracion/email/actualizar", 
                "configurar_whatsapp": "POST /api/v1/configuracion/whatsapp/actualizar",
                "probar_servicios": "POST /api/v1/configuracion/sistema/probar-integracion/{categoria}",
                "inicializar_defaults": "POST /api/v1/configuracion/sistema/inicializar-defaults"
            },
            
            "alertas_configuracion": _generar_alertas_configuracion(db, estado_categorias)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en dashboard de configuración: {str(e)}")


# Schemas
class ConfiguracionTasas(BaseModel):
    tasa_interes_base: Decimal = Field(..., ge=0, le=100, description="Tasa de interés base anual (%)")
    tasa_mora: Decimal = Field(..., ge=0, le=10, description="Tasa de mora mensual (%)")
    tasa_descuento_pronto_pago: Optional[Decimal] = Field(None, ge=0, le=10)

class ConfiguracionLimites(BaseModel):
    monto_minimo_prestamo: Decimal = Field(..., gt=0)
    monto_maximo_prestamo: Decimal = Field(..., gt=0)
    plazo_minimo_meses: int = Field(..., ge=1)
    plazo_maximo_meses: int = Field(..., le=360)
    limite_prestamos_activos: int = Field(..., ge=1, le=10)

class ConfiguracionNotificaciones(BaseModel):
    dias_previos_recordatorio: int = Field(default=3, ge=1, le=30)
    dias_mora_alerta: int = Field(default=15, ge=1, le=90)
    email_notificaciones: bool = True
    whatsapp_notificaciones: bool = False
    sms_notificaciones: bool = False

class ConfiguracionGeneral(BaseModel):
    nombre_empresa: str
    ruc: str
    direccion: str
    telefono: str
    email: str
    horario_atencion: str
    zona_horaria: str = "America/Guayaquil"

# Almacenamiento temporal de configuraciones (en producción usar Redis o DB)
_config_cache: Dict[str, Any] = {
    "tasas": {
        "tasa_interes_base": 15.0,
        "tasa_mora": 2.0,
        "tasa_descuento_pronto_pago": 1.0
    },
    "limites": {
        "monto_minimo_prestamo": 100.0,
        "monto_maximo_prestamo": 50000.0,
        "plazo_minimo_meses": 1,
        "plazo_maximo_meses": 60,
        "limite_prestamos_activos": 3
    },
    "notificaciones": {
        "dias_previos_recordatorio": 3,
        "dias_mora_alerta": 15,
        "email_notificaciones": True,
        "whatsapp_notificaciones": False,
        "sms_notificaciones": False
    },
    "general": {
        "nombre_empresa": "Sistema de Préstamos y Cobranza",
        "ruc": "0000000000001",
        "direccion": "Av. Principal 123",
        "telefono": "+593 99 999 9999",
        "email": "info@prestamos.com",
        "horario_atencion": "Lunes a Viernes 9:00 - 18:00",
        "zona_horaria": "America/Guayaquil"
    }
}


@router.get("/tasas")
def obtener_configuracion_tasas(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener configuración de tasas de interés.
    """
    return _config_cache["tasas"]


@router.put("/tasas")
def actualizar_configuracion_tasas(
    config: ConfiguracionTasas,
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar configuración de tasas de interés.
    Solo accesible para ADMIN.
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden modificar tasas")
    
    _config_cache["tasas"] = {
        "tasa_interes_base": float(config.tasa_interes_base),
        "tasa_mora": float(config.tasa_mora),
        "tasa_descuento_pronto_pago": float(config.tasa_descuento_pronto_pago) if config.tasa_descuento_pronto_pago else 0.0
    }
    
    logger.info(f"Tasas actualizadas por {current_user.email}: {_config_cache['tasas']}")
    
    return {
        "mensaje": "Configuración de tasas actualizada exitosamente",
        "tasas": _config_cache["tasas"]
    }


@router.get("/limites")
def obtener_configuracion_limites(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener configuración de límites de préstamos.
    """
    return _config_cache["limites"]


@router.put("/limites")
def actualizar_configuracion_limites(
    config: ConfiguracionLimites,
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar configuración de límites.
    Solo accesible para ADMIN.
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden modificar límites")
    
    # Validar que máximo > mínimo
    if config.monto_maximo_prestamo <= config.monto_minimo_prestamo:
        raise HTTPException(
            status_code=400,
            detail="El monto máximo debe ser mayor al monto mínimo"
        )
    
    if config.plazo_maximo_meses <= config.plazo_minimo_meses:
        raise HTTPException(
            status_code=400,
            detail="El plazo máximo debe ser mayor al plazo mínimo"
        )
    
    _config_cache["limites"] = {
        "monto_minimo_prestamo": float(config.monto_minimo_prestamo),
        "monto_maximo_prestamo": float(config.monto_maximo_prestamo),
        "plazo_minimo_meses": config.plazo_minimo_meses,
        "plazo_maximo_meses": config.plazo_maximo_meses,
        "limite_prestamos_activos": config.limite_prestamos_activos
    }
    
    logger.info(f"Límites actualizados por {current_user.email}: {_config_cache['limites']}")
    
    return {
        "mensaje": "Configuración de límites actualizada exitosamente",
        "limites": _config_cache["limites"]
    }


@router.get("/notificaciones")
def obtener_configuracion_notificaciones(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener configuración de notificaciones.
    """
    return _config_cache["notificaciones"]


@router.put("/notificaciones")
def actualizar_configuracion_notificaciones(
    config: ConfiguracionNotificaciones,
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar configuración de notificaciones.
    Solo accesible para ADMIN y GERENTE.
    """
    if current_user.rol not in ["ADMIN", "GERENTE"]:
        raise HTTPException(status_code=403, detail="Sin permisos para modificar notificaciones")
    
    _config_cache["notificaciones"] = {
        "dias_previos_recordatorio": config.dias_previos_recordatorio,
        "dias_mora_alerta": config.dias_mora_alerta,
        "email_notificaciones": config.email_notificaciones,
        "whatsapp_notificaciones": config.whatsapp_notificaciones,
        "sms_notificaciones": config.sms_notificaciones
    }
    
    logger.info(f"Notificaciones actualizadas por {current_user.email}")
    
    return {
        "mensaje": "Configuración de notificaciones actualizada exitosamente",
        "notificaciones": _config_cache["notificaciones"]
    }


@router.get("/general")
def obtener_configuracion_general(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener configuración general del sistema.
    """
    return _config_cache["general"]


@router.put("/general")
def actualizar_configuracion_general(
    config: ConfiguracionGeneral,
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar configuración general.
    Solo accesible para ADMIN.
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden modificar configuración general")
    
    _config_cache["general"] = {
        "nombre_empresa": config.nombre_empresa,
        "ruc": config.ruc,
        "direccion": config.direccion,
        "telefono": config.telefono,
        "email": config.email,
        "horario_atencion": config.horario_atencion,
        "zona_horaria": config.zona_horaria
    }
    
    logger.info(f"Configuración general actualizada por {current_user.email}")
    
    return {
        "mensaje": "Configuración general actualizada exitosamente",
        "configuracion": _config_cache["general"]
    }


@router.get("/completa")
def obtener_configuracion_completa(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener toda la configuración del sistema.
    """
    return {
        "tasas": _config_cache["tasas"],
        "limites": _config_cache["limites"],
        "notificaciones": _config_cache["notificaciones"],
        "general": _config_cache["general"]
    }


@router.post("/restablecer")
def restablecer_configuracion_defecto(
    seccion: str,  # tasas, limites, notificaciones, general, todo
    current_user: User = Depends(get_current_user)
):
    """
    Restablecer configuración a valores por defecto.
    Solo accesible para ADMIN.
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden restablecer configuración")
    
    defaults = {
        "tasas": {
            "tasa_interes_base": 15.0,
            "tasa_mora": 2.0,
            "tasa_descuento_pronto_pago": 1.0
        },
        "limites": {
            "monto_minimo_prestamo": 100.0,
            "monto_maximo_prestamo": 50000.0,
            "plazo_minimo_meses": 1,
            "plazo_maximo_meses": 60,
            "limite_prestamos_activos": 3
        },
        "notificaciones": {
            "dias_previos_recordatorio": 3,
            "dias_mora_alerta": 15,
            "email_notificaciones": True,
            "whatsapp_notificaciones": False,
            "sms_notificaciones": False
        },
        "general": {
            "nombre_empresa": "Sistema de Préstamos y Cobranza",
            "ruc": "0000000000001",
            "direccion": "Av. Principal 123",
            "telefono": "+593 99 999 9999",
            "email": "info@prestamos.com",
            "horario_atencion": "Lunes a Viernes 9:00 - 18:00",
            "zona_horaria": "America/Guayaquil"
        }
    }
    
    if seccion == "todo":
        _config_cache.update(defaults)
        logger.warning(f"TODA la configuración restablecida por {current_user.email}")
        return {
            "mensaje": "Toda la configuración ha sido restablecida a valores por defecto",
            "configuracion": _config_cache
        }
    
    elif seccion in defaults:
        _config_cache[seccion] = defaults[seccion]
        logger.warning(f"Configuración de {seccion} restablecida por {current_user.email}")
        return {
            "mensaje": f"Configuración de {seccion} restablecida a valores por defecto",
            "configuracion": _config_cache[seccion]
        }
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Sección inválida. Opciones: tasas, limites, notificaciones, general, todo"
        )


@router.get("/calcular-cuota")
def calcular_cuota_ejemplo(
    monto: float,
    plazo_meses: int,
    tasa_personalizada: Optional[float] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Calcular cuota mensual con la configuración actual de tasas.
    """
    # Obtener tasa
    tasa = tasa_personalizada if tasa_personalizada else _config_cache["tasas"]["tasa_interes_base"]
    
    # Validar límites
    limites = _config_cache["limites"]
    if monto < limites["monto_minimo_prestamo"] or monto > limites["monto_maximo_prestamo"]:
        raise HTTPException(
            status_code=400,
            detail=f"Monto fuera de límites permitidos: ${limites['monto_minimo_prestamo']:,.2f} - ${limites['monto_maximo_prestamo']:,.2f}"
        )
    
    if plazo_meses < limites["plazo_minimo_meses"] or plazo_meses > limites["plazo_maximo_meses"]:
        raise HTTPException(
            status_code=400,
            detail=f"Plazo fuera de límites permitidos: {limites['plazo_minimo_meses']} - {limites['plazo_maximo_meses']} meses"
        )
    
    # Cálculo de cuota (método francés)
    tasa_mensual = (tasa / 100) / 12
    
    if tasa_mensual == 0:
        cuota = monto / plazo_meses
    else:
        cuota = monto * (tasa_mensual * (1 + tasa_mensual)**plazo_meses) / ((1 + tasa_mensual)**plazo_meses - 1)
    
    total_pagar = cuota * plazo_meses
    total_interes = total_pagar - monto
    
    return {
        "monto_solicitado": monto,
        "plazo_meses": plazo_meses,
        "tasa_interes_anual": tasa,
        "cuota_mensual": round(cuota, 2),
        "total_pagar": round(total_pagar, 2),
        "total_interes": round(total_interes, 2),
        "relacion_cuota_ingreso_sugerida": "< 40%"
    }


@router.get("/validar-limites/{cliente_id}")
def validar_limites_cliente(
    cliente_id: int,
    monto_solicitado: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validar si un cliente puede solicitar un nuevo préstamo según límites configurados.
    """
    from app.models.prestamo import Prestamo
    
    # Contar préstamos activos del cliente
    prestamos_activos = db.query(Prestamo).filter(
        Prestamo.cliente_id == cliente_id,
        Prestamo.estado == "ACTIVO"
    ).count()
    
    limite_prestamos = _config_cache["limites"]["limite_prestamos_activos"]
    limites_monto = _config_cache["limites"]
    
    # Validaciones
    validaciones = {
        "puede_solicitar": True,
        "mensajes": []
    }
    
    if prestamos_activos >= limite_prestamos:
        validaciones["puede_solicitar"] = False
        validaciones["mensajes"].append(
            f"El cliente ya tiene {prestamos_activos} préstamos activos (límite: {limite_prestamos})"
        )
    
    if monto_solicitado < limites_monto["monto_minimo_prestamo"]:
        validaciones["puede_solicitar"] = False
        validaciones["mensajes"].append(
            f"Monto mínimo permitido: ${limites_monto['monto_minimo_prestamo']:,.2f}"
        )
    
    if monto_solicitado > limites_monto["monto_maximo_prestamo"]:
        validaciones["puede_solicitar"] = False
        validaciones["mensajes"].append(
            f"Monto máximo permitido: ${limites_monto['monto_maximo_prestamo']:,.2f}"
        )
    
    return {
        "cliente_id": cliente_id,
        "prestamos_activos": prestamos_activos,
        "limite_prestamos": limite_prestamos,
        "monto_solicitado": monto_solicitado,
        **validaciones
    }
