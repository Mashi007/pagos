# -*- coding: utf-8 -*-
"""
Endpoint para documentación y referencia de estados de cuota.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.response_schema import ResponseSchema
from app.services.conciliacion_automatica_service import EstadoCuota

router = APIRouter(prefix='/api/v1/referencia', tags=['referencia'])


@router.get('/estados-cuota')
async def obtener_referencia_estados_cuota(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """
    Retorna documentación completa de todos los estados de cuota válidos.
    Útil para frontend y para entender el ciclo de vida de una cuota.
    """
    
    estados = {
        'PAGADO': {
            'codigo': EstadoCuota.PAGADO,
            'documentacion': EstadoCuota.obtener_documentacion(EstadoCuota.PAGADO),
            'condicion': 'Monto aplicado >= Monto de cuota (con tolerancia de 0.01)',
            'transiciones_permitidas': ['CANCELADA'],
            'color_frontend': '#10b981',  # Verde
            'icono': 'check-circle',
            'es_final': False,
            'requiere_cobranza': False
        },
        'PENDIENTE': {
            'codigo': EstadoCuota.PENDIENTE,
            'documentacion': EstadoCuota.obtener_documentacion(EstadoCuota.PENDIENTE),
            'condicion': 'Sin pagos aplicados o con vencimiento futuro',
            'transiciones_permitidas': ['PAGADO', 'MORA', 'PARCIAL', 'CANCELADA'],
            'color_frontend': '#f59e0b',  # Amarillo
            'icono': 'clock',
            'es_final': False,
            'requiere_cobranza': False
        },
        'MORA': {
            'codigo': EstadoCuota.MORA,
            'documentacion': EstadoCuota.obtener_documentacion(EstadoCuota.MORA),
            'condicion': 'Vencida (fecha_vencimiento < hoy) y sin pagar completamente',
            'transiciones_permitidas': ['PAGADO', 'PARCIAL', 'CANCELADA'],
            'color_frontend': '#ef4444',  # Rojo
            'icono': 'exclamation-circle',
            'es_final': False,
            'requiere_cobranza': True
        },
        'PARCIAL': {
            'codigo': EstadoCuota.PARCIAL,
            'documentacion': EstadoCuota.obtener_documentacion(EstadoCuota.PARCIAL),
            'condicion': 'Con pagos parciales: Monto aplicado < Monto de cuota',
            'transiciones_permitidas': ['PAGADO', 'MORA', 'CANCELADA'],
            'color_frontend': '#8b5cf6',  # Púrpura
            'icono': 'minus-circle',
            'es_final': False,
            'requiere_cobranza': True
        },
        'CANCELADA': {
            'codigo': EstadoCuota.CANCELADA,
            'documentacion': EstadoCuota.obtener_documentacion(EstadoCuota.CANCELADA),
            'condicion': 'Anulada o no vigente por decisión administrativa',
            'transiciones_permitidas': [],
            'color_frontend': '#6b7280',  # Gris
            'icono': 'x-circle',
            'es_final': True,
            'requiere_cobranza': False
        }
    }
    
    return ResponseSchema(
        status='success',
        message='Documentación completa de estados de cuota',
        data={
            'estados': estados,
            'ciclo_vida': [
                {
                    'paso': 1,
                    'estado': 'PENDIENTE',
                    'descripcion': 'Cuota creada, aún no vencida'
                },
                {
                    'paso': 2,
                    'estado': 'MORA',
                    'descripcion': 'Cuota vencida, inicia cobranza'
                },
                {
                    'paso': 3,
                    'estado_posible_a': 'PARCIAL',
                    'estado_posible_b': 'PAGADO',
                    'descripcion': 'Se aplican pagos: parciales o completos'
                },
                {
                    'paso': 4,
                    'estado': 'CANCELADA',
                    'descripcion': '(Opcional) Cuota anulada administrativamente'
                }
            ],
            'transiciones': {
                'PENDIENTE': ['PAGADO', 'MORA', 'PARCIAL', 'CANCELADA'],
                'MORA': ['PAGADO', 'PARCIAL', 'CANCELADA'],
                'PARCIAL': ['PAGADO', 'MORA', 'CANCELADA'],
                'PAGADO': ['CANCELADA'],
                'CANCELADA': []
            },
            'reglas_negocio': [
                'Una cuota en MORA activa alertas de cobranza automáticamente',
                'No se puede aplicar dinero a cuota CANCELADA',
                'La transición automática a MORA ocurre cuando fecha_vencimiento < hoy',
                'La tolerancia de 0.01 se aplica para diferencias de redondeo (centavos)',
                'El estado se calcula en tiempo real según monto aplicado y fecha de vencimiento'
            ]
        }
    ).dict()
