"""
EJEMPLOS DE USO - Servicios de Préstamos
========================================

Este archivo muestra ejemplos prácticos de cómo utilizar los servicios
de préstamos en endpoints y otros contextos.
"""

# ============================================================================
# EJEMPLO 1: CREAR UN PRÉSTAMO COMPLETO
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from app.core.database import get_db
from app.services.prestamos import (
    PrestamosService,
    con_manejo_errores_prestamos,
    obtener_servicio_prestamos,
)

router = APIRouter(prefix="/prestamos", tags=["prestamos"])


@router.post("/")
@con_manejo_errores_prestamos
def crear_prestamo(datos: dict, db: Session = Depends(get_db)):
    """
    Crea un nuevo préstamo con validaciones automáticas.

    El decorador @con_manejo_errores_prestamos convierte excepciones
    de servicios en respuestas HTTP apropiadas.
    """
    service = obtener_servicio_prestamos(db)

    prestamo = service.crear_prestamo({
        'cliente_id': datos['cliente_id'],
        'cedula': datos['cedula'],
        'nombres': datos['nombres'],
        'total_financiamiento': datos['monto'],
        'fecha_requerimiento': date.today(),
        'modalidad_pago': datos.get('modalidad_pago', 'MENSUAL'),
        'numero_cuotas': datos['cuotas'],
        'cuota_periodo': datos['cuota_fija'],
        'tasa_interes': datos.get('tasa', 0.0),
        'producto': datos.get('producto', ''),
        'analista': datos.get('analista', ''),
        'estado': 'DRAFT',
    })

    return {
        'id': prestamo.id,
        'estado': prestamo.estado,
        'mensaje': 'Préstamo creado exitosamente'
    }


# ============================================================================
# EJEMPLO 2: OBTENER PRÉSTAMO Y TABLA DE AMORTIZACIÓN
# ============================================================================

@router.get("/{prestamo_id}")
@con_manejo_errores_prestamos
def obtener_prestamo_detalle(prestamo_id: int, db: Session = Depends(get_db)):
    """
    Obtiene préstamo completo con tabla de amortización.
    """
    service = obtener_servicio_prestamos(db)

    # Obtener información del préstamo
    prestamo = service.obtener_prestamo(prestamo_id)

    # Obtener tabla de amortización
    tabla_amortizacion = service.obtener_tabla_amortizacion(prestamo_id)

    return {
        'prestamo': {
            'id': prestamo.id,
            'cliente_id': prestamo.cliente_id,
            'monto': float(prestamo.total_financiamiento),
            'cuotas': prestamo.numero_cuotas,
            'tasa': float(prestamo.tasa_interes),
            'estado': prestamo.estado,
            'modalidad': prestamo.modalidad_pago,
        },
        'amortizacion': tabla_amortizacion,
    }


# ============================================================================
# EJEMPLO 3: CAMBIAR ESTADO DE PRÉSTAMO (CON VALIDACIONES)
# ============================================================================

@router.post("/{prestamo_id}/aprobar")
@con_manejo_errores_prestamos
def aprobar_prestamo(prestamo_id: int, usuario: str, db: Session = Depends(get_db)):
    """
    Aprueba un préstamo.

    Esto:
    1. Valida que la transición de estado sea permitida
    2. Registra al usuario que aprobó
    3. Genera la tabla de amortización automáticamente
    """
    service = obtener_servicio_prestamos(db)

    prestamo_actualizado = service.cambiar_estado_prestamo(
        prestamo_id,
        nuevo_estado='APROBADO',
        usuario_cambio=usuario
    )

    return {
        'id': prestamo_actualizado.id,
        'estado': prestamo_actualizado.estado,
        'mensaje': 'Préstamo aprobado. Tabla de amortización generada.'
    }


# ============================================================================
# EJEMPLO 4: REGISTRAR PAGO DE CUOTA
# ============================================================================

@router.post("/cuotas/{cuota_id}/pagar")
@con_manejo_errores_prestamos
def pagar_cuota(cuota_id: int, monto: float, db: Session = Depends(get_db)):
    """
    Registra un pago parcial o total de una cuota.

    El estado de la cuota se actualiza automáticamente:
    - PENDIENTE: sin pagos
    - PARCIAL: pagos parciales
    - PAGADO: completamente pagada
    """
    service = obtener_servicio_prestamos(db)

    cuota_actualizada = service.registrar_pago_cuota(cuota_id, monto)

    return {
        'cuota_id': cuota_actualizada['id'],
        'estado': cuota_actualizada['estado'],
        'monto_cuota': cuota_actualizada['monto_cuota'],
        'monto_pagado': cuota_actualizada['monto_pagado'],
        'pendiente': (
            cuota_actualizada['monto_cuota'] - cuota_actualizada['monto_pagado']
        ),
    }


# ============================================================================
# EJEMPLO 5: OBTENER CUOTAS VENCIDAS (GESTIÓN DE COBRANZAS)
# ============================================================================

@router.get("/{prestamo_id}/cuotas-vencidas")
@con_manejo_errores_prestamos
def obtener_cuotas_vencidas(prestamo_id: int, db: Session = Depends(get_db)):
    """
    Obtiene todas las cuotas vencidas de un préstamo.
    Útil para gestión de cobranzas y alertas.
    """
    service = obtener_servicio_prestamos(db)

    cuotas_vencidas = service.amortizacion.obtener_cuotas_vencidas(prestamo_id)

    total_adeudado = sum(
        c['monto_cuota'] - c['monto_pagado']
        for c in cuotas_vencidas
    )

    return {
        'prestamo_id': prestamo_id,
        'cantidad_cuotas_vencidas': len(cuotas_vencidas),
        'total_adeudado': total_adeudado,
        'cuotas': cuotas_vencidas,
    }


# ============================================================================
# EJEMPLO 6: OBTENER CUOTAS PRÓXIMAS A VENCER
# ============================================================================

@router.get("/{prestamo_id}/proximas-cuotas")
@con_manejo_errores_prestamos
def obtener_proximas_cuotas(
    prestamo_id: int,
    dias_adelante: int = 30,
    db: Session = Depends(get_db)
):
    """
    Obtiene cuotas que vencen en los próximos N días.
    Útil para notificaciones proactivas.
    """
    service = obtener_servicio_prestamos(db)

    cuotas = service.amortizacion.obtener_cuotas_proximas(
        prestamo_id,
        dias_adelante
    )

    return {
        'prestamo_id': prestamo_id,
        'dias_adelante': dias_adelante,
        'cantidad': len(cuotas),
        'cuotas': cuotas,
    }


# ============================================================================
# EJEMPLO 7: OBTENER ESTADO COMPLETO DE AMORTIZACIÓN
# ============================================================================

@router.get("/{prestamo_id}/estado-amortizacion")
@con_manejo_errores_prestamos
def obtener_estado_amortizacion(prestamo_id: int, db: Session = Depends(get_db)):
    """
    Obtiene el estado resumido de toda la amortización.
    Incluye: cuotas pagadas, pendientes, saldo total, etc.
    """
    service = obtener_servicio_prestamos(db)

    estado = service.amortizacion.calcular_estado_amortizacion(prestamo_id)

    return {
        'prestamo_id': prestamo_id,
        'estado': estado,
        'progreso': f"{estado['porcentaje_pagado']:.1f}% completado",
    }


# ============================================================================
# EJEMPLO 8: USAR ADAPTADOR LEGACY (SIN EXCEPCIONES)
# ============================================================================

from app.services.prestamos import AdaptadorPrestamosLegacy


@router.get("/legacy/{prestamo_id}/resumen")
def obtener_resumen_legacy(prestamo_id: int, db: Session = Depends(get_db)):
    """
    Usa el adaptador legacy que no lanza excepciones.
    Retorna None o dicts vacíos en lugar de HTTPException.

    Útil para migración gradual de endpoints existentes.
    """
    adaptador = AdaptadorPrestamosLegacy(db)

    resumen = adaptador.obtener_resumen_prestamo(prestamo_id)

    if resumen is None:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    return resumen


# ============================================================================
# EJEMPLO 9: VALIDAR DATOS ANTES DE CREAR (SIN LANZAR EXCEPCIONES)
# ============================================================================

@router.post("/validar-datos")
def validar_datos_prestamo(datos: dict, db: Session = Depends(get_db)):
    """
    Valida datos sin crear el préstamo.
    Retorna (es_valido, mensaje_error).

    Útil para validación en formularios frontend.
    """
    adaptador = AdaptadorPrestamosLegacy(db)

    es_valido, error = adaptador.validar_datos_antes_crear(datos)

    return {
        'valido': es_valido,
        'error': error,
    }


# ============================================================================
# EJEMPLO 10: GENERAR TABLA DE AMORTIZACIÓN MANUALMENTE
# ============================================================================

@router.post("/{prestamo_id}/generar-amortizacion")
@con_manejo_errores_prestamos
def generar_amortizacion(
    prestamo_id: int,
    regenerar: bool = False,
    db: Session = Depends(get_db)
):
    """
    Genera o regenera la tabla de amortización.

    regenerar=True: borra la tabla existente y crea una nueva
    regenerar=False: solo genera si no existe
    """
    service = obtener_servicio_prestamos(db)

    tabla = service.generar_tabla_amortizacion(
        prestamo_id,
        regenerar=regenerar
    )

    return {
        'prestamo_id': prestamo_id,
        'cantidad_cuotas': len(tabla),
        'primera_cuota': tabla[0] if tabla else None,
        'ultima_cuota': tabla[-1] if tabla else None,
    }


# ============================================================================
# EJEMPLO 11: OBTENER PRÉSTAMOS CON CUOTAS VENCIDAS (PARA COBRANZA)
# ============================================================================

@router.get("/cobranza/en-atraso")
def obtener_prestamos_en_atraso(db: Session = Depends(get_db)):
    """
    Obtiene todos los préstamos con cuotas vencidas.
    Útil para equipo de cobranzas.
    """
    service = obtener_servicio_prestamos(db)

    prestamos_vencidos = service.obtener_prestamos_vencidos(limit=100)

    return {
        'total': len(prestamos_vencidos),
        'prestamos': prestamos_vencidos,
    }


# ============================================================================
# EJEMPLO 12: OBTENER ESTADÍSTICAS GENERALES
# ============================================================================

@router.get("/estadisticas/general")
def obtener_estadisticas(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas generales de préstamos:
    - Total de préstamos
    - Monto total otorgado
    - Desglose por estado
    """
    service = obtener_servicio_prestamos(db)

    stats = service.obtener_estadistica_prestamos()

    return stats


# ============================================================================
# EJEMPLO 13: CALCULAR CUOTA FIJA
# ============================================================================

@router.post("/calcular-cuota")
def calcular_cuota_fija(
    principal: float,
    tasa_anual: float,
    numero_cuotas: int,
    modalidad: str = "MENSUAL",
    db: Session = Depends(get_db)
):
    """
    Calcula la cuota fija para un préstamo.
    Útil para simuladores y cotizaciones.
    """
    service = obtener_servicio_prestamos(db)

    cuota = service.calculo.calcular_cuota_fija(
        principal,
        tasa_anual,
        numero_cuotas,
        modalidad
    )

    # Calcular tabla de amortización de ejemplo
    interes_total = 0.0
    saldo = principal

    for i in range(numero_cuotas):
        interes = service.calculo.calcular_interes_periodo(
            saldo,
            tasa_anual,
            modalidad
        )
        interes_total += interes
        amortizacion = cuota - interes
        saldo -= amortizacion

    return {
        'cuota_fija': round(cuota, 2),
        'cuota_mensual': round(cuota, 2),
        'principal': principal,
        'tasa_anual': tasa_anual,
        'numero_cuotas': numero_cuotas,
        'interes_total': round(interes_total, 2),
        'total_a_pagar': round(principal + interes_total, 2),
    }


# ============================================================================
# EJEMPLO 14: USAR CON CONTEXT MANAGER (PATTERN AVANZADO)
# ============================================================================

def procesar_prestamo_completo(cliente_id: int, db: Session):
    """
    Ejemplo de flujo completo: crear, aprobar, generar amortización.
    """
    service = PrestamosService(db)

    try:
        # 1. Crear préstamo
        prestamo = service.crear_prestamo({
            'cliente_id': cliente_id,
            'cedula': '123456789',
            'nombres': 'Cliente Test',
            'total_financiamiento': 10000.0,
            'fecha_requerimiento': date.today(),
            'modalidad_pago': 'MENSUAL',
            'numero_cuotas': 12,
            'cuota_periodo': 833.33,
            'tasa_interes': 12.0,
            'producto': 'Préstamo Automático',
            'analista': 'Juan Pérez',
        })

        # 2. Cambiar a ENVIADO
        prestamo = service.cambiar_estado_prestamo(
            prestamo.id,
            'ENVIADO',
            usuario_cambio='gerente@empresa.com'
        )

        # 3. Aprobar
        prestamo = service.cambiar_estado_prestamo(
            prestamo.id,
            'APROBADO',
            usuario_cambio='jefe@empresa.com'
        )

        # 4. Obtener tabla de amortización
        tabla = service.obtener_tabla_amortizacion(prestamo.id)

        # 5. Cambiar a ACTIVO
        prestamo = service.cambiar_estado_prestamo(
            prestamo.id,
            'ACTIVO',
            usuario_cambio='operaciones@empresa.com'
        )

        return {
            'prestamo_id': prestamo.id,
            'estado': prestamo.estado,
            'cuotas': len(tabla),
            'estado_amortizacion': (
                service.amortizacion.calcular_estado_amortizacion(prestamo.id)
            ),
        }

    except Exception as e:
        # Manejar excepciones de servicios
        return {'error': str(e), 'success': False}


# ============================================================================
# INTEGRACIÓN CON LOGGING Y AUDITORÍA
# ============================================================================

import logging

logger = logging.getLogger(__name__)


@router.post("/{prestamo_id}/auditar")
@con_manejo_errores_prestamos
def registrar_cambio_estado(
    prestamo_id: int,
    nuevo_estado: str,
    usuario: str,
    observaciones: str,
    db: Session = Depends(get_db)
):
    """
    Cambio de estado con logging y auditoría.
    """
    service = obtener_servicio_prestamos(db)

    logger.info(
        f"Cambio de estado solicitado",
        extra={
            'prestamo_id': prestamo_id,
            'usuario': usuario,
            'nuevo_estado': nuevo_estado,
        }
    )

    try:
        prestamo = service.cambiar_estado_prestamo(
            prestamo_id,
            nuevo_estado,
            usuario_cambio=usuario,
            observaciones=observaciones
        )

        logger.info(
            f"Cambio de estado exitoso",
            extra={
                'prestamo_id': prestamo_id,
                'estado': prestamo.estado,
            }
        )

        return {
            'success': True,
            'prestamo_id': prestamo.id,
            'estado': prestamo.estado,
        }

    except Exception as e:
        logger.error(
            f"Error al cambiar estado: {str(e)}",
            extra={'prestamo_id': prestamo_id},
            exc_info=True
        )
        raise
