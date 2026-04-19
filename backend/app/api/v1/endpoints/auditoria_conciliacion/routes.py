# -*- coding: utf-8 -*-
"""
Endpoint para auditoría de conciliación manual.
Permite visualizar el historial de asignaciones de pagos a cuotas.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.response_schema import ResponseSchema
from app.models.auditoria_conciliacion_manual import AuditoriaConciliacionManual
from datetime import datetime, timedelta

router = APIRouter(prefix='/api/v1/auditoria', tags=['auditoria'])


@router.get('/conciliacion')
async def obtener_auditoria_conciliacion(
    dias: int = Query(7, ge=1, le=365),
    tipo_asignacion: str = Query(None),
    resultado: str = Query(None),
    usuario_id: int = Query(None),
    db: Session = Depends(get_db),
    admin = Depends(get_current_user)
):
    """
    Retorna historial de auditoría de conciliación manual/automática.
    
    Args:
        dias: Número de días a consultar (default: 7, máximo: 365)
        tipo_asignacion: Filtrar por 'MANUAL' o 'AUTOMATICA' (opcional)
        resultado: Filtrar por 'EXITOSA' o 'FALLIDA' (opcional)
        usuario_id: Filtrar por usuario específico (opcional)
    
    Returns:
        Historial detallado con estadísticas
    """
    
    try:
        fecha_inicio = datetime.utcnow() - timedelta(days=dias)
        
        query = db.query(AuditoriaConciliacionManual).filter(
            AuditoriaConciliacionManual.fecha_asignacion >= fecha_inicio
        )
        
        if tipo_asignacion:
            query = query.filter(AuditoriaConciliacionManual.tipo_asignacion == tipo_asignacion.upper())
        
        if resultado:
            query = query.filter(AuditoriaConciliacionManual.resultado == resultado.upper())
        
        if usuario_id:
            query = query.filter(AuditoriaConciliacionManual.usuario_id == usuario_id)
        
        registros = query.order_by(desc(AuditoriaConciliacionManual.fecha_asignacion)).all()
        
        # Calcular estadísticas
        total_registros = len(registros)
        total_exitosas = len([r for r in registros if r.resultado == 'EXITOSA'])
        total_fallidas = len([r for r in registros if r.resultado == 'FALLIDA'])
        monto_total_asignado = sum([float(r.monto_asignado or 0) for r in registros])
        
        por_tipo = {}
        for r in registros:
            tipo = r.tipo_asignacion
            if tipo not in por_tipo:
                por_tipo[tipo] = {'cantidad': 0, 'monto': 0, 'exitosas': 0, 'fallidas': 0}
            por_tipo[tipo]['cantidad'] += 1
            por_tipo[tipo]['monto'] += float(r.monto_asignado or 0)
            if r.resultado == 'EXITOSA':
                por_tipo[tipo]['exitosas'] += 1
            else:
                por_tipo[tipo]['fallidas'] += 1
        
        return ResponseSchema(
            status='success',
            message=f'Auditoría de conciliación (últimos {dias} días)',
            data={
                'estadisticas': {
                    'total_registros': total_registros,
                    'exitosas': total_exitosas,
                    'fallidas': total_fallidas,
                    'tasa_exito': f'{(total_exitosas / total_registros * 100):.1f}%' if total_registros > 0 else '0%',
                    'monto_total_asignado': monto_total_asignado
                },
                'por_tipo': por_tipo,
                'registros': [
                    {
                        'id': r.id,
                        'pago_id': r.pago_id,
                        'cuota_id': r.cuota_id,
                        'monto': float(r.monto_asignado),
                        'tipo': r.tipo_asignacion,
                        'resultado': r.resultado,
                        'usuario_id': r.usuario_id,
                        'motivo': r.motivo,
                        'fecha': r.fecha_asignacion.isoformat() if r.fecha_asignacion else None
                    }
                    for r in registros
                ]
            }
        ).dict()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al obtener auditoría: {str(e)}')


@router.get('/conciliacion/resumen-diario')
async def obtener_resumen_diario_conciliacion(
    dias: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    admin = Depends(get_current_user)
):
    """
    Retorna resumen diario de conciliaciones (automáticas + manuales).
    """
    
    try:
        fecha_inicio = datetime.utcnow() - timedelta(days=dias)
        
        registros = db.query(AuditoriaConciliacionManual).filter(
            AuditoriaConciliacionManual.fecha_asignacion >= fecha_inicio
        ).all()
        
        # Agrupar por día
        por_dia = {}
        for r in registros:
            fecha = r.fecha_asignacion.date() if r.fecha_asignacion else None
            if not fecha:
                continue
            
            fecha_str = fecha.isoformat()
            if fecha_str not in por_dia:
                por_dia[fecha_str] = {
                    'automaticas': 0,
                    'manuales': 0,
                    'exitosas': 0,
                    'fallidas': 0,
                    'monto_total': 0
                }
            
            por_dia[fecha_str]['monto_total'] += float(r.monto_asignado or 0)
            
            if r.tipo_asignacion == 'AUTOMATICA':
                por_dia[fecha_str]['automaticas'] += 1
            else:
                por_dia[fecha_str]['manuales'] += 1
            
            if r.resultado == 'EXITOSA':
                por_dia[fecha_str]['exitosas'] += 1
            else:
                por_dia[fecha_str]['fallidas'] += 1
        
        resumen_ordenado = sorted(por_dia.items(), key=lambda x: x[0], reverse=True)
        
        return ResponseSchema(
            status='success',
            message=f'Resumen diario de conciliación (últimos {dias} días)',
            data={'por_dia': dict(resumen_ordenado)}
        ).dict()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

