# -*- coding: utf-8 -*-
"""
Endpoint para ejecutar actualizacion manual de prestamos a LIQUIDADO
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db
from app.core.auth import verificar_token_admin
from app.schemas.response_schema import ResponseSchema
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

router = APIRouter(prefix='/api/v1/prestamos', tags=['prestamos'])

@router.post('/actualizar-liquidado-manual')
async def actualizar_liquidado_manual(
    db: Session = Depends(get_db),
    usuario = Depends(verificar_token_admin)
):
    """
    Ejecuta manualmente la actualizacion de prestamos a LIQUIDADO.
    Solo para usuarios admin.
    """
    try:
        # Ejecutar funcion
        result = db.execute(text('''
            SELECT actualizar_prestamos_a_liquidado_automatico()
        ''')).fetchone()
        
        # Contar cambios hoy
        cambios_hoy = db.execute(text('''
            SELECT COUNT(*) FROM auditoria_cambios_estado_prestamo
            WHERE DATE(fecha_cambio) = CURRENT_DATE
        ''')).fetchone()
        
        # Obtener detalles de cambios recientes
        detalles = db.execute(text('''
            SELECT 
              prestamo_id, 
              estado_anterior, 
              estado_nuevo, 
              fecha_cambio,
              total_financiamiento,
              suma_pagado
            FROM auditoria_cambios_estado_prestamo
            WHERE DATE(fecha_cambio) = CURRENT_DATE
            ORDER BY fecha_cambio DESC
            LIMIT 10
        ''')).fetchall()
        
        return ResponseSchema(
            status='success',
            message='Actualizacion de prestamos a LIQUIDADO completada',
            data={
                'total_cambios_hoy': cambios_hoy[0],
                'ultima_ejecucion': datetime.now().isoformat(),
                'cambios_recientes': [
                    {
                        'prestamo_id': d[0],
                        'estado_anterior': d[1],
                        'estado_nuevo': d[2],
                        'fecha_cambio': d[3].isoformat() if d[3] else None,
                        'total_financiamiento': float(d[4]) if d[4] else 0,
                        'suma_pagado': float(d[5]) if d[5] else 0
                    }
                    for d in detalles
                ]
            }
        ).dict()
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Error al actualizar prestamos a LIQUIDADO: {str(e)}'
        )

@router.get('/auditoria-cambios-estado')
async def obtener_auditoria_cambios_estado(
    dias: int = 7,
    db: Session = Depends(get_db),
    usuario = Depends(verificar_token_admin)
):
    """
    Obtiene el historial de cambios de estado a LIQUIDADO.
    Por defecto ultimos 7 dias.
    """
    try:
        cambios = db.execute(text('''
            SELECT 
              id,
              prestamo_id,
              estado_anterior,
              estado_nuevo,
              motivo,
              fecha_cambio,
              total_financiamiento,
              suma_pagado
            FROM auditoria_cambios_estado_prestamo
            WHERE fecha_cambio >= CURRENT_DATE - INTERVAL ':dias days'
            ORDER BY fecha_cambio DESC
        '''), {'dias': dias}).fetchall()
        
        resumen = db.execute(text('''
            SELECT 
              COUNT(*) as total_cambios,
              COUNT(DISTINCT prestamo_id) as prestamos_afectados,
              SUM(total_financiamiento)::numeric(14,2) as suma_capital
            FROM auditoria_cambios_estado_prestamo
            WHERE fecha_cambio >= CURRENT_DATE - INTERVAL ':dias days'
        '''), {'dias': dias}).fetchone()
        
        return ResponseSchema(
            status='success',
            message=f'Historial de cambios de estado (ultimos {dias} dias)',
            data={
                'resumen': {
                    'total_cambios': resumen[0],
                    'prestamos_afectados': resumen[1],
                    'suma_capital': float(resumen[2]) if resumen[2] else 0
                },
                'cambios': [
                    {
                        'id': c[0],
                        'prestamo_id': c[1],
                        'estado_anterior': c[2],
                        'estado_nuevo': c[3],
                        'motivo': c[4],
                        'fecha_cambio': c[5].isoformat() if c[5] else None,
                        'total_financiamiento': float(c[6]) if c[6] else 0,
                        'suma_pagado': float(c[7]) if c[7] else 0
                    }
                    for c in cambios
                ]
            }
        ).dict()
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Error al obtener auditoria: {str(e)}'
        )

