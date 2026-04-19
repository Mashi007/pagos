# -*- coding: utf-8 -*-
"""
Endpoints para diagnóstico y corrección de problemas críticos.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.response_schema import ResponseSchema
from app.services.diagnostico_critico_service import DiagnosticoCritico, CorrectoresCriticos

router = APIRouter(prefix='/api/v1/criticos', tags=['criticos'])


@router.get('/diagnostico/pagos-sin-asignar')
async def diagnostico_pagos_sin_asignar(
    db: Session = Depends(get_db),
    admin = Depends(get_current_user)
):
    """
    Diagnóstico: 14,127 pagos sin asignar a cuotas (3,426,096.76 BS = 49.2%)
    
    Retorna:
    - Cantidad total de pagos sin asignar
    - Monto total no aplicado
    - Categorización por antigüedad
    - Primeros 100 pagos para análisis
    """
    try:
        resultado = DiagnosticoCritico.diagnosticar_pagos_sin_asignar(db)
        
        return ResponseSchema(
            status='warning' if resultado['total_pagos'] > 0 else 'success',
            message=f"Se encontraron {resultado['total_pagos']} pagos sin asignar ({resultado['monto_total']:.2f} BS)",
            data=resultado
        ).dict()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/diagnostico/cuota-sobre-aplicada/{cuota_id}')
async def diagnostico_cuota_sobre_aplicada(
    cuota_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_user)
):
    """
    Diagnóstico: Cuota sobre-aplicada
    
    Ejemplo: Cuota 216933 con 96 BS exceso
    
    Retorna:
    - Monto de cuota vs total aplicado
    - Exceso exacto
    - Historial de pagos aplicados
    """
    try:
        resultado = DiagnosticoCritico.diagnosticar_cuota_sobre_aplicada(db, cuota_id)
        
        if 'error' in resultado:
            raise HTTPException(status_code=404, detail=resultado['error'])
        
        return ResponseSchema(
            status='warning' if resultado['exceso'] > 0 else 'success',
            message=f"Cuota {cuota_id}: {resultado['exceso']:.2f} BS sobre-aplicado",
            data=resultado
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/diagnostico/estados-inconsistentes')
async def diagnostico_estados_inconsistentes(
    db: Session = Depends(get_db),
    admin = Depends(get_current_user)
):
    """
    Diagnóstico: Estados de cuota inconsistentes
    
    Compara estado registrado vs estado calculado.
    Identifica cuotas MORA que deberían estar PAGADO o PARCIAL.
    """
    try:
        resultado = DiagnosticoCritico.diagnosticar_estados_inconsistentes(db)
        
        return ResponseSchema(
            status='warning' if resultado['inconsistencias'] > 0 else 'success',
            message=f"Se encontraron {resultado['inconsistencias']} inconsistencias en {resultado['total_mora']} cuotas MORA",
            data=resultado
        ).dict()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/corregir/cuota-sobre-aplicada/{cuota_id}')
async def corregir_cuota_sobre_aplicada(
    cuota_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_user)
):
    """
    Corrección: Reduce el exceso de dinero aplicado a una cuota.
    
    Estrategia:
    - Obtiene el exceso exacto
    - Reduce el monto del último pago aplicado
    - Registra en auditoría
    
    Solo para admin. Afecta tabla cuota_pagos.
    """
    try:
        resultado = CorrectoresCriticos.corregir_cuota_sobre_aplicada(db, cuota_id)
        
        if not resultado['success']:
            raise HTTPException(status_code=400, detail=resultado.get('message'))
        
        return ResponseSchema(
            status='success',
            message=resultado['message'],
            data=resultado
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/corregir/estados-inconsistentes')
async def corregir_estados_inconsistentes(
    db: Session = Depends(get_db),
    admin = Depends(get_current_user)
):
    """
    Corrección: Actualiza estados inconsistentes de cuotas.
    
    Estrategia:
    - Calcula el estado correcto para cada cuota MORA
    - Compara con estado registrado
    - Actualiza solo si hay diferencia
    
    Afecta todas las cuotas en estado MORA con inconsistencias.
    """
    try:
        resultado = CorrectoresCriticos.corregir_estados_mora_inconsistentes(db)
        
        if not resultado['success']:
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        return ResponseSchema(
            status='success',
            message=resultado['message'],
            data=resultado
        ).dict()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

