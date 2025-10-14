# backend/app/api/v1/endpoints/auditoria.py
"""
Endpoint para consulta de auditoría del sistema.
Tracking completo de todas las operaciones.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional, List
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from app.db.session import get_db
from app.models.auditoria import Auditoria, TipoAccion
from app.models.user import User
from app.api.deps import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Schemas
class AuditoriaResponse(BaseModel):
    id: int
    usuario_id: int
    usuario_email: str
    accion: str
    tabla: str
    registro_id: int
    datos_anteriores: Optional[dict]
    datos_nuevos: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
    fecha: datetime
    
    class Config:
        from_attributes = True

class FiltrosAuditoria(BaseModel):
    usuario_id: Optional[int] = None
    accion: Optional[str] = None
    tabla: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None


@router.get("/log")
def obtener_log_auditoria(
    usuario_id: Optional[int] = None,
    accion: Optional[str] = None,
    tabla: Optional[str] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener log de auditoría con filtros.
    """
    # Verificar permisos (solo admin o roles con permiso AUDITORIA_VER)
    if current_user.rol not in ["ADMIN", "GERENTE", "DIRECTOR"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sin permisos para ver auditoría")
    
    # Construir query
    query = db.query(Auditoria)
    
    if usuario_id:
        query = query.filter(Auditoria.usuario_id == usuario_id)
    
    if accion:
        query = query.filter(Auditoria.accion == accion)
    
    if tabla:
        query = query.filter(Auditoria.tabla == tabla)
    
    if fecha_inicio:
        query = query.filter(Auditoria.fecha >= fecha_inicio)
    
    if fecha_fin:
        # Incluir todo el día
        fecha_fin_end = datetime.combine(fecha_fin, datetime.max.time())
        query = query.filter(Auditoria.fecha <= fecha_fin_end)
    
    # Contar total
    total = query.count()
    
    # Paginación
    offset = (page - 1) * page_size
    registros = query.order_by(Auditoria.fecha.desc()).offset(offset).limit(page_size).all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "registros": [
            {
                "id": r.id,
                "usuario": r.usuario.email if r.usuario else "Sistema",
                "accion": r.accion,
                "tabla": r.tabla,
                "registro_id": r.registro_id,
                "datos_anteriores": r.datos_anteriores,
                "datos_nuevos": r.datos_nuevos,
                "ip_address": r.ip_address,
                "fecha": r.fecha
            }
            for r in registros
        ]
    }


@router.get("/actividad/{usuario_id}")
def actividad_usuario(
    usuario_id: int,
    dias: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener actividad de un usuario específico.
    """
    # Solo admin o el mismo usuario
    if current_user.rol != "ADMIN" and current_user.id != usuario_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    fecha_inicio = datetime.now() - timedelta(days=dias)
    
    actividades = db.query(Auditoria).filter(
        and_(
            Auditoria.usuario_id == usuario_id,
            Auditoria.fecha >= fecha_inicio
        )
    ).order_by(Auditoria.fecha.desc()).all()
    
    # Estadísticas
    acciones_count = {}
    tablas_count = {}
    
    for act in actividades:
        acciones_count[act.accion] = acciones_count.get(act.accion, 0) + 1
        tablas_count[act.tabla] = tablas_count.get(act.tabla, 0) + 1
    
    return {
        "usuario_id": usuario_id,
        "periodo_dias": dias,
        "total_acciones": len(actividades),
        "por_accion": acciones_count,
        "por_tabla": tablas_count,
        "ultimas_actividades": [
            {
                "accion": a.accion,
                "tabla": a.tabla,
                "registro_id": a.registro_id,
                "fecha": a.fecha
            }
            for a in actividades[:20]
        ]
    }


@router.get("/cambios/{tabla}/{registro_id}")
def historial_cambios_registro(
    tabla: str,
    registro_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener historial completo de cambios de un registro específico.
    """
    cambios = db.query(Auditoria).filter(
        and_(
            Auditoria.tabla == tabla,
            Auditoria.registro_id == registro_id
        )
    ).order_by(Auditoria.fecha).all()
    
    return {
        "tabla": tabla,
        "registro_id": registro_id,
        "total_cambios": len(cambios),
        "historial": [
            {
                "id": c.id,
                "accion": c.accion,
                "usuario": c.usuario.email if c.usuario else "Sistema",
                "datos_anteriores": c.datos_anteriores,
                "datos_nuevos": c.datos_nuevos,
                "fecha": c.fecha,
                "cambios_detectados": _detectar_cambios_campos(c.datos_anteriores, c.datos_nuevos)
            }
            for c in cambios
        ]
    }


@router.get("/estadisticas")
def estadisticas_auditoria(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas generales de auditoría.
    """
    if current_user.rol not in ["ADMIN", "GERENTE", "DIRECTOR"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    # Periodo por defecto: últimos 30 días
    if not fecha_inicio:
        fecha_inicio = date.today() - timedelta(days=30)
    if not fecha_fin:
        fecha_fin = date.today()
    
    # Query base
    query = db.query(Auditoria).filter(
        and_(
            Auditoria.fecha >= fecha_inicio,
            Auditoria.fecha <= datetime.combine(fecha_fin, datetime.max.time())
        )
    )
    
    # Totales por acción
    por_accion = db.query(
        Auditoria.accion,
        func.count(Auditoria.id).label('total')
    ).filter(
        and_(
            Auditoria.fecha >= fecha_inicio,
            Auditoria.fecha <= datetime.combine(fecha_fin, datetime.max.time())
        )
    ).group_by(Auditoria.accion).all()
    
    # Totales por tabla
    por_tabla = db.query(
        Auditoria.tabla,
        func.count(Auditoria.id).label('total')
    ).filter(
        and_(
            Auditoria.fecha >= fecha_inicio,
            Auditoria.fecha <= datetime.combine(fecha_fin, datetime.max.time())
        )
    ).group_by(Auditoria.tabla).all()
    
    # Usuarios más activos
    usuarios_activos = db.query(
        Auditoria.usuario_id,
        User.email,
        func.count(Auditoria.id).label('total')
    ).join(User).filter(
        and_(
            Auditoria.fecha >= fecha_inicio,
            Auditoria.fecha <= datetime.combine(fecha_fin, datetime.max.time())
        )
    ).group_by(Auditoria.usuario_id, User.email).order_by(
        func.count(Auditoria.id).desc()
    ).limit(10).all()
    
    # Actividad por día
    actividad_diaria = db.query(
        func.date(Auditoria.fecha).label('dia'),
        func.count(Auditoria.id).label('total')
    ).filter(
        and_(
            Auditoria.fecha >= fecha_inicio,
            Auditoria.fecha <= datetime.combine(fecha_fin, datetime.max.time())
        )
    ).group_by(func.date(Auditoria.fecha)).order_by(
        func.date(Auditoria.fecha)
    ).all()
    
    return {
        "periodo": {
            "inicio": fecha_inicio,
            "fin": fecha_fin
        },
        "total_registros": query.count(),
        "por_accion": {accion: total for accion, total in por_accion},
        "por_tabla": {tabla: total for tabla, total in por_tabla},
        "usuarios_mas_activos": [
            {
                "usuario_id": uid,
                "email": email,
                "total_acciones": total
            }
            for uid, email, total in usuarios_activos
        ],
        "actividad_diaria": [
            {
                "fecha": str(dia),
                "total": total
            }
            for dia, total in actividad_diaria
        ]
    }


@router.get("/acciones-criticas")
def acciones_criticas(
    dias: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener acciones críticas recientes (eliminaciones, rechazos, etc.).
    """
    if current_user.rol not in ["ADMIN", "GERENTE", "DIRECTOR"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    fecha_inicio = datetime.now() - timedelta(days=dias)
    
    acciones_criticas = [
        TipoAccion.ELIMINAR.value,
        TipoAccion.ANULAR.value,
        "RECHAZAR",
        "DESACTIVAR"
    ]
    
    registros = db.query(Auditoria).filter(
        and_(
            Auditoria.accion.in_(acciones_criticas),
            Auditoria.fecha >= fecha_inicio
        )
    ).order_by(Auditoria.fecha.desc()).all()
    
    return {
        "periodo_dias": dias,
        "total_acciones_criticas": len(registros),
        "acciones": [
            {
                "id": r.id,
                "accion": r.accion,
                "tabla": r.tabla,
                "registro_id": r.registro_id,
                "usuario": r.usuario.email if r.usuario else "Sistema",
                "fecha": r.fecha,
                "datos_eliminados": r.datos_anteriores
            }
            for r in registros
        ]
    }


@router.get("/exportar")
async def exportar_auditoria(
    formato: str = Query("csv", pattern="^(csv|excel)$"),
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exportar log de auditoría en CSV o Excel.
    """
    if current_user.rol not in ["ADMIN", "GERENTE"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sin permisos para exportar")
    
    # Query
    query = db.query(Auditoria)
    
    if fecha_inicio:
        query = query.filter(Auditoria.fecha >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Auditoria.fecha <= datetime.combine(fecha_fin, datetime.max.time()))
    
    registros = query.order_by(Auditoria.fecha.desc()).all()
    
    # Preparar datos
    datos = []
    for r in registros:
        datos.append({
            "ID": r.id,
            "Usuario": r.usuario.email if r.usuario else "Sistema",
            "Acción": r.accion,
            "Tabla": r.tabla,
            "Registro ID": r.registro_id,
            "IP": r.ip_address,
            "Fecha": r.fecha.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    if formato == "csv":
        import csv
        from io import StringIO
        from fastapi.responses import StreamingResponse
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=datos[0].keys())
        writer.writeheader()
        writer.writerows(datos)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=auditoria.csv"}
        )
    
    else:  # excel
        import pandas as pd
        from io import BytesIO
        from fastapi.responses import StreamingResponse
        
        df = pd.DataFrame(datos)
        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=auditoria.xlsx"}
        )


# Helper functions
def _detectar_cambios_campos(datos_anteriores: dict, datos_nuevos: dict) -> dict:
    """
    Detectar qué campos cambiaron entre dos versiones de un registro.
    """
    if not datos_anteriores or not datos_nuevos:
        return {}
    
    cambios = {}
    
    for campo, valor_nuevo in datos_nuevos.items():
        valor_anterior = datos_anteriores.get(campo)
        if valor_anterior != valor_nuevo:
            cambios[campo] = {
                "anterior": valor_anterior,
                "nuevo": valor_nuevo
            }
    
    return cambios
