# -*- coding: utf-8 -*-
"`"
Dashboard de monitoreo en tiempo real de conciliación.
Muestra métricas de salud del sistema de pagos y cuotas.
"`"
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.response_schema import ResponseSchema
from decimal import Decimal

router = APIRouter(prefix='/api/v1/dashboard', tags=['dashboard'])


@router.get('/conciliacion-health')
async def dashboard_conciliacion_health(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    "`"
    Dashboard de salud de conciliación.
    Métricas críticas en tiempo real.
    "`"
    
    try:
        # Pagos sin asignar
        pagos_sin_asignar = db.query(text('''
            SELECT COUNT(*) as cantidad, COALESCE(SUM(monto_pagado), 0) as monto
            FROM pagos p
            WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
        ''')).fetchone()
        
        # Cuotas por estado
        estados = db.query(text('''
            SELECT estado, COUNT(*) as cantidad, COALESCE(SUM(monto), 0) as monto
            FROM cuotas
            GROUP BY estado
        ''')).fetchall()
        
        # Cuotas sobre-aplicadas
        sobre_aplicadas = db.query(text('''
            SELECT COUNT(*) as cantidad
            FROM cuotas c
            WHERE (SELECT COALESCE(SUM(cp.monto_aplicado), 0) FROM cuota_pagos cp WHERE cp.cuota_id = c.id) > c.monto + 0.01
        ''')).fetchone()
        
        # Tasa de asignación
        total_pagos = db.query(text('SELECT COUNT(*) FROM pagos')).scalar() or 0
        pagos_asignados = total_pagos - (pagos_sin_asignar[0] or 0)
        tasa_asignacion = (pagos_asignados / total_pagos * 100) if total_pagos > 0 else 0
        
        # Cuotas en mora
        en_mora = db.query(text('''
            SELECT COUNT(*) FROM cuotas
            WHERE estado = 'MORA'
        ''')).scalar() or 0
        
        return ResponseSchema(
            status='success',
            message='Dashboard de conciliación',
            data={
                'timestamp': db.query(func.now()).scalar().isoformat(),
                'salud_general': {
                    'tasa_asignacion': f'{tasa_asignacion:.1f}%',
                    'pagos_sin_asignar': pagos_sin_asignar[0],
                    'monto_sin_asignar': float(pagos_sin_asignar[1]),
                    'cuotas_sobre_aplicadas': sobre_aplicadas[0],
                    'cuotas_en_mora': en_mora
                },
                'estados_cuota': [
                    {
                        'estado': e[0],
                        'cantidad': e[1],
                        'monto': float(e[2])
                    }
                    for e in estados
                ],
                'indicadores': {
                    'status_general': 'healthy' if tasa_asignacion > 95 and sobre_aplicadas[0] == 0 else 'warning',
                    'mensaje': 'Sistema operando correctamente' if tasa_asignacion > 95 else 'Se detectaron problemas'
                }
            }
        ).dict()
    
    except Exception as e:
        return ResponseSchema(
            status='error',
            message=str(e),
            data={}
        ).dict()


@router.get('/conciliacion-metrics')
async def dashboard_conciliacion_metrics(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    "`"
    Métricas detalladas de conciliación con histórico.
    "`"
    
    try:
        # Auditoría del día
        auditoria_hoy = db.query(text('''
            SELECT 
              tipo_asignacion,
              resultado,
              COUNT(*) as cantidad,
              SUM(monto_asignado) as monto
            FROM auditoria_conciliacion_manual
            WHERE DATE(fecha_asignacion) = CURRENT_DATE
            GROUP BY tipo_asignacion, resultado
        ''')).fetchall()
        
        # Promedio de aplicación por pago
        promedio_aplicacion = db.query(text('''
            SELECT 
              AVG(cp.monto_aplicado) as promedio,
              MIN(cp.monto_aplicado) as minimo,
              MAX(cp.monto_aplicado) as maximo
            FROM cuota_pagos cp
        ''')).fetchone()
        
        # Cuotas que requieren intervención manual
        intervenciones_requeridas = db.query(text('''
            SELECT 
              COUNT(*) as cantidad
            FROM cuotas c
            LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
            WHERE c.estado = 'MORA' AND EXTRACT(DAY FROM NOW() - c.fecha_vencimiento) > 60
        ''')).fetchone()
        
        return ResponseSchema(
            status='success',
            message='Métricas detalladas de conciliación',
            data={
                'auditoria_hoy': [
                    {
                        'tipo': a[0],
                        'resultado': a[1],
                        'cantidad': a[2],
                        'monto': float(a[3]) if a[3] else 0
                    }
                    for a in auditoria_hoy
                ],
                'estadisticas_aplicacion': {
                    'promedio': float(promedio_aplicacion[0]) if promedio_aplicacion[0] else 0,
                    'minimo': float(promedio_aplicacion[1]) if promedio_aplicacion[1] else 0,
                    'maximo': float(promedio_aplicacion[2]) if promedio_aplicacion[2] else 0
                },
                'intervenciones_requeridas': intervenciones_requeridas[0]
            }
        ).dict()
    
    except Exception as e:
        return ResponseSchema(
            status='error',
            message=str(e),
            data={}
        ).dict()
