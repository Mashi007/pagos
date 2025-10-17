# backend/app/api/v1/endpoints/monitoreo_auditoria.py
"""
🔍 Endpoints de Monitoreo de Auditoría en Tiempo Real
=====================================================

Endpoints especializados para monitoreo avanzado del sistema de auditoría
Incluye métricas en tiempo real, alertas y análisis de comportamiento
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta
import json
import asyncio
import logging

from app.db.session import get_db
from app.models.auditoria import Auditoria
from app.models.user import User
from app.api.deps import get_admin_user
from app.schemas.auditoria import AuditoriaResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Conexiones WebSocket activas para monitoreo en tiempo real
active_connections: List[WebSocket] = []

class MonitoreoAuditoria:
    """
    🔍 Clase para monitoreo avanzado de auditoría
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def obtener_metricas_tiempo_real(self) -> Dict[str, Any]:
        """
        📊 Obtener métricas de auditoría en tiempo real
        """
        ahora = datetime.utcnow()
        ultima_hora = ahora - timedelta(hours=1)
        ultimo_dia = ahora - timedelta(days=1)
        
        # Actividad por hora
        actividad_hora = self.db.query(Auditoria).filter(
            Auditoria.fecha >= ultima_hora
        ).count()
        
        # Actividad por día
        actividad_dia = self.db.query(Auditoria).filter(
            Auditoria.fecha >= ultimo_dia
        ).count()
        
        # Usuarios activos (última hora)
        usuarios_activos = self.db.query(
            func.count(func.distinct(Auditoria.usuario_email))
        ).filter(
            Auditoria.fecha >= ultima_hora
        ).scalar() or 0
        
        # Módulos más activos (última hora)
        modulos_activos = self.db.query(
            Auditoria.modulo,
            func.count(Auditoria.id).label('total')
        ).filter(
            Auditoria.fecha >= ultima_hora
        ).group_by(Auditoria.modulo).order_by(desc('total')).limit(5).all()
        
        # Acciones más frecuentes (última hora)
        acciones_frecuentes = self.db.query(
            Auditoria.accion,
            func.count(Auditoria.id).label('total')
        ).filter(
            Auditoria.fecha >= ultima_hora
        ).group_by(Auditoria.accion).order_by(desc('total')).limit(5).all()
        
        # Errores recientes
        errores_recientes = self.db.query(Auditoria).filter(
            and_(
                Auditoria.fecha >= ultima_hora,
                Auditoria.resultado == "FALLIDO"
            )
        ).count()
        
        return {
            "timestamp": ahora.isoformat(),
            "actividad_hora": actividad_hora,
            "actividad_dia": actividad_dia,
            "usuarios_activos": usuarios_activos,
            "modulos_activos": [
                {"modulo": m.modulo, "total": m.total} 
                for m in modulos_activos
            ],
            "acciones_frecuentes": [
                {"accion": a.accion, "total": a.total} 
                for a in acciones_frecuentes
            ],
            "errores_recientes": errores_recientes,
            "estado_sistema": "ACTIVO" if errores_recientes < 5 else "ALERTA"
        }
    
    def detectar_anomalias(self) -> List[Dict[str, Any]]:
        """
        🚨 Detectar anomalías en el comportamiento del sistema
        """
        anomalias = []
        ahora = datetime.utcnow()
        ultima_hora = ahora - timedelta(hours=1)
        
        # Detectar múltiples fallos del mismo usuario
        fallos_usuario = self.db.query(
            Auditoria.usuario_email,
            func.count(Auditoria.id).label('fallos')
        ).filter(
            and_(
                Auditoria.fecha >= ultima_hora,
                Auditoria.resultado == "FALLIDO"
            )
        ).group_by(Auditoria.usuario_email).having(
            func.count(Auditoria.id) >= 3
        ).all()
        
        for fallo in fallos_usuario:
            anomalias.append({
                "tipo": "MULTIPLES_FALLOS",
                "usuario": fallo.usuario_email,
                "fallos": fallo.fallos,
                "severidad": "ALTA" if fallo.fallos >= 10 else "MEDIA",
                "descripcion": f"Usuario {fallo.usuario_email} ha tenido {fallo.fallos} fallos en la última hora"
            })
        
        # Detectar actividad inusual (muchas acciones en poco tiempo)
        actividad_inusual = self.db.query(
            Auditoria.usuario_email,
            func.count(Auditoria.id).label('acciones')
        ).filter(
            Auditoria.fecha >= ultima_hora
        ).group_by(Auditoria.usuario_email).having(
            func.count(Auditoria.id) >= 50
        ).all()
        
        for actividad in actividad_inusual:
            anomalias.append({
                "tipo": "ACTIVIDAD_INUSUAL",
                "usuario": actividad.usuario_email,
                "acciones": actividad.acciones,
                "severidad": "ALTA" if actividad.acciones >= 100 else "MEDIA",
                "descripcion": f"Usuario {actividad.usuario_email} ha realizado {actividad.acciones} acciones en la última hora"
            })
        
        return anomalias
    
    def obtener_tendencias(self, dias: int = 7) -> Dict[str, Any]:
        """
        📈 Obtener tendencias de auditoría
        """
        fecha_inicio = datetime.utcnow() - timedelta(days=dias)
        
        # Actividad por día
        actividad_diaria = self.db.query(
            func.date(Auditoria.fecha).label('fecha'),
            func.count(Auditoria.id).label('total')
        ).filter(
            Auditoria.fecha >= fecha_inicio
        ).group_by(
            func.date(Auditoria.fecha)
        ).order_by('fecha').all()
        
        # Módulos más utilizados
        modulos_tendencia = self.db.query(
            Auditoria.modulo,
            func.count(Auditoria.id).label('total')
        ).filter(
            Auditoria.fecha >= fecha_inicio
        ).group_by(Auditoria.modulo).order_by(desc('total')).limit(10).all()
        
        # Usuarios más activos
        usuarios_tendencia = self.db.query(
            Auditoria.usuario_email,
            func.count(Auditoria.id).label('total')
        ).filter(
            Auditoria.fecha >= fecha_inicio
        ).group_by(Auditoria.usuario_email).order_by(desc('total')).limit(10).all()
        
        return {
            "periodo_dias": dias,
            "actividad_diaria": [
                {"fecha": str(a.fecha), "total": a.total} 
                for a in actividad_diaria
            ],
            "modulos_tendencia": [
                {"modulo": m.modulo, "total": m.total} 
                for m in modulos_tendencia
            ],
            "usuarios_tendencia": [
                {"usuario": u.usuario_email, "total": u.total} 
                for u in usuarios_tendencia
            ]
        }

# ============================================
# ENDPOINTS DE MONITOREO
# ============================================

@router.get("/metricas-tiempo-real")
def obtener_metricas_tiempo_real(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    📊 Obtener métricas de auditoría en tiempo real (SOLO ADMIN)
    """
    try:
        monitoreo = MonitoreoAuditoria(db)
        metricas = monitoreo.obtener_metricas_tiempo_real()
        
        return {
            "status": "success",
            "metricas": metricas,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/anomalias")
def detectar_anomalias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    🚨 Detectar anomalías en el comportamiento del sistema (SOLO ADMIN)
    """
    try:
        monitoreo = MonitoreoAuditoria(db)
        anomalias = monitoreo.detectar_anomalias()
        
        return {
            "status": "success",
            "anomalias": anomalias,
            "total_anomalias": len(anomalias),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error detectando anomalías: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/tendencias")
def obtener_tendencias(
    dias: int = Query(7, ge=1, le=30, description="Número de días para análisis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    📈 Obtener tendencias de auditoría (SOLO ADMIN)
    """
    try:
        monitoreo = MonitoreoAuditoria(db)
        tendencias = monitoreo.obtener_tendencias(dias)
        
        return {
            "status": "success",
            "tendencias": tendencias,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo tendencias: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/dashboard-completo")
def dashboard_completo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    🎛️ Dashboard completo de monitoreo de auditoría (SOLO ADMIN)
    """
    try:
        monitoreo = MonitoreoAuditoria(db)
        
        # Obtener todas las métricas
        metricas = monitoreo.obtener_metricas_tiempo_real()
        anomalias = monitoreo.detectar_anomalias()
        tendencias = monitoreo.obtener_tendencias(7)
        
        # Estadísticas generales
        total_registros = db.query(Auditoria).count()
        usuarios_unicos = db.query(func.count(func.distinct(Auditoria.usuario_email))).scalar()
        modulos_unicos = db.query(func.count(func.distinct(Auditoria.modulo))).scalar()
        
        return {
            "status": "success",
            "dashboard": {
                "metricas_tiempo_real": metricas,
                "anomalias": anomalias,
                "tendencias": tendencias,
                "estadisticas_generales": {
                    "total_registros": total_registros,
                    "usuarios_unicos": usuarios_unicos,
                    "modulos_unicos": modulos_unicos,
                    "fecha_ultima_actualizacion": datetime.utcnow().isoformat()
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generando dashboard: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# ============================================
# WEBSOCKET PARA MONITOREO EN TIEMPO REAL
# ============================================

@router.websocket("/ws-monitoreo")
async def websocket_monitoreo(websocket: WebSocket):
    """
    🔌 WebSocket para monitoreo en tiempo real
    """
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Obtener métricas cada 30 segundos
            await asyncio.sleep(30)
            
            # Obtener métricas actuales
            db = next(get_db())
            monitoreo = MonitoreoAuditoria(db)
            metricas = monitoreo.obtener_metricas_tiempo_real()
            anomalias = monitoreo.detectar_anomalias()
            
            # Enviar datos a todos los clientes conectados
            data = {
                "type": "metricas_tiempo_real",
                "data": {
                    "metricas": metricas,
                    "anomalias": anomalias
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Enviar a todos los clientes conectados
            for connection in active_connections.copy():
                try:
                    await connection.send_text(json.dumps(data))
                except:
                    # Remover conexiones cerradas
                    active_connections.remove(connection)
            
            db.close()
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)
