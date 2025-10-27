from sqlalchemy import Column, Integer, Numeric, String

from app.db.session import Base


class PrestamoEvaluacion(Base):
    """
    Sistema de Scoring Crediticio - 100 Puntos Totales
    Evaluación completa del cliente para préstamos de motos en Venezuela
    """

    __tablename__ = "prestamos_evaluacion"

    id = Column(Integer, primary_key=True, index=True)
    prestamo_id = Column(Integer, nullable=False, index=True)

    # ============================================
    # CRITERIO 1: CAPACIDAD DE PAGO (33 puntos)
    # ============================================
    # 1.A - Ratio de Endeudamiento (17 puntos)
    ratio_endeudamiento_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    ratio_endeudamiento_calculo = Column(Numeric(10, 4), nullable=False, default=0)

    # 1.B - Ratio de Cobertura (16 puntos)
    ratio_cobertura_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    ratio_cobertura_calculo = Column(Numeric(10, 4), nullable=False, default=0)

    # ============================================
    # CRITERIO 2: ESTABILIDAD LABORAL (23 puntos)
    # ============================================
    # 2.A - Antigüedad en Trabajo (9 puntos)
    antiguedad_trabajo_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    meses_trabajo = Column(Numeric(6, 2), nullable=True)

    # 2.B - Tipo y Calidad de Empleo (8 puntos)
    tipo_empleo_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    tipo_empleo_descripcion = Column(String(50), nullable=True)

    # 2.C - Sector Económico (6 puntos)
    sector_economico_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    sector_economico_descripcion = Column(String(50), nullable=True)

    # ============================================
    # CRITERIO 3: REFERENCIAS PERSONALES (9 puntos)
    # ============================================
    # 3 referencias individuales
    referencia1_calificacion = Column(Integer, nullable=True, default=0)  # 0-3
    referencia1_observaciones = Column(String(200), nullable=True)
    referencia2_calificacion = Column(Integer, nullable=True, default=0)  # 0-3
    referencia2_observaciones = Column(String(200), nullable=True)
    referencia3_calificacion = Column(Integer, nullable=True, default=0)  # 0-3
    referencia3_observaciones = Column(String(200), nullable=True)

    # Total de puntos (suma de las 3 referencias)
    referencias_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    referencias_descripcion = Column(String(50), nullable=True)

    # Mantener para compatibilidad
    num_referencias_verificadas = Column(Integer, nullable=True)

    # ============================================
    # CRITERIO 4: ARRAIGO GEOGRÁFICO (7 puntos)
    # ============================================
    # 4.A - Tiempo en Domicilio (ELIMINADO - 0 puntos)
    # Campo mantenido en BD por compatibilidad, siempre será 0
    arraigo_vivienda_puntos = Column(Numeric(5, 2), nullable=False, default=0)

    # 4.B - Arraigo Familiar (4 puntos)
    arraigo_familiar_puntos = Column(Numeric(5, 2), nullable=False, default=0)

    # 4.C - Arraigo Laboral (3 puntos)
    arraigo_laboral_puntos = Column(Numeric(5, 2), nullable=False, default=0)

    # ============================================
    # CRITERIO 5: PERFIL SOCIODEMOGRÁFICO (17 puntos)
    # ============================================
    # 5.A - Situación de Vivienda (6 puntos)
    vivienda_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    vivienda_descripcion = Column(String(50), nullable=True)

    # 5.B - Estado Civil y Pareja (6 puntos)
    estado_civil_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    estado_civil_descripcion = Column(String(50), nullable=True)

    # 5.C - Número y Edad de Hijos (5 puntos)
    hijos_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    hijos_descripcion = Column(String(50), nullable=True)

    # ============================================
    # CRITERIO 6: EDAD DEL CLIENTE (10 puntos)
    # ============================================
    edad_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    edad_cliente = Column(Integer, nullable=True)

    # ============================================
    # CRITERIO 7: ENGANCHE PAGADO (5 puntos)
    # ============================================
    enganche_garantias_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    enganche_garantias_calculo = Column(Numeric(10, 4), nullable=False, default=0)

    # ============================================
    # PUNTUACIÓN TOTAL Y CLASIFICACIÓN
    # ============================================
    puntuacion_total = Column(Numeric(5, 2), nullable=False, default=0)
    clasificacion_riesgo = Column(String(20), nullable=False, default="PENDIENTE")
    # A, B, C, D, E

    decision_final = Column(String(20), nullable=False, default="PENDIENTE")
    # APROBADO_AUTOMATICO, APROBADO_ESTANDAR, APROBADO_CONDICIONAL,
    # REQUIERE_MITIGACION, RECHAZADO

    # ============================================
    # CONDICIONES SEGÚN RIESGO
    # ============================================
    tasa_interes_aplicada = Column(Numeric(5, 2), nullable=True)
    plazo_maximo = Column(Integer, nullable=True)
    enganche_minimo = Column(Numeric(5, 2), nullable=True)
    requisitos_adicionales = Column(String(500), nullable=True)

    # Datos de historial crediticio (mantener para compatibilidad)
    historial_crediticio_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    historial_crediticio_descripcion = Column(String(50), nullable=True)
    anos_empleo = Column(Numeric(4, 2), nullable=True)

    def __repr__(self):
        return (
            f"<PrestamoEvaluacion(id={self.id}, prestamo_id={self.prestamo_id}, "
            f"puntuacion={self.puntuacion_total}, riesgo='{self.clasificacion_riesgo}', "
            f"decision='{self.decision_final}')>"
        )
