from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CuotaBase(BaseModel):
    # Schema base para Cuota
    numero_cuota: int = Field(..., gt=0, description="Número de la cuota")
    fecha_vencimiento: date = Field(..., description="Fecha de vencimiento")
    monto_cuota: Decimal = Field(..., gt=0, description="Monto total de la cuota")
    monto_capital: Decimal = Field(..., ge=0, description="Monto de capital")
    monto_interes: Decimal = Field(..., ge=0, description="Monto de interés")
    saldo_capital_inicial: Decimal = Field(..., ge=0, description="Saldo inicial de capital")
    saldo_capital_final: Decimal = Field(..., ge=0, description="Saldo final de capital")

    @field_validator(
        "monto_cuota",
        "monto_capital",
        "monto_interes",
        "saldo_capital_inicial",
        "saldo_capital_final",
        mode="before",
    )
    @classmethod
    def validate_decimal_places(cls, v):
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class CuotaCreate(CuotaBase):
    # Schema para crear una cuota
    prestamo_id: int


class CuotaUpdate(BaseModel):
    # Schema para actualizar una cuota
    fecha_pago: Optional[date] = None
    capital_pagado: Optional[Decimal] = Field(None, ge=0)
    interes_pagado: Optional[Decimal] = Field(None, ge=0)
    mora_pagada: Optional[Decimal] = Field(None, ge=0)
    estado: Optional[str] = None
    observaciones: Optional[str] = None

    @field_validator("capital_pagado", "interes_pagado", "mora_pagada", mode="before")
    @classmethod
    def validate_decimal_places(cls, v):
        if v is not None and not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if v else v


class CuotaResponse(CuotaBase):
    # Schema para respuesta de cuota - FASE 2: Sincronizado con modelo ORM
    id: int
    prestamo_id: int
    fecha_pago: Optional[date] = None
    capital_pagado: Decimal
    interes_pagado: Decimal
    mora_pagada: Decimal
    total_pagado: Decimal
    capital_pendiente: Decimal
    interes_pendiente: Decimal
    dias_mora: int
    monto_mora: Decimal
    tasa_mora: Decimal
    estado: str
    observaciones: Optional[str] = None
    esta_vencida: bool = False
    monto_pendiente_total: Decimal = Decimal("0.00")
    porcentaje_pagado: Decimal = Decimal("0.00")

    # FASE 2: Campos adicionales sincronizados con ORM
    dias_morosidad: Optional[int] = Field(None, description="Días de atraso (actualización automática)")
    monto_morosidad: Optional[Decimal] = Field(None, description="Monto pendiente (actualización automática)")
    es_cuota_especial: Optional[bool] = Field(None, description="Indica si es una cuota especial")
    creado_en: Optional[datetime] = Field(None, description="Fecha de creación del registro")
    actualizado_en: Optional[datetime] = Field(None, description="Fecha de última actualización")

    model_config = {"from_attributes": True}


class TablaAmortizacionRequest(BaseModel):
    # Schema para solicitar generación de tabla de amortización
    monto_financiado: Decimal = Field(..., gt=0, description="Monto a financiar")
    tasa_interes: Decimal = Field(..., ge=0, description="Tasa de interés anual")
    numero_cuotas: int = Field(..., gt=0, description="Número de cuotas")
    fecha_inicio: date = Field(..., description="Fecha de inicio del préstamo")
    tipo_amortizacion: str = Field(default="FRANCESA", description="Tipo de amortización")
    tasa_mora: Optional[Decimal] = Field(None, ge=0, description="Tasa de mora diaria")

    @field_validator("monto_financiado", "tasa_interes", "tasa_mora", mode="before")
    @classmethod
    def validate_decimal_places(cls, v):
        if v is not None and not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if v else v


class TablaAmortizacionResponse(BaseModel):
    # Schema para respuesta de tabla de amortización
    cuotas: List[CuotaResponse]
    resumen: dict


class RecalcularMoraRequest(BaseModel):
    # Schema para recalcular mora
    tasa_mora_diaria: Optional[Decimal] = Field(None, ge=0, description="Tasa de mora diaria")
    fecha_calculo: Optional[date] = Field(None, description="Fecha de cálculo")

    @field_validator("tasa_mora_diaria", mode="before")
    @classmethod
    def validate_decimal_places(cls, v):
        if v is not None and not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if v else v


class RecalcularMoraResponse(BaseModel):
    # Schema para respuesta de recálculo de mora
    cuotas_actualizadas: int
    total_mora_calculada: Decimal
    mensaje: str


class EstadoCuentaResponse(BaseModel):
    # Schema para respuesta de estado de cuenta
    prestamo_id: int
    resumen: dict
    cuotas_pagadas: List[CuotaResponse]
    cuotas_pendientes: List[CuotaResponse]
    cuotas_vencidas: List[CuotaResponse]
    proximas_cuotas: List[CuotaResponse]
    total_mora: float


class ProyeccionPagoRequest(BaseModel):
    # Schema para proyectar pago
    monto_pago: Decimal = Field(..., gt=0, description="Monto del pago a proyectar")
    fecha_pago: Optional[date] = Field(None, description="Fecha del pago")

    @field_validator("monto_pago", mode="before")
    @classmethod
    def validate_decimal_places(cls, v):
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ProyeccionPagoResponse(BaseModel):
    # Schema para respuesta de proyección de pago
    cuotas_afectadas: List[CuotaResponse]
    nuevo_saldo_pendiente: float
    mensaje: str


# tasa_interes_anual: Decimal = Field( ..., ge=0, le=100, description="Tasa de interés anual (%)" ) numero_cuotas: int =
# Field( ..., gt=0, le=360, description="Número de cuotas" ) fecha_primer_vencimiento: date = Field
# del primer vencimiento" ) modalidad: str = Field( default="MENSUAL", description="SEMANAL, QUINCENAL, MENSUAL" )
# sistema_amortizacion: str = Field( default="FRANCES", description="FRANCES, ALEMAN, AMERICANO" )
# @field_validator("monto_financiado", "tasa_interes_anual", mode="before") @classmethod def validate_decimal_places(cls, v):
# Decimal(str(v)) return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) @field_validator("modalidad") @classmethod def
# validate_modalidad(cls, v): """Validar modalidad""" modalidades_validas = [ "SEMANAL", "QUINCENAL", "MENSUAL", "BIMENSUAL",
# "TRIMESTRAL", ] if v not in modalidades_validas: raise ValueError
# ".join(modalidades_validas)}' ) return v @field_validator("sistema_amortizacion") @classmethod def validate_sistema
# CuotaDetalle(BaseModel): """Detalle de una cuota en la tabla de amortización""" numero_cuota: int fecha_vencimiento: date
# saldo_inicial: Decimal capital: Decimal interes: Decimal cuota: Decimal saldo_final: Decimal @field_validator
# "saldo_inicial", "capital", "interes", "cuota", "saldo_final", mode="before", ) @classmethod def
# isinstance(v, Decimal): v = Decimal(str(v)) return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)class
# TablaAmortizacionResponse(BaseModel): """Schema para respuesta de tabla de amortización""" cuotas: List[CuotaDetalle]
# resumen: dict = Field
# tabla", )class AplicarPagoRequest(BaseModel): """Schema para aplicar un pago a cuotas""" cuota_ids: List[int] = Field
# description="IDs de cuotas a aplicar el pago" ) monto_total: Decimal = Field(..., gt=0, description="Monto total del pago")
# orden_aplicacion: str = Field( default="SECUENCIAL", description="SECUENCIAL (orden de cuotas) o VENCIDAS_PRIMERO", )
# @field_validator("monto_total", mode="before") @classmethod def validate_decimal_places(cls, v): """Validar y normalizar
# v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)class AplicarPagoResponse(BaseModel): """Schema para respuesta de
# aplicación de pago""" cuotas_afectadas: List[int] detalle_aplicacion: List[dict] monto_aplicado: Decimal monto_sobrante:
# Decimal mensaje: strclass EstadoCuentaResponse(BaseModel): """Schema para estado de cuenta de un préstamo""" prestamo_id:
# int codigo_prestamo: str cliente: dict resumen: dict = Field
# préstamo" ) cuotas_pagadas: List[CuotaResponse] cuotas_pendientes: List[CuotaResponse] cuotas_vencidas: List[CuotaResponse]
# Field( ..., gt=0, description="Monto que se planea pagar" ) fecha_proyeccion: Optional[date] = Field
# description="Fecha para la proyección (default: hoy)" ) @field_validator("monto_pago", mode="before") @classmethod def
# isinstance(v, Decimal): v = Decimal(str(v)) return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)class
# List[CuotaResponse] monto_a_mora: Decimal monto_a_interes: Decimal monto_a_capital: Decimal monto_sobrante: Decimal
# nuevo_saldo_pendiente: Decimal cuotas_restantes: int mensaje: strclass RecalcularMoraRequest(BaseModel): """Schema para
# solicitar recálculo de mora""" prestamo_id: int tasa_mora_diaria: Optional[Decimal] = Field
# description="Tasa de mora diaria (%). Si no se especifica, usa \ la configurada en el sistema", ) fecha_calculo:
# Optional[date] = Field( default=None, description="Fecha para el cálculo (default: hoy)" )
# @field_validator("tasa_mora_diaria", mode="before") @classmethod def validate_decimal_places(cls, v): """Validar y
# v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)class RecalcularMoraResponse(BaseModel): """Schema para respuesta de
# recálculo de mora""" prestamo_id: int cuotas_actualizadas: int total_mora_anterior: Decimal total_mora_nueva: Decimal
# diferencia: Decimal cuotas_con_mora: List[dict] mensaje: str

"""
"""
