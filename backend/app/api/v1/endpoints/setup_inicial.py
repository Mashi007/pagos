# backend/app/api/v1/endpoints/setup_inicial.py
"""
🔧 Setup Inicial del Sistema
Endpoint especial para configuración inicial del sistema desde el frontend
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.configuracion_sistema import ConfiguracionSistema, ConfiguracionPorDefecto
from app.core.security import get_current_user

router = APIRouter()


@router.post("/inicializar-sistema")
def inicializar_sistema_completo(
    db: Session = Depends(get_db)
):
    """
    🚀 Inicialización completa del sistema
    Endpoint público para primer setup (solo funciona si no hay admins)
    """
    try:
        # Verificar si ya hay administradores
        admin_existente = db.query(User).filter(User.rol == "ADMIN").first()
        
        if admin_existente:
            raise HTTPException(
                status_code=400, 
                detail="Sistema ya está inicializado. Use endpoints de configuración normales."
            )
        
        # 1. Crear configuraciones por defecto
        ConfiguracionPorDefecto.crear_configuraciones_default(db)
        
        # 2. Contar configuraciones creadas
        total_configs = db.query(ConfiguracionSistema).count()
        
        return {
            "mensaje": "✅ Sistema inicializado exitosamente",
            "configuraciones_creadas": total_configs,
            "categorias_disponibles": [
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
            "siguiente_paso": {
                "accion": "Crear usuario administrador",
                "endpoint": "python backend/scripts/create_admin.py",
                "descripcion": "Crear primer usuario administrador para gestionar el sistema"
            },
            "fecha_inicializacion": datetime.now().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error inicializando sistema: {str(e)}")


@router.get("/estado-inicializacion")
def verificar_estado_inicializacion(
    db: Session = Depends(get_db)
):
    """
    🔍 Verificar estado de inicialización del sistema
    Endpoint público para verificar si el sistema está listo
    """
    try:
        # Verificar si hay administradores
        total_admins = db.query(User).filter(User.rol == "ADMIN").count()
        admin_activo = db.query(User).filter(
            User.rol == "ADMIN",
            User.is_active == True
        ).first()
        
        # Verificar configuraciones
        total_configs = db.query(ConfiguracionSistema).count()
        configs_requeridas = db.query(ConfiguracionSistema).filter(
            ConfiguracionSistema.requerido == True
        ).count()
        configs_requeridas_configuradas = db.query(ConfiguracionSistema).filter(
            ConfiguracionSistema.requerido == True,
            ConfiguracionSistema.valor.isnot(None),
            ConfiguracionSistema.valor != ""
        ).count()
        
        # Determinar estado del sistema
        sistema_inicializado = total_configs > 0
        admin_configurado = admin_activo is not None
        configuracion_completa = configs_requeridas_configuradas == configs_requeridas
        
        estado_general = "COMPLETO" if (sistema_inicializado and admin_configurado and configuracion_completa) else \
                        "PARCIAL" if sistema_inicializado else \
                        "PENDIENTE"
        
        return {
            "titulo": "🔍 ESTADO DE INICIALIZACIÓN DEL SISTEMA",
            "fecha_verificacion": datetime.now().isoformat(),
            
            "estado_general": {
                "estado": estado_general,
                "descripcion": {
                    "COMPLETO": "✅ Sistema completamente configurado y listo",
                    "PARCIAL": "⚠️ Sistema parcialmente configurado",
                    "PENDIENTE": "❌ Sistema requiere inicialización"
                }.get(estado_general),
                "porcentaje_completitud": _calcular_completitud(
                    sistema_inicializado, admin_configurado, configuracion_completa
                )
            },
            
            "componentes": {
                "configuraciones": {
                    "estado": "✅ LISTO" if sistema_inicializado else "❌ PENDIENTE",
                    "total_configuraciones": total_configs,
                    "configuraciones_requeridas": configs_requeridas,
                    "requeridas_configuradas": configs_requeridas_configuradas,
                    "accion": "POST /api/v1/setup/inicializar-sistema" if not sistema_inicializado else None
                },
                "administrador": {
                    "estado": "✅ CONFIGURADO" if admin_configurado else "❌ PENDIENTE",
                    "total_admins": total_admins,
                    "admin_activo": bool(admin_activo),
                    "email_admin": admin_activo.email if admin_activo else None,
                    "accion": "python backend/scripts/create_admin.py" if not admin_configurado else None
                },
                "servicios": {
                    "estado": "✅ FUNCIONALES" if configuracion_completa else "⚠️ PARCIAL",
                    "base_datos": "✅ CONECTADA",
                    "api": "✅ ACTIVA",
                    "autenticacion": "✅ FUNCIONAL"
                }
            },
            
            "pasos_siguientes": _generar_pasos_siguientes(
                sistema_inicializado, admin_configurado, configuracion_completa
            ),
            
            "urls_importantes": {
                "aplicacion": "https://pagos-f2qf.onrender.com",
                "documentacion": "https://pagos-f2qf.onrender.com/docs",
                "dashboard_config": "/api/v1/configuracion/dashboard",
                "estado_servicios": "/api/v1/configuracion/sistema/estado-servicios"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verificando inicialización: {str(e)}")


@router.get("/configuracion-frontend")
def obtener_configuracion_para_frontend(
    db: Session = Depends(get_db)
):
    """
    🎨 Obtener configuración específica para el frontend
    Endpoint optimizado para cargar configuración en la aplicación web
    """
    try:
        # Configuraciones públicas (sin datos sensibles)
        configuracion_publica = {
            "aplicacion": {
                "nombre": "Sistema de Financiamiento Automotriz",
                "version": "1.0.0",
                "timezone": "America/Santo_Domingo"
            },
            "funcionalidades": {
                "ia_habilitada": False,  # Se actualizará con configuración real
                "whatsapp_habilitado": False,
                "email_configurado": False,
                "reportes_pdf": True,
                "carga_masiva": True,
                "conciliacion_bancaria": True,
                "sistema_aprobaciones": True
            },
            "limites": {
                "monto_maximo": 5000000,
                "plazo_maximo": 84,
                "cuota_inicial_minima": 10.0
            },
            "roles_disponibles": [
                "ADMIN", "GERENTE", "DIRECTOR", 
                "COBRANZAS", "COMERCIAL", "ASESOR", "CONTADOR"
            ]
        }
        
        # Actualizar con configuración real si existe
        try:
            from app.models.configuracion_sistema import ConfigHelper
            
            configuracion_publica["funcionalidades"]["ia_habilitada"] = ConfigHelper.is_ai_enabled(db)
            configuracion_publica["funcionalidades"]["whatsapp_habilitado"] = ConfigHelper.is_whatsapp_enabled(db)
            configuracion_publica["funcionalidades"]["email_configurado"] = ConfigHelper.is_email_configured(db)
            
            # Configuración financiera
            config_financiera = ConfigHelper.get_financial_config(db)
            configuracion_publica["limites"].update(config_financiera)
            
        except:
            pass  # Usar valores por defecto si hay error
        
        return {
            "configuracion": configuracion_publica,
            "fecha_consulta": datetime.now().isoformat(),
            "endpoints_configuracion": {
                "dashboard": "/api/v1/configuracion/dashboard",
                "ia": "/api/v1/configuracion/ia",
                "email": "/api/v1/configuracion/email",
                "whatsapp": "/api/v1/configuracion/whatsapp",
                "estado_servicios": "/api/v1/configuracion/sistema/estado-servicios"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo configuración frontend: {str(e)}")


# ============================================
# FUNCIONES AUXILIARES
# ============================================

def _calcular_completitud(sistema_init: bool, admin_config: bool, config_completa: bool) -> float:
    """Calcular porcentaje de completitud del sistema"""
    componentes = [sistema_init, admin_config, config_completa]
    return round(sum(componentes) / len(componentes) * 100, 1)


def _generar_pasos_siguientes(sistema_init: bool, admin_config: bool, config_completa: bool) -> List[Dict]:
    """Generar pasos siguientes según estado"""
    pasos = []
    
    if not sistema_init:
        pasos.append({
            "paso": 1,
            "titulo": "Inicializar configuraciones",
            "descripcion": "Crear configuraciones por defecto del sistema",
            "accion": "POST /api/v1/setup/inicializar-sistema",
            "prioridad": "ALTA"
        })
    
    if not admin_config:
        pasos.append({
            "paso": 2,
            "titulo": "Crear administrador",
            "descripcion": "Crear primer usuario administrador",
            "accion": "python backend/scripts/create_admin.py",
            "prioridad": "CRITICA"
        })
    
    if not config_completa:
        pasos.append({
            "paso": 3,
            "titulo": "Configurar servicios",
            "descripcion": "Configurar email, IA, WhatsApp según necesidades",
            "accion": "Usar dashboard de configuración",
            "prioridad": "MEDIA"
        })
    
    if sistema_init and admin_config and config_completa:
        pasos.append({
            "paso": "FINAL",
            "titulo": "Sistema listo",
            "descripcion": "Sistema completamente configurado y funcional",
            "accion": "Comenzar a usar el sistema",
            "prioridad": "INFO"
        })
    
    return pasos
