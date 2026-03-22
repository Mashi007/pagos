# -*- coding: utf-8 -*-
"""
Patch para mejorar validación de tasas de cambio.
Agrega endpoint para validación clara antes de procesar pagos.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.user_utils import user_is_administrator
from app.schemas.auth import UserResponse
from app.services.tasa_cambio_service import (
    obtener_tasa_hoy,
    obtener_tasa_por_fecha,
    debe_ingresar_tasa,
    fecha_hoy_caracas,
)
from app.models.tasa_cambio_diaria import TasaCambioDiaria

router = APIRouter(prefix="/admin/tasas-cambio", tags=["tasas-cambio"])


class ValidacionTasaResponse(BaseModel):
    """Respuesta de validación de tasa de cambio"""
    
    puede_procesar_pagos_bs: bool = Field(
        ..., 
        description="Si True, se pueden procesar pagos en Bolívares"
    )
    tasa_actual: Optional[float] = Field(
        None, 
        description="Tasa de cambio actual si está ingresada"
    )
    fecha_tasa: Optional[str] = Field(
        None, 
        description="Fecha de la tasa actual"
    )
    hora_obligatoria_desde: str = Field(
        "01:00",
        description="Hora desde la cual se debe ingresar tasa"
    )
    hora_obligatoria_hasta: str = Field(
        "23:59",
        description="Hora hasta la cual se puede ingresar tasa"
    )
    mensaje: str = Field(
        ...,
        description="Mensaje descriptivo del estado"
    )
    acciones_recomendadas: list = Field(
        default_factory=list,
        description="Acciones recomendadas si no puede procesar"
    )


@router.get(
    "/validar-para-pago",
    response_model=ValidacionTasaResponse,
    summary="Valida si se pueden procesar pagos en Bolívares",
    description="""
    Verifica si el sistema puede procesar pagos en Bolívares.
    
    - Si retorna puede_procesar_pagos_bs=true: Adelante, procesa el pago
    - Si retorna false: El admin debe ingresar la tasa o el usuario debe pagar en USD
    
    Úsalo ANTES de procesar cualquier pago en Bolívares.
    """
)
def validar_tasa_para_pago(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
    fecha_pago: Optional[date] = Query(
        None,
        description="Fecha de pago del reporte; valida tasa en tasas_cambio_diaria para esa fecha (Bs).",
    ),
):
    """
    Endpoint para validar si se pueden procesar pagos en Bolívares.
    Retorna un mensaje claro y acciones recomendadas.
    """
    
    # Verificar que sea admin o que tenga permisos (opcional para usuarios comunes)
    # Por ahora permitimos que cualquier usuario consulte
    
    debe_ingresar = debe_ingresar_tasa()
    if fecha_pago is not None:
        tasa = obtener_tasa_por_fecha(db, fecha_pago)
    else:
        tasa = obtener_tasa_hoy(db)

    # Caso 1: Tasa existe para la fecha de pago indicada o para hoy (Caracas)
    if tasa:
        return ValidacionTasaResponse(
            puede_procesar_pagos_bs=True,
            tasa_actual=float(tasa.tasa_oficial),
            fecha_tasa=tasa.fecha.isoformat() if tasa.fecha else None,
            hora_obligatoria_desde="01:00",
            hora_obligatoria_hasta="23:59",
            mensaje="✓ Sistema listo para procesar pagos en Bolívares",
            acciones_recomendadas=[
                "Proceder normalmente con pagos en BS",
                f"Tasa actual: 1 USD = {float(tasa.tasa_oficial)} BS"
            ]
        )
    
    if fecha_pago is not None:
        return ValidacionTasaResponse(
            puede_procesar_pagos_bs=False,
            tasa_actual=None,
            fecha_tasa=None,
            hora_obligatoria_desde="01:00",
            hora_obligatoria_hasta="23:59",
            mensaje=(
                "CRITICO: No hay tasa de cambio registrada para la fecha de pago "
                f"{fecha_pago.isoformat()}. Registrela en Administracion > Tasas de cambio para esa fecha."
            ),
            acciones_recomendadas=[
                "Registrar la tasa oficial para esa fecha en tasas_cambio_diaria",
                "O solicitar al cliente que reporte en USD",
            ],
        )

    # Caso 2: Tasa no existe y estamos en horario de ingreso obligatorio
    if debe_ingresar:
        return ValidacionTasaResponse(
            puede_procesar_pagos_bs=False,
            tasa_actual=None,
            fecha_tasa=None,
            hora_obligatoria_desde="01:00",
            hora_obligatoria_hasta="23:59",
            mensaje="🚨 CRÍTICO: Tasa de cambio no ingresada. Pagos en Bolívares serán RECHAZADOS.",
            acciones_recomendadas=[
                "1. URGENTE: Ingresa la tasa oficial del día",
                "2. O: Pídele al cliente que pague en USD",
                "3. O: Contacta a administración",
                "Ubicación: Panel Principal → Ingreso de Tasa de Cambio"
            ]
        )
    
    # Caso 3: Tasa no existe pero NO estamos en horario de ingreso aún
    return ValidacionTasaResponse(
        puede_procesar_pagos_bs=False,
        tasa_actual=None,
        fecha_tasa=None,
        hora_obligatoria_desde="01:00",
        hora_obligatoria_hasta="23:59",
        mensaje="⏰ Aún no es hora de ingresar la tasa de cambio (comienza a las 01:00 AM)",
        acciones_recomendadas=[
            "Espera hasta las 01:00 AM",
            "O: Pídele al cliente que pague en USD por ahora"
        ]
    )


@router.get(
    "/estado-completo",
    summary="Estado completo de tasas de cambio",
    description="Retorna estado detallado de tasas incluyendo auditoría"
)
def get_estado_completo_tasa(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Retorna información completa sobre el estado de las tasas.
    """
    
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    tasa_hoy = obtener_tasa_hoy(db)
    debe_ingresar = debe_ingresar_tasa()
    
    # Obtener tasas recientes para comparación
    tasas_recientes = db.query(TasaCambioDiaria).order_by(
        TasaCambioDiaria.fecha.desc()
    ).limit(5).all()
    
    return {
        "tasa_hoy": {
            "existe": tasa_hoy is not None,
            "valor": float(tasa_hoy.tasa_oficial) if tasa_hoy else None,
            "usuario_quien_ingreso": tasa_hoy.usuario_email if tasa_hoy else None,
            "fecha_ingreso": tasa_hoy.created_at.isoformat() if tasa_hoy else None,
            "ultima_actualizacion": tasa_hoy.updated_at.isoformat() if tasa_hoy else None
        },
        "obligatoriedad": {
            "debe_ingresar_ahora": debe_ingresar,
            "hora_desde": "01:00",
            "hora_hasta": "23:59",
            "mensaje": "Ingreso obligatorio entre 01:00 AM y 23:59 PM"
        },
        "cambios_recientes": [
            {
                "fecha": t.fecha.isoformat(),
                "tasa_oficial": float(t.tasa_oficial),
                "usuario_email": t.usuario_email,
                "cambio_porcentaje": (
                    round(((float(t.tasa_oficial) - float(tasas_recientes[i+1].tasa_oficial)) / 
                           float(tasas_recientes[i+1].tasa_oficial) * 100), 2)
                    if i < len(tasas_recientes) - 1
                    else 0
                )
            }
            for i, t in enumerate(tasas_recientes)
        ]
    }


# Ejemplo de uso en pagos_service.py:
# 
# def procesar_pago_en_bs(monto_bs: float, db: Session):
#     """Procesa pago en Bolívares"""
#     
#     # PASO 1: Validar que tasa esté ingresada
#     from app.services.tasa_cambio_service import obtener_tasa_hoy
#     
#     tasa = obtener_tasa_hoy(db)
#     if not tasa:
#         raise HTTPException(
#             status_code=400,
#             detail={
#                 "error": "TASA_NO_INGRESADA",
#                 "mensaje": "No se puede procesar pago en Bolívares. "
#                           "Tasa de cambio no ingresada. Usa USD.",
#                 "url_ayuda": "/api/admin/tasas-cambio/validar-para-pago"
#             }
#         )
#     
#     # PASO 2: Convertir a USD
#     from app.services.tasa_cambio_service import convertir_bs_a_usd
#     monto_usd = convertir_bs_a_usd(monto_bs, float(tasa.tasa_oficial))
#     
#     # PASO 3: Procesar con monto en USD
#     # ... resto del código

