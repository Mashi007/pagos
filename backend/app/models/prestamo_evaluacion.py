from sqlalchemy import Column, Integer, Numeric, String

from app.db.session import Base


class PrestamoEvaluacion(Base):
    """
    Tabla 1 compartida: Criterios y Pesos de Evaluación.
    Cada préstamo tiene una evaluación basada en 6 criterios.
    """

    __tablename__ = "prestamos_evaluacion"

    id = Column(Integer, primary_key=True, index=True)

    # Referencia al préstamo
    prestamo_id = Column(Integer, nullable=False, index=True)

    # ============================================
    # CRITERIO 1: RATIO DE ENDEUDAMIENTO (25%)
    # ============================================
    ratio_endeudamiento_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    ratio_endeudamiento_calculo = Column(Numeric(10, 4), nullable=False, default=0)

    # ============================================
    # CRITERIO 2: RATIO DE COBERTURA (20%)
    # ============================================
    ratio_cobertura_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    ratio_cobertura_calculo = Column(Numeric(10, 4), nullable=False, default=0)

    # ============================================
    # CRITERIO 3: HISTORIAL CREDITICIO (20%)
    # ============================================
    historial_crediticio_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    historial_crediticio_descripcion = Column(
        String(50), nullable=True
    )  # Excelente, Bueno, Regular, Malo

    # ============================================
    # CRITERIO 4: ESTABILIDAD LABORAL (15%)
    # ============================================
    estabilidad_laboral_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    anos_empleo = Column(Numeric(4, 2), nullable=True)  # Años en el trabajo actual

    # ============================================
    # CRITERIO 5: TIPO DE EMPLEO (10%)
    # ============================================
    tipo_empleo_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    tipo_empleo_descripcion = Column(
        String(50), nullable=True
    )  # Formal, Independiente, Contratado

    # ============================================
    # CRITERIO 6: ENGANCHE Y GARANTÍAS (10%)
    # ============================================
    enganche_garantias_puntos = Column(Numeric(5, 2), nullable=False, default=0)
    enganche_garantias_calculo = Column(
        Numeric(10, 4), nullable=False, default=0
    )  # LTV

    # ============================================
    # PUNTUACIÓN TOTAL Y CLASIFICACIÓN
    # ============================================
    puntuacion_total = Column(
        Numeric(5, 2), nullable=False, default=0
    )  # Suma de los 6 criterios (máx 100)
    clasificacion_riesgo = Column(String(20), nullable=False, default="PENDIENTE")
    # BAJO, MODERADO, ALTO, CRÍTICO

    decision_final = Column(String(20), nullable=False, default="PENDIENTE")
    # APROBADO, CONDICIONAL, REQUIERE_MITIGACION, RECHAZADO

    # ============================================
    # CONDICIONES SEGÚN RIESGO
    # ============================================
    tasa_interes_aplicada = Column(
        Numeric(5, 2), nullable=True
    )  # Tasa según nivel de riesgo
    plazo_maximo = Column(Integer, nullable=True)  # Plazo máximo según riesgo
    enganche_minimo = Column(
        Numeric(5, 2), nullable=True
    )  # Enganche mínimo según riesgo
    requisitos_adicionales = Column(
        String(200), nullable=True
    )  # Requisitos adicionales

    def __repr__(self):
        return (
            f"<PrestamoEvaluacion(id={self.id}, prestamo_id={self.prestamo_id}, "
            f"puntuacion={self.puntuacion_total}, riesgo='{self.clasificacion_riesgo}', "
            f"decision='{self.decision_final}')>"
        )
