from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, field_validator


# ============================================
# SCHEMAS BASE
# ============================================
class PrestamoBase(BaseModel):
    cedula: str = Field(..., max_length=20, description="Cédula del cliente")
    valor_activo: Optional[Decimal] = Field(None, gt=0, description="Valor del activo (vehículo)")
    total_financiamiento: Decimal = Field(..., gt=0, description="Monto total del préstamo")
    modalidad_pago: str = Field(..., max_length=20, description="MENSUAL, QUINCENAL, SEMANAL")

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
    numero_cuotas: Optional[int] = None  # Si se envía, se usa; si no, se calcula automáticamente
    cuota_periodo: Optional[Decimal] = None  # Si se envía, se usa; si no, se calcula automáticamente
    concesionario: str = Field(..., max_length=100)
    analista: str = Field(..., max_length=100)
    modelo_vehiculo: str = Field(..., max_length=100)
    usuario_autoriza: Optional[str] = Field(None, max_length=100)
    observaciones: Optional[str] = None

    @field_validator(
        "cedula",
        "producto",
        "producto_financiero",
        "concesionario",
        "analista",
        "modelo_vehiculo",
    )
    @classmethod
    def non_empty_strings(cls, v: str) -> str:
        if isinstance(v, str) and v.strip() == "":
            raise ValueError("Campo requerido")
        return v


class PrestamoUpdate(BaseModel):
    """Schema para actualizar un préstamo"""

    valor_activo: Optional[Decimal] = None
    total_financiamiento: Optional[Decimal] = None
    modalidad_pago: Optional[str] = None
    fecha_requerimiento: Optional[date] = None
    numero_cuotas: Optional[int] = None
    cuota_periodo: Optional[Decimal] = None
    tasa_interes: Optional[Decimal] = None
    fecha_base_calculo: Optional[date] = None
    estado: Optional[str] = None
    observaciones: Optional[str] = None
    concesionario: Optional[str] = Field(None, max_length=100)
    analista: Optional[str] = Field(None, max_length=100)
    modelo_vehiculo: Optional[str] = Field(None, max_length=100)
    usuario_proponente: Optional[str] = Field(None, max_length=100, description="Email del analista asignado")


# ============================================
# SCHEMAS DE RESPUESTA
# ============================================
class PrestamoResponse(PrestamoBase):
    """Schema para respuesta de préstamo"""

    id: int
    cliente_id: int
    nombres: str
    cedula: str
    valor_activo: Optional[Decimal] = None
    total_financiamiento: Decimal
    fecha_requerimiento: date
    modalidad_pago: str
    numero_cuotas: int
    cuota_periodo: Decimal
    tasa_interes: Decimal
    fecha_base_calculo: Optional[date] = None
    producto: str
    producto_financiero: str
    concesionario: Optional[str] = None
    analista: Optional[str] = None
    modelo_vehiculo: Optional[str] = None
    estado: str
    usuario_proponente: str
    usuario_aprobador: Optional[str] = None
    usuario_autoriza: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_registro: datetime
    fecha_aprobacion: Optional[datetime] = None
    fecha_actualizacion: datetime

    @field_serializer("fecha_registro")
    def serialize_fecha_registro(self, value: datetime) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @field_serializer("fecha_aprobacion")
    def serialize_fecha_aprobacion(self, value: Optional[datetime]) -> Optional[str]:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return None if value is None else str(value)

    @field_serializer("fecha_actualizacion")
    def serialize_fecha_actualizacion(self, value: Optional[datetime]) -> Optional[str]:
        if isinstance(value, datetime):
            return value.isoformat()
        return None if value is None else str(value)

    @field_serializer("fecha_requerimiento")
    def serialize_fecha_requerimiento(self, value: Optional[date]) -> Optional[str]:
        if isinstance(value, date):
            return value.isoformat()
        return None if value is None else str(value)

    @field_serializer("fecha_base_calculo")
    def serialize_fecha_base_calculo(self, value: Optional[date]) -> Optional[str]:
        if value and isinstance(value, date):
            return value.isoformat()
        return value

    @field_serializer("valor_activo")
    def serialize_valor_activo(self, value: Optional[Decimal]) -> Optional[float]:
        return float(value) if value is not None else None

    @field_serializer("total_financiamiento")
    def serialize_total_financiamiento(self, value: Decimal) -> float:
        return float(value)

    @field_serializer("cuota_periodo")
    def serialize_cuota_periodo(self, value: Decimal) -> float:
        return float(value)

    @field_serializer("tasa_interes")
    def serialize_tasa_interes(self, value: Decimal) -> float:
        return float(value)

    class Config:
        from_attributes = True


# ============================================
# SCHEMA DE EVALUACIÓN
# ============================================
class PrestamoEvaluacionBase(BaseModel):
    """Schema base para evaluación de préstamo"""

    pass


class PrestamoEvaluacionCreate(PrestamoEvaluacionBase):
    """Schema para crear evaluación con 7 criterios (100 puntos)"""

    prestamo_id: int

    # ============================================
    # CRITERIO 1: CAPACIDAD DE PAGO (33 puntos)
    # ============================================
    # Criterio 1.A: Ratio de Endeudamiento (17%)
    ratio_endeudamiento_puntos: Decimal = Field(default=0, ge=0, le=17)
    ratio_endeudamiento_calculo: Decimal = Field(default=0)

    # Criterio 1.B: Ratio de Cobertura (16%)
    ratio_cobertura_puntos: Decimal = Field(default=0, ge=0, le=16)
    ratio_cobertura_calculo: Decimal = Field(default=0)

    # ============================================
    # CRITERIO 2: ESTABILIDAD LABORAL (23 puntos)
    # ============================================
    antiguedad_trabajo_puntos: Decimal = Field(default=0, ge=0, le=9)
    meses_trabajo: Optional[Decimal] = None

    tipo_empleo_puntos: Decimal = Field(default=0, ge=0, le=8)
    tipo_empleo_descripcion: Optional[str] = None

    sector_economico_puntos: Decimal = Field(default=0, ge=0, le=6)
    sector_economico_descripcion: Optional[str] = None

    # ============================================
    # CRITERIO 3: REFERENCIAS PERSONALES (5 puntos)
    # ============================================
    referencias_puntos: Decimal = Field(default=0, ge=0, le=5)
    referencias_descripcion: Optional[str] = None
    num_referencias_verificadas: Optional[int] = None

    # ============================================
    # CRITERIO 4: ARRAIGO GEOGRÁFICO (12 puntos)
    # ============================================
    arraigo_vivienda_puntos: Decimal = Field(default=0, ge=0, le=5)
    arraigo_familiar_puntos: Decimal = Field(default=0, ge=0, le=4)
    arraigo_laboral_puntos: Decimal = Field(default=0, ge=0, le=3)

    # ============================================
    # CRITERIO 5: PERFIL SOCIODEMOGRÁFICO (17 puntos)
    # ============================================
    vivienda_puntos: Decimal = Field(default=0, ge=0, le=6)
    vivienda_descripcion: Optional[str] = None

    estado_civil_puntos: Decimal = Field(default=0, ge=0, le=6)
    estado_civil_descripcion: Optional[str] = None

    hijos_puntos: Decimal = Field(default=0, ge=0, le=5)
    hijos_descripcion: Optional[str] = None

    # ============================================
    # CRITERIO 6: EDAD DEL CLIENTE (5 puntos)
    # ============================================
    edad_puntos: Decimal = Field(default=0, ge=0, le=5)
    edad_cliente: Optional[int] = None

    # ============================================
    # CRITERIO 7: ENGANCHE PAGADO (5 puntos)
    # ============================================
    enganche_garantias_puntos: Decimal = Field(default=0, ge=0, le=5)
    enganche_garantias_calculo: Decimal = Field(default=0)

    # ============================================
    # CLASIFICACIÓN Y DECISIÓN
    # ============================================
    puntuacion_total: Decimal = Field(default=0, ge=0, le=100)
    clasificacion_riesgo: str = Field(default="PENDIENTE")
    decision_final: str = Field(default="PENDIENTE")

    # ============================================
    # CONDICIONES SEGÚN RIESGO
    # ============================================
    tasa_interes_aplicada: Optional[Decimal] = None
    plazo_maximo: Optional[int] = None
    enganche_minimo: Optional[Decimal] = None
    requisitos_adicionales: Optional[str] = None

    # Campos de compatibilidad con sistema anterior
    historial_crediticio_puntos: Decimal = Field(default=0, ge=0, le=20)
    historial_crediticio_descripcion: Optional[str] = None
    estabilidad_laboral_puntos: Decimal = Field(default=0, ge=0, le=15)
    anos_empleo: Optional[Decimal] = None


class PrestamoEvaluacionResponse(PrestamoEvaluacionBase):
    """Schema para respuesta de evaluación con 7 criterios"""

    id: int
    prestamo_id: int

    # Criterio 1: Capacidad de Pago
    ratio_endeudamiento_puntos: Decimal
    ratio_endeudamiento_calculo: Decimal
    ratio_cobertura_puntos: Decimal
    ratio_cobertura_calculo: Decimal

    # Criterio 2: Estabilidad Laboral
    antiguedad_trabajo_puntos: Decimal
    meses_trabajo: Optional[Decimal]
    tipo_empleo_puntos: Decimal
    tipo_empleo_descripcion: Optional[str]
    sector_economico_puntos: Decimal
    sector_economico_descripcion: Optional[str]

    # Criterio 3: Referencias
    referencias_puntos: Decimal
    referencias_descripcion: Optional[str]
    num_referencias_verificadas: Optional[int]

    # Criterio 4: Arraigo Geográfico
    arraigo_vivienda_puntos: Decimal
    arraigo_familiar_puntos: Decimal
    arraigo_laboral_puntos: Decimal

    # Criterio 5: Perfil Sociodemográfico
    vivienda_puntos: Decimal
    vivienda_descripcion: Optional[str]
    estado_civil_puntos: Decimal
    estado_civil_descripcion: Optional[str]
    hijos_puntos: Decimal
    hijos_descripcion: Optional[str]

    # Criterio 6: Edad
    edad_puntos: Decimal
    edad_cliente: Optional[int]

    # Criterio 7: Enganche
    enganche_garantias_puntos: Decimal
    enganche_garantias_calculo: Decimal

    # Clasificación
    puntuacion_total: Decimal
    clasificacion_riesgo: str
    decision_final: str

    # Condiciones
    tasa_interes_aplicada: Optional[Decimal]
    plazo_maximo: Optional[int]
    enganche_minimo: Optional[Decimal]
    requisitos_adicionales: Optional[str]

    # Campos de compatibilidad
    historial_crediticio_puntos: Decimal
    historial_crediticio_descripcion: Optional[str]
    estabilidad_laboral_puntos: Decimal
    anos_empleo: Optional[Decimal]

    # Pydantic v2 serializa automáticamente Decimal a float en JSON
    # No necesitamos serializers explícitos

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
