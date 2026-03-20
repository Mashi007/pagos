# -*- coding: utf-8 -*-
"""
Endpoints para conciliación automática y manual de pagos.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.response_schema import ResponseSchema
from app.services.conciliacion_automatica_service import ConciliacionAutomaticaService, EstadoCuota
from app.core.auth import verificar_token_admin

router = APIRouter(prefix='/api/v1/conciliacion', tags=['conciliacion'])


@router.post('/asignar-pagos-automatico')
async def asignar_pagos_automatico(
    prestamo_id: int = None,
    db: Session = Depends(get_db),
    usuario = Depends(verificar_token_admin)
):
    """
    Asigna automáticamente pagos sin cuotas a cuotas pendientes (FIFO).
    Requiere: Token de administrador
    """
    try:
        resultado = ConciliacionAutomaticaService.asignar_pagos_no_conciliados(
            db,
            prestamo_id=prestamo_id,
            usuario_id=usuario.get('id') if isinstance(usuario, dict) else getattr(usuario, 'id', None)
        )
        
        return ResponseSchema(
            status='success',
            message=f"Asignación completada: {resultado['exitosas']} exitosas, {resultado['fallidas']} fallidas",
            data=resultado
        ).dict()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en asignación automática: {str(e)}")


@router.get('/estados-cuotas')
async def obtener_estados_cuotas(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """
    Retorna documentación de estados de cuota y estadísticas.
    Estados válidos: PAGADO, PENDIENTE, MORA, PARCIAL, CANCELADA
    """
    try:
        resumen = ConciliacionAutomaticaService.obtener_resumen_estado_cuotas(db)
        
        documentacion = {
            estado: EstadoCuota.obtener_documentacion(estado)
            for estado in EstadoCuota.ESTADOS_VALIDOS
        }
        
        return ResponseSchema(
            status='success',
            message='Estados de cuota con documentación y estadísticas',
            data={
                'resumen': resumen,
                'documentacion': documentacion
            }
        ).dict()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/cuotas-sobre-aplicadas')
async def obtener_cuotas_sobre_aplicadas(
    db: Session = Depends(get_db),
    usuario = Depends(verificar_token_admin)
):
    """
    Identifica cuotas que tienen más dinero aplicado que su monto.
    Ayuda a detectar errores de conciliación.
    """
    try:
        cuotas_problematicas = ConciliacionAutomaticaService.obtener_cuotas_sobre_aplicadas(db)
        
        return ResponseSchema(
            status='success' if not cuotas_problematicas else 'warning',
            message=f"Se encontraron {len(cuotas_problematicas)} cuotas con sobre-aplicación" if cuotas_problematicas else "No hay cuotas sobre-aplicadas",
            data={'cuotas': cuotas_problematicas}
        ).dict()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
