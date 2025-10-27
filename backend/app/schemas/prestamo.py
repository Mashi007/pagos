from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_serializer


# ============================================
# SCHEMAS BASE
# ============================================
class PrestamoBase(BaseModel):
    cedula: str = Field(..., max_length=20, description="Cédula del cliente")
    total_financiamiento: Decimal = Field(
        ..., gt=0, description="Monto total del préstamo"
    )
    modalidad_pago: str = Field(
        ..., max_length=20, description="MENSUAL, QUINCENAL, SEMANAL"
    )

    @field_validator("modalidad_pago")
    @classmethod
    def validate_modalidad(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in ["MENSUAL", "QUINCENAL", "SEMANAL"]:
            raise ValueError("Modalidad debe ser: MENSUAL, QUINCENAL o SEMANAL")
        return v_upper


class PrestamoCreate(PrestamoBase):
    """Schema para crear un préstamo"""

    fecha_requerimiento: date
    producto: str = Field(..., max_length=100)
    producto_financiero: str = Field(..., max_length=100)


class PrestamoUpdate(BaseModel):
    """Schema para actualizar un préstamo"""

    total_financiamiento: Optional[Decimal] = None
    modalidad_pago: Optional[str] = None
    fecha_requerimiento: Optional[date] = None
    numero_cuotas: Optional[int] = None
    cuota_periodo: Optional[Decimal] = None
    tasa_interes: Optional[Decimal] = None
    fecha_base_calculo: Optional[date] = None
    estado: Optional[str] = None
    observaciones: Optional[str] = None


# ============================================
# SCHEMAS DE RESPUESTA
# ============================================
class PrestamoResponse(PrestamoBase):
    """Schema para respuesta de préstamo"""

    id: int
    cliente_id: int
    nombres: str
    cedula: str
    total_financiamiento: Decimal
    fecha_requerimiento: date
    modalidad_pago: str
    numero_cuotas: int
    cuota_periodo: Decimal
    tasa_interes: Decimal
    fecha_base_calculo: Optional[date] = None
    producto: str
    producto_financiero: str
    estado: str
    usuario_proponente: str
    usuario_aprobador: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_registro: datetime
    fecha_aprobacion: Optional[datetime] = None
    fecha_actualizacion: datetime

    @model_serializer
    def serialize_model(self):
        """Serializa las fechas datetime a string"""
        data = {
            **self.__dict__,
            'fecha_registro': self.fecha_registro.isoformat() if isinstance(self.fecha_registro, datetime) else self.fecha_registro,
            'fecha_aprobacion': self.fecha_aprobacion.isoformat() if self.fecha_aprobacion and isinstance(self.fecha_aprobacion, datetime) else self.fecha_aprobacion,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if isinstance(self.fecha_actualizacion, datetime) else self.fecha_actualizacion,
        }
        # Asegurar que la fecha_base_calculo también sea string si es date
        if hasattr(self, 'fecha_base_calculo') and self.fecha_base_calculo:
            if isinstance(self.fecha_base_calculo, date):
                data['fecha_base_calculo'] = self.fecha_base_calculo.isoformat()
        return data

    class Config:
        from_attributes = True


# ============================================
# SCHEMA DE EVALUACIÓN
# ============================================
class PrestamoEvaluacionBase(BaseModel):
    """Schema base para evaluación de préstamo"""

    pass


class PrestamoEvaluacionCreate(PrestamoEvaluacionBase):
    """Schema para crear evaluación"""

    prestamo_id: int
    # Criterio 1: Ratio de Endeudamiento (25%)
    ratio_endeudamiento_puntos: Decimal = Field(default=0, ge=0, le=25)
    ratio_endeudamiento_calculo: Decimal = Field(default=0)

    # Criterio 2: Ratio de Cobertura (20%)
    ratio_cobertura_puntos: Decimal = Field(default=0, ge=0, le=20)
    ratio_cobertura_calculo: Decimal = Field(default=0)

    # Criterio 3: Historial Crediticio (20%)
    historial_crediticio_puntos: Decimal = Field(default=0, ge=0, le=20)
    historial_crediticio_descripcion: Optional[str] = None

    # Criterio 4: Estabilidad Laboral (15%)
    estabilidad_laboral_puntos: Decimal = Field(default=0, ge=0, le=15)
    anos_empleo: Optional[Decimal] = None

    # Criterio 5: Tipo de Empleo (10%)
    tipo_empleo_puntos: Decimal = Field(default=0, ge=0, le=10)
    tipo_empleo_descripcion: Optional[str] = None

    # Criterio 6: Enganche y Garantías (10%)
    enganche_garantias_puntos: Decimal = Field(default=0, ge=0, le=10)
    enganche_garantias_calculo: Decimal = Field(default=0)

    # Puntuación total y clasificación
    puntuacion_total: Decimal = Field(default=0, ge=0, le=100)
    clasificacion_riesgo: str = Field(default="PENDIENTE")
    decision_final: str = Field(default="PENDIENTE")

    # Condiciones
    tasa_interes_aplicada: Optional[Decimal] = None
    plazo_maximo: Optional[int] = None
    enganche_minimo: Optional[Decimal] = None
    requisitos_adicionales: Optional[str] = None


class PrestamoEvaluacionResponse(PrestamoEvaluacionBase):
    """Schema para respuesta de evaluación"""

    id: int
    prestamo_id: int
    ratio_endeudamiento_puntos: Decimal
    ratio_endeudamiento_calculo: Decimal
    ratio_cobertura_puntos: Decimal
    ratio_cobertura_calculo: Decimal
    historial_crediticio_puntos: Decimal
    historial_crediticio_descripcion: Optional[str]
    estabilidad_laboral_puntos: Decimal
    anos_empleo: Optional[Decimal]
    tipo_empleo_puntos: Decimal
    tipo_empleo_descripcion: Optional[str]
    enganche_garantias_puntos: Decimal
    enganche_garantias_calculo: Decimal
    puntuacion_total: Decimal
    clasificacion_riesgo: str
    decision_final: str
    tasa_interes_aplicada: Optional[Decimal]
    plazo_maximo: Optional[int]
    enganche_minimo: Optional[Decimal]
    requisitos_adicionales: Optional[str]

    class Config:
        from_attributes = True


# ============================================
# SCHEMA DE AUDITORÍA
# ============================================
class PrestamoAuditoriaResponse(BaseModel):
    """Schema para respuesta de auditoría"""

    id: int
    prestamo_id: int
    cedula: str
    usuario: str
    campo_modificado: str
    valor_anterior: Optional[str]
    valor_nuevo: str
    accion: str
    estado_anterior: Optional[str]
    estado_nuevo: Optional[str]
    observaciones: Optional[str]
    fecha_cambio: str

    class Config:
        from_attributes = True
