"""
Servicio para evaluación de riesgo de préstamos
Implementa los 6 criterios de evaluación según TABLA 1 compartida
"""

import logging
from decimal import Decimal
from typing import Dict

from sqlalchemy.orm import Session

from app.models.prestamo_evaluacion import PrestamoEvaluacion

logger = logging.getLogger(__name__)

# ============================================
# TABLA 1: CRITERIOS Y PESOS DE EVALUACIÓN
# ============================================
CRITERIOS_PESOS = {
    "ratio_endeudamiento": 17,  # 17% (Criterio 1.A)
    "ratio_cobertura": 16,  # 16% (Criterio 1.B)
    "historial_crediticio": 20,  # 20%
    "estabilidad_laboral": 15,  # 15%
    "tipo_empleo": 10,  # 10%
    "enganche_garantias": 10,  # 10%
}


def calcular_ratio_endeudamiento(
    ingresos_mensuales: Decimal,
    otras_deudas: Decimal,
) -> Decimal:
    """
    CRITERIO 1.A: RATIO DE ENDEUDAMIENTO (17 puntos - 17%)
    
    Formula: (Otras Deudas / Ingresos) × 100
    IMPORTANTE: NO incluir la cuota del préstamo propuesto, solo deudas actuales

    Returns:
        - Decimal con el valor del ratio como porcentaje (ej: 0.45 = 45%)
    """
    if ingresos_mensuales <= 0:
        return Decimal("999.99")  # Indicador de error

    ratio = (otras_deudas / ingresos_mensuales) * Decimal(100)
    return ratio


def evaluar_ratio_endeudamiento_puntos(ratio: Decimal) -> Decimal:
    """
    CRITERIO 1.A: Evalúa puntos según ratio de endeudamiento.
    
    Rangos:
    - < 25%  -> Excelente -> 17 puntos
    - 25-35% -> Bueno     -> 13 puntos
    - 35-50% -> Regular   -> 7 puntos
    - > 50%  -> Malo      -> 2 puntos

    Returns:
        Puntos de 0 a 17
    """
    if ratio < Decimal("25"):  # Menos de 25%
        return Decimal(17)
    elif ratio < Decimal("35"):  # 25% - 34.99%
        return Decimal(13)
    elif ratio < Decimal("50"):  # 35% - 49.99%
        return Decimal(7)
    else:  # 50% o más
        return Decimal(2)


def calcular_ratio_cobertura(
    ingresos_mensuales: Decimal,
    gastos_fijos: Decimal,
    otras_deudas: Decimal,
    cuota: Decimal,
) -> Decimal:
    """
    CRITERIO 1.B: RATIO DE COBERTURA (16 puntos - 16%)
    
    Formula: Disponible = Ingresos - Gastos Fijos - Otras Deudas
    Formula: Ratio = Disponible / Cuota

    Returns:
        Decimal con el ratio (cuántas veces cubre el disponible a la cuota)
    """
    if cuota <= 0:
        return Decimal("0")  # Sin cuota, ratio 0

    disponible = ingresos_mensuales - gastos_fijos - otras_deudas
    ratio = disponible / cuota
    return ratio


def evaluar_ratio_cobertura_puntos(ratio: Decimal) -> tuple[Decimal, bool]:
    """
    CRITERIO 1.B: Evalúa puntos según ratio de cobertura.
    
    Rangos:
    - > 2.5x     -> Excelente     -> 16 puntos
    - 2.0x-2.5x  -> Bueno         -> 13 puntos
    - 1.5x-2.0x  -> Regular       -> 7 puntos
    - < 1.5x     -> Insuficiente  -> 0 puntos (RECHAZO)

    Returns:
        Tuple: (puntos, rechazo_automatico)
        Puntos de 0 a 16
    """
    if ratio > Decimal("2.5"):  # Más de 2.5x
        return Decimal(16), False
    elif ratio >= Decimal("2.0"):  # 2.0x - 2.5x
        return Decimal(13), False
    elif ratio >= Decimal("1.5"):  # 1.5x - 1.99x
        return Decimal(7), False
    else:  # Menos de 1.5x - RECHAZO
        return Decimal(0), True


def evaluar_historial_crediticio(calificacion: str) -> Dict[str, Decimal]:
    """
    Evalúa historial crediticio basado en calificación.

    Nueva escala:
    - Categoría A (20 puntos): Persona que mantiene todos sus pagos al día
    - Categoría B (15 puntos): Persona con atrasos menores o debilidades en su capacidad de pago
    - Categoría C (8 puntos): Persona con atrasos moderados que comprometen el pago normal
    - Categoría D (2 puntos): Persona con mora significativa (difícil cobro)
    - Categoría E (0 puntos): Persona con créditos prácticamente irrecuperables

    Args:
        calificacion: "A", "B", "C", "D", "E"

    Returns:
        Dict con puntos y descripción
    """
    evaluaciones = {
        "A": {"puntos": Decimal(20), "descripcion": "Todos los pagos al día"},
        "B": {
            "puntos": Decimal(15),
            "descripcion": "Atrasos menores o debilidades en capacidad de pago",
        },
        "C": {
            "puntos": Decimal(8),
            "descripcion": "Atrasos moderados que comprometen el pago normal",
        },
        "D": {
            "puntos": Decimal(2),
            "descripcion": "Mora significativa (difícil cobro)",
        },
        "E": {
            "puntos": Decimal(0),
            "descripcion": "Créditos prácticamente irrecuperables",
        },
    }

    return evaluaciones.get(
        calificacion.upper(), {"puntos": Decimal(0), "descripcion": "Desconocido"}
    )


def evaluar_estabilidad_laboral(anos_empleo: Decimal) -> Decimal:
    """
    Evalúa estabilidad laboral según años en el trabajo.

    Returns:
        Puntos de 0 a 15
    """
    if anos_empleo >= Decimal(5):
        return Decimal(15)
    elif anos_empleo >= Decimal(3):
        return Decimal(12)
    elif anos_empleo >= Decimal(1):
        return Decimal(8)
    elif anos_empleo >= Decimal(0.5):  # 6 meses
        return Decimal(5)
    else:
        return Decimal(2)


def evaluar_tipo_empleo(tipo: str) -> Dict[str, Decimal]:
    """
    Evalúa tipo de empleo.

    Args:
        tipo: "FORMAL", "INDEPENDIENTE", "CONTRATADO", "TEMPORAL"

    Returns:
        Dict con puntos y descripción
    """
    evaluaciones = {
        "FORMAL": {
            "puntos": Decimal(10),
            "descripcion": "Empleo formal con beneficios",
        },
        "INDEPENDIENTE": {
            "puntos": Decimal(7),
            "descripcion": "Trabajador independiente estable",
        },
        "CONTRATADO": {
            "puntos": Decimal(6),
            "descripcion": "Contratado por tiempo determinado",
        },
        "TEMPORAL": {"puntos": Decimal(3), "descripcion": "Empleo temporal o eventual"},
    }

    return evaluaciones.get(
        tipo.upper(), {"puntos": Decimal(0), "descripcion": "Desconocido"}
    )


def calcular_ltv(
    enganche_pagado: Decimal,
    monto_financiado: Decimal,
) -> Decimal:
    """
    TABLA 7: ENGANCHE Y GARANTÍAS (LTV - Loan to Value)

    Formula: (Enganche Pagado / Monto Financiado) * 100

    Mide el porcentaje de enganche sobre el financiamiento.

    Returns:
        Porcentaje LTV
    """
    if monto_financiado <= 0:
        return Decimal("0.00")

    ltv = (enganche_pagado / monto_financiado) * Decimal(100)
    return ltv


def evaluar_enganche_garantias(ltv: Decimal) -> Decimal:
    """
    Evalúa enganche y garantías según LTV.

    Returns:
        Puntos de 0 a 10
    """
    if ltv >= Decimal(30):  # 30% o más de enganche
        return Decimal(10)
    elif ltv >= Decimal(20):  # 20-29%
        return Decimal(8)
    elif ltv >= Decimal(15):  # 15-19%
        return Decimal(6)
    elif ltv >= Decimal(10):  # 10-14%
        return Decimal(4)
    elif ltv >= Decimal(5):  # 5-9%
        return Decimal(2)
    else:  # Menos de 5%
        return Decimal(0)


def clasificar_riesgo_total(puntuacion_total: Decimal) -> str:
    """
    TABLA 8: CLASIFICACIÓN FINAL DE RIESGO

    Returns:
        "BAJO", "MODERADO", "ALTO", "CRÍTICO"
    """
    if puntuacion_total >= Decimal(80):
        return "BAJO"
    elif puntuacion_total >= Decimal(60):
        return "MODERADO"
    elif puntuacion_total >= Decimal(40):
        return "ALTO"
    else:
        return "CRÍTICO"


def determinar_decision_final(
    puntuacion_total: Decimal, tiene_red_flags: bool = False
) -> str:
    """
    TABLA 8: Determina la decisión final del préstamo.

    Args:
        puntuacion_total: Puntuación total de 0-100
        tiene_red_flags: Si tiene señales de alerta

    Returns:
        "APROBADO", "CONDICIONAL", "REQUIERE_MITIGACION", "RECHAZADO"
    """
    if tiene_red_flags:
        return "RECHAZADO"

    if puntuacion_total >= Decimal(70):
        return "APROBADO"
    elif puntuacion_total >= Decimal(50):
        return "CONDICIONAL"
    elif puntuacion_total >= Decimal(35):
        return "REQUIERE_MITIGACION"
    else:
        return "RECHAZADO"


def aplicar_condiciones_segun_riesgo(
    clasificacion_riesgo: str,
    puntuacion_total: Decimal,
) -> Dict[str, any]:
    """
    TABLA 9: CONDICIONES SEGÚN NIVEL DE RIESGO

    Returns:
        Dict con tasa_interes_aplicada, plazo_maximo, enganche_minimo, requisitos_adicionales
    """
    condiciones = {
        "BAJO": {
            "tasa_interes_aplicada": Decimal("8.0"),
            "plazo_maximo": 36,
            "enganche_minimo": Decimal("15.0"),
            "requisitos_adicionales": "Ninguno",
        },
        "MODERADO": {
            "tasa_interes_aplicada": Decimal("12.0"),
            "plazo_maximo": 30,
            "enganche_minimo": Decimal("20.0"),
            "requisitos_adicionales": "Garante opcional",
        },
        "ALTO": {
            "tasa_interes_aplicada": Decimal("18.0"),
            "plazo_maximo": 24,
            "enganche_minimo": Decimal("30.0"),
            "requisitos_adicionales": "Garante obligatorio",
        },
        "CRÍTICO": {
            "tasa_interes_aplicada": Decimal("25.0"),
            "plazo_maximo": 18,
            "enganche_minimo": Decimal("40.0"),
            "requisitos_adicionales": "Garante y colateral",
        },
    }

    return condiciones.get(clasificacion_riesgo, condiciones["CRÍTICO"])


def calcular_evaluacion_completa(datos_evaluacion: Dict) -> PrestamoEvaluacion:
    """
    Calcula la evaluación completa de un préstamo usando los 6 criterios.

    Args:
        datos_evaluacion: Dict con datos financieros del cliente

    Returns:
        PrestamoEvaluacion con la evaluación completa
    """
    # Extraer datos
    ingresos = Decimal(str(datos_evaluacion.get("ingresos_mensuales", 0)))
    gastos_fijos = Decimal(str(datos_evaluacion.get("gastos_fijos_mensuales", 0)))
    otras_deudas = Decimal(str(datos_evaluacion.get("otras_deudas", 0)))  # Deudas actuales del cliente
    cuota = Decimal(str(datos_evaluacion.get("cuota_mensual", 0)))
    historial = datos_evaluacion.get("historial_crediticio", "DESCONOCIDO")
    anos_trabajo = Decimal(str(datos_evaluacion.get("anos_empleo", 0)))
    tipo_trabajo = datos_evaluacion.get("tipo_empleo", "DESCONOCIDO")
    enganche = Decimal(str(datos_evaluacion.get("enganche_pagado", 0)))
    monto_financiado = Decimal(str(datos_evaluacion.get("monto_financiado", 0)))

    # Criterio 1.A: Ratio de Endeudamiento (NO incluir cuota del préstamo propuesto)
    ratio_end = calcular_ratio_endeudamiento(ingresos, otras_deudas)
    puntos_end = evaluar_ratio_endeudamiento_puntos(ratio_end)

    # Criterio 1.B: Ratio de Cobertura
    ratio_cob = calcular_ratio_cobertura(ingresos, gastos_fijos, otras_deudas, cuota)
    puntos_cob, rechazo_automatico = evaluar_ratio_cobertura_puntos(ratio_cob)
    
    # Si ratio de cobertura < 1.5x, rechazo automático
    if rechazo_automatico:
        logger.warning("RECHAZO AUTOMÁTICO: Ratio de cobertura < 1.5x (insuficiente para cubrir cuota)")
        # Retornar evaluación con rechazo inmediato
        evaluacion = PrestamoEvaluacion(
            prestamo_id=datos_evaluacion.get("prestamo_id"),
            ratio_endeudamiento_puntos=puntos_end,
            ratio_endeudamiento_calculo=ratio_end,
            ratio_cobertura_puntos=Decimal(0),
            ratio_cobertura_calculo=ratio_cob,
            historial_crediticio_puntos=Decimal(0),
            historial_crediticio_descripcion="RECHAZADO: Ratio de cobertura insuficiente",
            estabilidad_laboral_puntos=Decimal(0),
            anos_empleo=anos_trabajo,
            tipo_empleo_puntos=Decimal(0),
            tipo_empleo_descripcion="No evaluado",
            enganche_garantias_puntos=Decimal(0),
            enganche_garantias_calculo=Decimal(0),
            puntuacion_total=puntos_end,  # Solo cuenta el ratio de endeudamiento
            clasificacion_riesgo="CRÍTICO",
            decision_final="RECHAZADO",
            tasa_interes_aplicada=None,
            plazo_maximo=0,
            enganche_minimo=None,
            requisitos_adicionales="RECHAZO: Ratio de cobertura insuficiente (< 1.5x). El disponible no alcanza para cubrir la cuota del préstamo.",
        )
        return evaluacion

    # Criterio 3: Historial Crediticio
    eval_hist = evaluar_historial_crediticio(historial)
    puntos_hist = eval_hist["puntos"]
    desc_hist = eval_hist["descripcion"]

    # Criterio 4: Estabilidad Laboral
    puntos_est = evaluar_estabilidad_laboral(anos_trabajo)

    # Criterio 5: Tipo de Empleo
    eval_tipo = evaluar_tipo_empleo(tipo_trabajo)
    puntos_tipo = eval_tipo["puntos"]
    desc_tipo = eval_tipo["descripcion"]

    # Criterio 6: Enganche y Garantías
    ltv = calcular_ltv(enganche, monto_financiado)
    puntos_enganche = evaluar_enganche_garantias(ltv)

    # Puntuación total
    puntuacion_total = (
        puntos_end
        + puntos_cob
        + puntos_hist
        + puntos_est
        + puntos_tipo
        + puntos_enganche
    )

    # Clasificación y decisión
    clasificacion = clasificar_riesgo_total(puntuacion_total)
    decision = determinar_decision_final(puntuacion_total)

    # Condiciones según riesgo
    condiciones = aplicar_condiciones_segun_riesgo(clasificacion, puntuacion_total)

    # Crear registro de evaluación
    evaluacion = PrestamoEvaluacion(
        prestamo_id=datos_evaluacion.get("prestamo_id"),
        ratio_endeudamiento_puntos=puntos_end,
        ratio_endeudamiento_calculo=ratio_end,
        ratio_cobertura_puntos=puntos_cob,
        ratio_cobertura_calculo=ratio_cob,
        historial_crediticio_puntos=puntos_hist,
        historial_crediticio_descripcion=desc_hist,
        estabilidad_laboral_puntos=puntos_est,
        anos_empleo=anos_trabajo,
        tipo_empleo_puntos=puntos_tipo,
        tipo_empleo_descripcion=desc_tipo,
        enganche_garantias_puntos=puntos_enganche,
        enganche_garantias_calculo=ltv,
        puntuacion_total=puntuacion_total,
        clasificacion_riesgo=clasificacion,
        decision_final=decision,
        tasa_interes_aplicada=condiciones["tasa_interes_aplicada"],
        plazo_maximo=condiciones["plazo_maximo"],
        enganche_minimo=condiciones["enganche_minimo"],
        requisitos_adicionales=condiciones["requisitos_adicionales"],
    )

    return evaluacion


def crear_evaluacion_prestamo(
    datos_evaluacion: Dict,
    db: Session,
) -> PrestamoEvaluacion:
    """
    Crea o actualiza la evaluación de un préstamo en la base de datos.

    Args:
        datos_evaluacion: Dict con datos financieros
        db: Sesión de base de datos

    Returns:
        PrestamoEvaluacion creado/actualizado
    """
    prestamo_id = datos_evaluacion.get("prestamo_id")

    # Buscar evaluación existente
    evaluacion_existente = (
        db.query(PrestamoEvaluacion)
        .filter(PrestamoEvaluacion.prestamo_id == prestamo_id)
        .first()
    )

    # Calcular evaluación
    nueva_evaluacion = calcular_evaluacion_completa(datos_evaluacion)

    if evaluacion_existente:
        # Actualizar evaluación existente
        for key, value in nueva_evaluacion.__dict__.items():
            if not key.startswith("_"):
                setattr(evaluacion_existente, key, value)
        evaluacion = evaluacion_existente
    else:
        # Crear nueva evaluación
        evaluacion = nueva_evaluacion
        db.add(evaluacion)

    try:
        db.commit()
        db.refresh(evaluacion)
        logger.info(f"Evaluación guardada para préstamo {prestamo_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error guardando evaluación: {str(e)}")
        raise

    return evaluacion
