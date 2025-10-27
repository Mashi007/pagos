"""
Servicio para evaluación de riesgo de préstamos - Sistema de 100 Puntos
Implementa los 7 criterios de evaluación según nueva especificación
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Dict, Tuple

from sqlalchemy.orm import Session

from app.models.prestamo_evaluacion import PrestamoEvaluacion

logger = logging.getLogger(__name__)

# ============================================
# TABLA 1: CRITERIOS Y PESOS DE EVALUACIÓN (100 Puntos Totales)
# ACTUALIZADO: Criterio 1 reducido de 33 a 29 pts, Criterio 3 aumentado de 5 a 9 pts
# ============================================
CRITERIOS_PESOS = {
    "capacidad_pago": 29,  # Criterio 1 (14 + 15)
    "estabilidad_laboral": 23,  # Criterio 2 (9 + 8 + 6)
    "referencias": 9,  # Criterio 3 (3 referencias × 3 pts c/u)
    "arraigo_geografico": 7,  # Criterio 4 (4 + 3) - SIN situación de vivienda
    "perfil_sociodemografico": 17,  # Criterio 5 (6 + 6 + 5)
    "edad": 10,  # Criterio 6 (incrementado de 5 a 10)
    "enganche": 5,  # Criterio 7
}

# ============================================
# CRITERIO 1: CAPACIDAD DE PAGO (29 puntos)
# ============================================


def calcular_ratio_endeudamiento(
    ingresos_mensuales: Decimal,
    otras_deudas: Decimal,
) -> Decimal:
    """
           CRITERIO 1.A: RATIO DE ENDEUDAMIENTO (14 puntos - 14%)

    Formula: (Otras Deudas / Ingresos) × 100
    IMPORTANTE: NO incluir la cuota del préstamo propuesto, solo deudas actuales

    Returns:
        - Decimal con el valor del ratio como porcentaje
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
        Puntos de 0 a 14
    """
    if ratio < Decimal("25"):  # Menos de 25%
        return Decimal(14)  # Reducido de 17 a 14
    elif ratio < Decimal("35"):  # 25% - 34.99%
        return Decimal(11)  # Reducido de 13 a 11
    elif ratio < Decimal("50"):  # 35% - 49.99%
        return Decimal(6)  # Reducido de 7 a 6
    else:  # 50% o más
        return Decimal(2)


def calcular_ratio_cobertura(
    ingresos_mensuales: Decimal,
    gastos_fijos: Decimal,
    otras_deudas: Decimal,
    cuota: Decimal,
) -> Decimal:
    """
           CRITERIO 1.B: RATIO DE COBERTURA (15 puntos - 15%)

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


def evaluar_ratio_cobertura_puntos(ratio: Decimal) -> Tuple[Decimal, bool]:
    """
    CRITERIO 1.B: Evalúa puntos según ratio de cobertura.

    Rangos:
    - > 2.5x     -> Excelente     -> 16 puntos
    - 2.0x-2.5x  -> Bueno         -> 13 puntos
    - 1.5x-2.0x  -> Regular       -> 7 puntos
    - < 1.5x     -> Insuficiente  -> 0 puntos (RECHAZO)

    Returns:
        Tuple: (puntos, rechazo_automatico)
        Puntos de 0 a 15
    """
    if ratio > Decimal("2.5"):  # Más de 2.5x
        return Decimal(15), False  # Reducido de 16 a 15
    elif ratio >= Decimal("2.0"):  # 2.0x - 2.5x
        return Decimal(12), False  # Reducido de 13 a 12
    elif ratio >= Decimal("1.5"):  # 1.5x - 1.99x
        return Decimal(6), False  # Reducido de 7 a 6
    else:  # Menos de 1.5x - RECHAZO
        return Decimal(0), True


# ============================================
# CRITERIO 2: ESTABILIDAD LABORAL (23 puntos)
# ============================================


def evaluar_antiguedad_trabajo(meses_trabajo: int) -> Decimal:
    """
    CRITERIO 2.A: Antigüedad en Trabajo (9 puntos - 9%)

    Rangos:
    - > 24 meses  -> Muy estable -> 9 puntos
    - 12-24 meses -> Estable     -> 7 puntos
    - 6-12 meses  -> Moderado    -> 4 puntos
    - < 6 meses   -> Inestable   -> 0 puntos

    Returns:
        Puntos de 0 a 9
    """
    if meses_trabajo > 24:
        return Decimal(9)
    elif meses_trabajo >= 12:
        return Decimal(7)
    elif meses_trabajo >= 6:
        return Decimal(4)
    else:
        return Decimal(0)


def evaluar_tipo_empleo(tipo_empleo: str) -> Decimal:
    """
    CRITERIO 2.B: Tipo y Calidad de Empleo (8 puntos - 8%)

    Tipos y puntos:
    - empleado_formal        -> 8 puntos
    - informal_estable       -> 6 puntos
    - independiente_formal   -> 5 puntos
    - independiente_informal -> 3 puntos
    - sin_empleo            -> 0 puntos

    Returns:
        Puntos de 0 a 8
    """
    tipo_puntos = {
        "empleado_formal": 8,
        "informal_estable": 6,
        "independiente_formal": 5,
        "independiente_informal": 3,
        "sin_empleo": 0,
    }
    return Decimal(tipo_puntos.get(tipo_empleo.lower(), 0))


def evaluar_sector_economico(sector: str) -> Decimal:
    """
    CRITERIO 2.C: Sector Económico (6 puntos - 6%)

    Sectores y puntos:
    - gobierno_publico           -> 6 puntos
    - servicios_esenciales       -> 5 puntos
    - comercio_establecido       -> 4 puntos
    - construccion_manufactura  -> 3 puntos
    - turismo_entretenimiento    -> 2 puntos
    - servicios_temporales       -> 1 punto
    - agricultura_estacional    -> 0 puntos

    Returns:
        Puntos de 0 a 6
    """
    sector_puntos = {
        "gobierno_publico": 6,
        "servicios_esenciales": 5,
        "comercio_establecido": 4,
        "construccion_manufactura": 3,
        "turismo_entretenimiento": 2,
        "servicios_temporales": 1,
        "agricultura_estacional": 0,
    }
    return Decimal(sector_puntos.get(sector.lower(), 0))


# ============================================
# CRITERIO 3: REFERENCIAS PERSONALES (9 puntos)
# ============================================


def evaluar_referencias_individuales(calificacion: int) -> Decimal:
    """
    CRITERIO 3: Referencias Personales (9 puntos - 3 referencias)

    Calificaciones:
    - 3 = Recomendable -> 3 puntos
    - 2 = Dudosa -> 2 puntos
    - 1 = No recomendable -> 1 punto
    - 0 = No contestó -> 0 puntos

    Returns:
        Puntos de 0 a 3 por referencia
    """
    return Decimal(calificacion)


# ============================================
# CRITERIO 4: ARRAIGO GEOGRÁFICO (12 puntos)
# ============================================


def evaluar_vivienda(tipo_vivienda: str) -> Decimal:
    """
    CRITERIO 4.A: Tiempo en Domicilio (5 puntos - 5%)

    Situación y puntos:
    - casa_propia      -> 5 puntos
    - alquiler_mas_2   -> 4 puntos
    - alquiler_1_2     -> 3 puntos
    - alquiler_menos_1 -> 1 punto
    - prestado         -> 0.5 puntos
    - sin_vivienda     -> 0 puntos

    Returns:
        Puntos de 0 a 5
    """
    vivienda_puntos = {
        "casa_propia": 5,
        "alquiler_mas_2": 4,
        "alquiler_1_2": 3,
        "alquiler_menos_1": 1,
        "prestado": Decimal("0.5"),
        "sin_vivienda": 0,
    }
    return Decimal(vivienda_puntos.get(tipo_vivienda.lower(), 0))


def evaluar_arraigo_familiar(familia_cercana: bool, familia_pais: bool) -> Decimal:
    """
    CRITERIO 4.B: Arraigo Familiar (4 puntos - 4%)

    Situación y puntos:
    - Familia cercana en ciudad -> 4 puntos
    - Familia en el país        -> 2 puntos
    - Sin familia en zona       -> 0 puntos

    Returns:
        Puntos de 0 a 4
    """
    if familia_cercana:
        return Decimal(4)
    elif familia_pais:
        return Decimal(2)
    else:
        return Decimal(0)


def evaluar_arraigo_laboral(minutos_trabajo: int) -> Decimal:
    """
    CRITERIO 4.C: Arraigo Laboral (3 puntos - 3%)

    Distancia y puntos:
    - < 30 min -> 3 puntos
    - 30-60 min -> 2 puntos
    - > 60 min  -> 0 puntos

    Returns:
        Puntos de 0 a 3
    """
    if minutos_trabajo < 30:
        return Decimal(3)
    elif minutos_trabajo <= 60:
        return Decimal(2)
    else:
        return Decimal(0)


# ============================================
# CRITERIO 5: PERFIL SOCIODEMOGRÁFICO (17 puntos)
# ============================================


def evaluar_vivienda_detallada(
    tipo_vivienda: str,
    zona_urbana: bool = False,
    servicios_nombre: bool = False,
    zona_rural: bool = False,
    personas_casa: int = 1,
) -> Decimal:
    """
    CRITERIO 5.A: Situación de Vivienda (6 puntos - 6%)

    Base + modificadores (MAX: 6 puntos)
    """
    vivienda_puntos = {
        "casa_propia_pagada": 6,
        "casa_propia_hipoteca": 5,
        "casa_familiar": 5,
        "alquiler_mas_3": 4,
        "alquiler_1_3": 3,
        "alquiler_menos_1": 1,
        "prestado": Decimal("0.5"),
        "sin_vivienda": 0,
    }

    puntos_base = Decimal(vivienda_puntos.get(tipo_vivienda.lower(), 0))
    modificadores = Decimal("0")

    if zona_urbana:
        modificadores += Decimal("0.5")
    if servicios_nombre:
        modificadores += Decimal("0.5")
    if zona_rural:
        modificadores -= Decimal("0.5")
    if personas_casa > 5:
        modificadores -= Decimal("0.5")

    return min(Decimal(6), puntos_base + modificadores)


def evaluar_estado_civil(
    estado_civil: str,
    pareja_trabaja: bool = False,
    pareja_aval: bool = False,
    pareja_desempleada: bool = False,
    relacion_conflictiva: bool = False,
) -> Decimal:
    """
    CRITERIO 5.B: Estado Civil y Pareja (6 puntos - 6%)

    Base + modificadores (MAX: 6 puntos)
    """
    estado_puntos = {
        "casado_mas_3": Decimal("3.5"),
        "casado_menos_3": Decimal("3.0"),
        "divorciado_con_hijos": Decimal("2.5"),
        "soltero_con_pareja": Decimal("2.0"),
        "soltero_sin_pareja": Decimal("1.5"),
        "divorciado_sin_hijos": Decimal("1.0"),
        "separado_reciente": Decimal("0"),
    }

    puntos_base = estado_puntos.get(estado_civil.lower(), Decimal("0"))
    modificadores = Decimal("0")

    if pareja_trabaja:
        modificadores += Decimal("1.0")
    if pareja_aval:
        modificadores += Decimal("1.5")
    if pareja_desempleada:
        modificadores -= Decimal("0.5")
    if relacion_conflictiva:
        modificadores -= Decimal("1.0")

    return min(Decimal(6), puntos_base + modificadores)


def evaluar_hijos(
    situacion_hijos: str,
    todos_estudian: bool = False,
    viven_con_cliente: bool = False,
    necesidades_especiales: bool = False,
    viven_con_ex: bool = False,
    embarazo_actual: bool = False,
) -> Decimal:
    """
    CRITERIO 5.C: Número y Edad de Hijos (5 puntos - 5%)

    Base + modificadores (MAX: 5 puntos)
    """
    hijos_puntos = {
        "1_2_menores": Decimal("5.0"),
        "1_2_mayores": Decimal("4.0"),
        "3_4_mixtos": Decimal("3.0"),
        "sin_hijos_planea": Decimal("2.5"),
        "5_mas": Decimal("1.5"),
        "sin_hijos_no_planea": Decimal("2.0"),
        "hijos_independientes": Decimal("1.0"),
    }

    puntos_base = hijos_puntos.get(situacion_hijos.lower(), Decimal("0"))
    modificadores = Decimal("0")

    if todos_estudian:
        modificadores += Decimal("0.5")
    if viven_con_cliente:
        modificadores += Decimal("0.5")
    if necesidades_especiales:
        modificadores -= Decimal("1.0")
    if viven_con_ex:
        modificadores -= Decimal("0.5")
    if embarazo_actual:
        modificadores -= Decimal("0.5")

    return min(Decimal(5), puntos_base + modificadores)


# ============================================
# CRITERIO 6: EDAD DEL CLIENTE (10 puntos)
# ============================================


def evaluar_edad_cliente(edad: int) -> Tuple[Decimal, str, bool]:
    """
    CRITERIO 6: Edad del Cliente (10 puntos - 10%)

    Rangos:
    - 25-50 años -> Óptimo      -> 10.0 puntos
    - 22-24 / 51-55 -> Muy bueno/Bueno -> 8.0 puntos
    - 18-21 / 56-60 -> Regular  -> 6.0 puntos
    - 61-65 -> Bajo -> 3.0 puntos
    - < 18 años -> RECHAZO
    - > 65 años -> Muy bajo -> 2.0 puntos

    Returns:
        Tuple: (puntos, categoria, rechazo)
    """
    if edad >= 25 and edad <= 50:
        return Decimal(10), "Óptimo", False
    elif (edad >= 22 and edad <= 24) or (edad >= 51 and edad <= 55):
        categoria = "Muy bueno" if edad <= 24 else "Bueno"
        return Decimal(8), categoria, False
    elif (edad >= 18 and edad <= 21) or (edad >= 56 and edad <= 60):
        return Decimal(6), "Regular", False
    elif edad >= 61 and edad <= 65:
        return Decimal(3), "Bajo", False
    elif edad < 18:
        return Decimal(0), "Menor de edad - RECHAZO", True
    else:  # edad > 65
        return Decimal(2), "Muy bajo", False


# ============================================
# CRITERIO 7: ENGANCHE PAGADO (5 puntos)
# ============================================


def calcular_enganche_porcentaje(enganche: Decimal, valor_moto: Decimal) -> Decimal:
    """
    CRITERIO 7: Enganche Pagado (5 puntos - 5%)

    Formula: % Enganche = (Enganche / Valor Moto) × 100
    """
    if valor_moto <= 0:
        return Decimal("0")

    return (enganche / valor_moto) * Decimal(100)


def evaluar_enganche_puntos(porcentaje_enganche: Decimal) -> Decimal:
    """
    CRITERIO 7: Enganche Pagado (5 puntos - 5%)

    Rangos:
    - ≥30%   -> 5.0 puntos
    - 25-29.9% -> 4.5 puntos
    - 20-24.9% -> 4.0 puntos
    - 15-19.9% -> 3.0 puntos
    - 10-14.9% -> 2.0 puntos
    - 5-9.9% -> 1.0 punto
    - <5%    -> 0.5 puntos
    - 0%     -> 0 puntos
    """
    if porcentaje_enganche >= 30:
        return Decimal("5.0")
    elif porcentaje_enganche >= 25:
        return Decimal("4.5")
    elif porcentaje_enganche >= 20:
        return Decimal("4.0")
    elif porcentaje_enganche >= 15:
        return Decimal("3.0")
    elif porcentaje_enganche >= 10:
        return Decimal("2.0")
    elif porcentaje_enganche >= 5:
        return Decimal("1.0")
    elif porcentaje_enganche > 0:
        return Decimal("0.5")
    else:
        return Decimal("0")


# ============================================
# CLASIFICACIÓN Y DECISIÓN
# ============================================


def clasificar_riesgo_total(puntuacion_total: Decimal) -> str:
    """
    CLASIFICACIÓN FINAL DE RIESGO

    Returns:
        "A", "B", "C", "D", "E"
    """
    if puntuacion_total >= 85:
        return "A"  # Muy Bajo
    elif puntuacion_total >= 70:
        return "B"  # Bajo
    elif puntuacion_total >= 55:
        return "C"  # Medio
    elif puntuacion_total >= 40:
        return "D"  # Alto
    else:
        return "E"  # Crítico


def determinar_decision_final(puntuacion_total: Decimal) -> str:
    """
    DETERMINA LA DECISIÓN FINAL DEL PRÉSTAMO

    Returns:
        "APROBADO_AUTOMATICO", "APROBADO_ESTANDAR", "APROBADO_CONDICIONAL",
        "REQUIERE_MITIGACION", "RECHAZADO"
    """
    if puntuacion_total >= 85:
        return "APROBADO_AUTOMATICO"
    elif puntuacion_total >= 70:
        return "APROBADO_ESTANDAR"
    elif puntuacion_total >= 55:
        return "APROBADO_CONDICIONAL"
    elif puntuacion_total >= 40:
        return "REQUIERE_MITIGACION"
    else:
        return "RECHAZADO"


def aplicar_condiciones_segun_riesgo(
    clasificacion_riesgo: str,
    puntuacion_total: Decimal,
) -> Dict[str, any]:
    """
    CONDICIONES SEGÚN NIVEL DE RIESGO
    """
    condiciones = {
        "A": {
            "tasa_interes_aplicada": Decimal("15.0"),
            "plazo_maximo": 36,
            "enganche_minimo": Decimal("10.0"),
            "requisitos_adicionales": "GPS opcional",
        },
        "B": {
            "tasa_interes_aplicada": Decimal("20.0"),
            "plazo_maximo": 30,
            "enganche_minimo": Decimal("15.0"),
            "requisitos_adicionales": "GPS recomendado",
        },
        "C": {
            "tasa_interes_aplicada": Decimal("24.0"),
            "plazo_maximo": 24,
            "enganche_minimo": Decimal("20.0"),
            "requisitos_adicionales": "GPS + Aval obligatorio",
        },
        "D": {
            "tasa_interes_aplicada": Decimal("28.0"),
            "plazo_maximo": 18,
            "enganche_minimo": Decimal("25.0"),
            "requisitos_adicionales": "GPS + Aval + Visitas",
        },
        "E": {
            "tasa_interes_aplicada": Decimal("30.0"),
            "plazo_maximo": 12,
            "enganche_minimo": Decimal("30.0"),
            "requisitos_adicionales": "No aprobar",
        },
    }

    return condiciones.get(clasificacion_riesgo, condiciones["E"])


# ============================================
# FUNCIÓN PRINCIPAL DE EVALUACIÓN
# ============================================


def calcular_evaluacion_completa(datos_evaluacion: Dict) -> PrestamoEvaluacion:
    """
    Calcula la evaluación completa de un préstamo usando los 7 criterios (100 puntos).

    Args:
        datos_evaluacion: Dict con datos financieros del cliente

    Returns:
        PrestamoEvaluacion con la evaluación completa
    """
    # Extraer datos financieros
    ingresos = Decimal(str(datos_evaluacion.get("ingresos_mensuales", 0)))
    gastos_fijos = Decimal(str(datos_evaluacion.get("gastos_fijos_mensuales", 0)))
    otras_deudas = Decimal(str(datos_evaluacion.get("otras_deudas", 0)))
    cuota = Decimal(str(datos_evaluacion.get("cuota_mensual", 0)))

    # Criterio 1.A: Ratio de Endeudamiento (14 puntos)
    ratio_end = calcular_ratio_endeudamiento(ingresos, otras_deudas)
    puntos_1a = evaluar_ratio_endeudamiento_puntos(ratio_end)

    # Criterio 1.B: Ratio de Cobertura (15 puntos)
    ratio_cob = calcular_ratio_cobertura(ingresos, gastos_fijos, otras_deudas, cuota)
    puntos_1b, rechazo_automatico = evaluar_ratio_cobertura_puntos(ratio_cob)

    # Rechazo automático por ratio de cobertura < 1.5x
    if rechazo_automatico:
        logger.warning("RECHAZO AUTOMÁTICO: Ratio de cobertura < 1.5x")
        evaluacion = PrestamoEvaluacion(
            prestamo_id=datos_evaluacion.get("prestamo_id"),
            ratio_endeudamiento_puntos=puntos_1a,
            ratio_endeudamiento_calculo=ratio_end,
            ratio_cobertura_puntos=Decimal(0),
            ratio_cobertura_calculo=ratio_cob,
            antiguedad_trabajo_puntos=Decimal(0),
            tipo_empleo_puntos=Decimal(0),
            sector_economico_puntos=Decimal(0),
            referencia1_calificacion=0,
            referencia1_observaciones="",
            referencia2_calificacion=0,
            referencia2_observaciones="",
            referencia3_calificacion=0,
            referencia3_observaciones="",
            referencias_puntos=Decimal(0),
            arraigo_vivienda_puntos=Decimal(0),
            arraigo_familiar_puntos=Decimal(0),
            arraigo_laboral_puntos=Decimal(0),
            vivienda_puntos=Decimal(0),
            estado_civil_puntos=Decimal(0),
            hijos_puntos=Decimal(0),
            edad_puntos=Decimal(0),
            enganche_garantias_puntos=Decimal(0),
            enganche_garantias_calculo=Decimal(0),
            puntuacion_total=puntos_1a,
            clasificacion_riesgo="E",
            decision_final="RECHAZADO",
            requisitos_adicionales="RECHAZO: Ratio de cobertura insuficiente (< 1.5x)",
            # Campos de compatibilidad
            historial_crediticio_puntos=Decimal(0),
            historial_crediticio_descripcion="RECHAZADO",
        )
        return evaluacion

    # Criterio 2: Estabilidad Laboral (23 puntos)
    meses_trabajo = int(datos_evaluacion.get("meses_trabajo", 0))
    puntos_2a = evaluar_antiguedad_trabajo(meses_trabajo)

    tipo_empleo = datos_evaluacion.get("tipo_empleo", "sin_empleo")
    puntos_2b = evaluar_tipo_empleo(tipo_empleo)

    sector = datos_evaluacion.get("sector_economico", "agricultura_estacional")
    puntos_2c = evaluar_sector_economico(sector)

    # Criterio 3: Referencias (9 puntos - 3 referencias individuales)
    referencia1_cal = int(datos_evaluacion.get("referencia1_calificacion", 0))
    referencia2_cal = int(datos_evaluacion.get("referencia2_calificacion", 0))
    referencia3_cal = int(datos_evaluacion.get("referencia3_calificacion", 0))
    puntos_3 = (
        Decimal(referencia1_cal) + Decimal(referencia2_cal) + Decimal(referencia3_cal)
    )
    desc_referencias = (
        f"Ref1:{referencia1_cal} Ref2:{referencia2_cal} Ref3:{referencia3_cal}"
    )

    # Criterio 4: Arraigo Geográfico (7 puntos - SIN situación de vivienda)
    # puntos_4a ELIMINADO - solo familia y trabajo

    familia_cercana = datos_evaluacion.get("familia_cercana", False)
    familia_pais = datos_evaluacion.get("familia_pais", False)
    puntos_4b = evaluar_arraigo_familiar(familia_cercana, familia_pais)

    minutos_trabajo = datos_evaluacion.get("minutos_trabajo", 999)
    puntos_4c = evaluar_arraigo_laboral(minutos_trabajo)
    
    puntos_4a = Decimal(0)  # Mantener para compatibilidad, siempre 0

    # Criterio 5: Perfil Sociodemográfico (17 puntos)
    tipo_vivienda_det = datos_evaluacion.get("tipo_vivienda_detallado", "sin_vivienda")
    puntos_5a = evaluar_vivienda_detallada(
        tipo_vivienda_det,
        datos_evaluacion.get("zona_urbana", False),
        datos_evaluacion.get("servicios_nombre", False),
        datos_evaluacion.get("zona_rural", False),
        datos_evaluacion.get("personas_casa", 1),
    )

    estado_civil = datos_evaluacion.get("estado_civil", "soltero_sin_pareja")
    puntos_5b = evaluar_estado_civil(
        estado_civil,
        datos_evaluacion.get("pareja_trabaja", False),
        datos_evaluacion.get("pareja_aval", False),
        datos_evaluacion.get("pareja_desempleada", False),
        datos_evaluacion.get("relacion_conflictiva", False),
    )

    situacion_hijos = datos_evaluacion.get("situacion_hijos", "sin_hijos_no_planea")
    puntos_5c = evaluar_hijos(
        situacion_hijos,
        datos_evaluacion.get("todos_estudian", False),
        datos_evaluacion.get("viven_con_cliente", False),
        datos_evaluacion.get("necesidades_especiales", False),
        datos_evaluacion.get("viven_con_ex", False),
        datos_evaluacion.get("embarazo_actual", False),
    )

    # Criterio 6: Edad (10 puntos)
    edad_cliente = int(datos_evaluacion.get("edad", 25))
    puntos_6, categoria_edad, rechazo_edad = evaluar_edad_cliente(edad_cliente)

    if rechazo_edad:
        logger.warning("RECHAZO AUTOMÁTICO: Cliente menor de 18 años")
        evaluacion = PrestamoEvaluacion(
            prestamo_id=datos_evaluacion.get("prestamo_id"),
            ratio_endeudamiento_puntos=puntos_1a,
            ratio_endeudamiento_calculo=ratio_end,
            ratio_cobertura_puntos=puntos_1b,
            ratio_cobertura_calculo=ratio_cob,
            antiguedad_trabajo_puntos=puntos_2a,
            tipo_empleo_puntos=puntos_2b,
            sector_economico_puntos=puntos_2c,
            referencia1_calificacion=referencia1_cal,
            referencia1_observaciones=datos_evaluacion.get(
                "referencia1_observaciones", ""
            ),
            referencia2_calificacion=referencia2_cal,
            referencia2_observaciones=datos_evaluacion.get(
                "referencia2_observaciones", ""
            ),
            referencia3_calificacion=referencia3_cal,
            referencia3_observaciones=datos_evaluacion.get(
                "referencia3_observaciones", ""
            ),
            referencias_puntos=puntos_3,
            arraigo_vivienda_puntos=puntos_4a,
            arraigo_familiar_puntos=puntos_4b,
            arraigo_laboral_puntos=puntos_4c,
            vivienda_puntos=puntos_5a,
            estado_civil_puntos=puntos_5b,
            hijos_puntos=puntos_5c,
            edad_puntos=Decimal(0),
            edad_cliente=edad_cliente,
            enganche_garantias_puntos=Decimal(0),
            enganche_garantias_calculo=Decimal(0),
            puntuacion_total=puntos_1a
            + puntos_1b
            + puntos_2a
            + puntos_2b
            + puntos_2c
            + puntos_3
            + puntos_4a
            + puntos_4b
            + puntos_4c
            + puntos_5a
            + puntos_5b
            + puntos_5c,
            clasificacion_riesgo="E",
            decision_final="RECHAZADO",
            requisitos_adicionales="RECHAZO: Cliente menor de 18 años",
            historial_crediticio_puntos=Decimal(0),
            historial_crediticio_descripcion="RECHAZADO",
        )
        return evaluacion

    # Criterio 7: Enganche (5 puntos)
    enganche = Decimal(str(datos_evaluacion.get("enganche_pagado", 0)))
    valor_moto = Decimal(str(datos_evaluacion.get("valor_garantia", 0)))
    porcentaje_enganche = calcular_enganche_porcentaje(enganche, valor_moto)
    puntos_7 = evaluar_enganche_puntos(porcentaje_enganche)

    # Puntuación total
    puntuacion_total = (
        puntos_1a
        + puntos_1b  # Criterio 1 (29 puntos)
        + puntos_2a
        + puntos_2b
        + puntos_2c  # Criterio 2 (23 puntos)
        + puntos_3  # Criterio 3 (9 puntos)
        + puntos_4a  # Siempre 0 (eliminado situación vivienda)
        + puntos_4b
        + puntos_4c  # Criterio 4 (7 puntos - solo arraigo familiar y laboral)
        + puntos_5a
        + puntos_5b
        + puntos_5c  # Criterio 5 (17 puntos)
        + puntos_6  # Criterio 6 (10 puntos)
        + puntos_7  # Criterio 7 (5 puntos)
    )

    # Clasificación y decisión
    clasificacion = clasificar_riesgo_total(puntuacion_total)
    decision = determinar_decision_final(puntuacion_total)

    # Condiciones según riesgo
    condiciones = aplicar_condiciones_segun_riesgo(clasificacion, puntuacion_total)

    # Crear evaluación
    evaluacion = PrestamoEvaluacion(
        prestamo_id=datos_evaluacion.get("prestamo_id"),
        # Criterio 1
        ratio_endeudamiento_puntos=puntos_1a,
        ratio_endeudamiento_calculo=ratio_end,
        ratio_cobertura_puntos=puntos_1b,
        ratio_cobertura_calculo=ratio_cob,
        # Criterio 2
        antiguedad_trabajo_puntos=puntos_2a,
        meses_trabajo=Decimal(meses_trabajo),
        tipo_empleo_puntos=puntos_2b,
        tipo_empleo_descripcion=tipo_empleo,
        sector_economico_puntos=puntos_2c,
        sector_economico_descripcion=sector,
        # Criterio 3 - Referencias individuales
        referencia1_calificacion=referencia1_cal,
        referencia1_observaciones=datos_evaluacion.get("referencia1_observaciones", ""),
        referencia2_calificacion=referencia2_cal,
        referencia2_observaciones=datos_evaluacion.get("referencia2_observaciones", ""),
        referencia3_calificacion=referencia3_cal,
        referencia3_observaciones=datos_evaluacion.get("referencia3_observaciones", ""),
        referencias_puntos=puntos_3,
        referencias_descripcion=desc_referencias,
        num_referencias_verificadas=0,  # Compatibilidad
        # Criterio 4
        arraigo_vivienda_puntos=puntos_4a,
        arraigo_familiar_puntos=puntos_4b,
        arraigo_laboral_puntos=puntos_4c,
        # Criterio 5
        vivienda_puntos=puntos_5a,
        estado_civil_puntos=puntos_5b,
        estado_civil_descripcion=estado_civil,
        hijos_puntos=puntos_5c,
        hijos_descripcion=situacion_hijos,
        # Criterio 6
        edad_puntos=puntos_6,
        edad_cliente=edad_cliente,
        # Criterio 7
        enganche_garantias_puntos=puntos_7,
        enganche_garantias_calculo=porcentaje_enganche,
        # Totales y clasificación
        puntuacion_total=puntuacion_total,
        clasificacion_riesgo=clasificacion,
        decision_final=decision,
        tasa_interes_aplicada=condiciones["tasa_interes_aplicada"],
        plazo_maximo=condiciones["plazo_maximo"],
        enganche_minimo=condiciones["enganche_minimo"],
        requisitos_adicionales=condiciones["requisitos_adicionales"],
        # Compatibilidad
        historial_crediticio_puntos=Decimal(0),
        historial_crediticio_descripcion="No aplica",
    )

    return evaluacion


def crear_evaluacion_prestamo(
    datos_evaluacion: Dict,
    db: Session,
) -> PrestamoEvaluacion:
    """
    Crea o actualiza la evaluación de un préstamo en la base de datos.
    """
    evaluacion = calcular_evaluacion_completa(datos_evaluacion)

    # Buscar evaluación existente
    eval_existente = (
        db.query(PrestamoEvaluacion)
        .filter(PrestamoEvaluacion.prestamo_id == evaluacion.prestamo_id)
        .first()
    )

    if eval_existente:
        # Actualizar
        for key, value in evaluacion.__dict__.items():
            if not key.startswith("_"):
                setattr(eval_existente, key, value)
        db.commit()
        db.refresh(eval_existente)
        return eval_existente
    else:
        # Crear nuevo
        db.add(evaluacion)
        db.commit()
        db.refresh(evaluacion)
    return evaluacion
