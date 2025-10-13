# backend/app/schemas/pago.py
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import date, time, datetime
from decimal import Decimal, ROUND_HALF_UP


class PagoBase(BaseModel):
    """Schema base para Pago"""
    prestamo_id: int
    monto_pagado: Decimal = Field(..., gt=0, description="Monto pagado")
    monto_capital: Decimal = Field(default=Decimal("0.00"), ge=0, description="Monto aplicado a capital")
    monto_interes: Decimal = Field(default=Decimal("0.00"), ge=0, description="Monto aplicado a interés")
    monto_mora: Decimal = Field(default=Decimal("0.00"), ge=0, description="Monto de mora")
    descuento: Decimal = Field(default=Decimal("0.00"), ge=0, description="Descuento aplicado")
    fecha_pago: date
    fecha_vencimiento: date
    metodo_pago: str = Field(default="EFECTIVO")
    numero_operacion: Optional[str] = Field(None, max_length=50)
    comprobante: Optional[str] = Field(None, max_length=50)
    banco: Optional[str] = Field(None, max_length=50)
    observaciones: Optional[str] = None
    
    @field_validator('monto_pagado', 'monto_capital', 'monto_interes', 'monto_mora', 'descuento', mode='before')
    @classmethod
    def validate_decimal_places(cls, v: Decimal) -> Decimal:
        """Validar que los montos tengan máximo 2 decimales"""
        if v is None:
            return v
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        # Redondear a 2 decimales
        return v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class PagoCreate(PagoBase):
    """Schema para crear un pago"""
    pass


class PagoResponse(PagoBase):
    """Schema para respuesta de pago"""
    id: int
    numero_cuota: int
    codigo_pago: Optional[str] = None
    monto_cuota_programado: Decimal
    monto_total: Decimal
    hora_pago: Optional[time] = None
    dias_mora: int
    tasa_mora: Decimal
    estado: str
    tipo_pago: str
    usuario_registro: Optional[str] = None
    creado_en: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PagoList(BaseModel):
    """Schema para lista de pagos con paginación"""
    items: list[PagoResponse]
    total: int
    page: int = 1
    page_size: int = 10
    total_pages: int
    
    model_config = ConfigDict(from_attributes=True)


class PagoManualRequest(BaseModel):
    """Schema para registro de pago manual avanzado"""
    # Identificación del cliente
    cliente_cedula: str = Field(..., description="Cédula del cliente")
    
    # Cuotas a pagar
    cuotas_seleccionadas: list[int] = Field(..., description="IDs de cuotas a pagar")
    
    # Información del pago
    monto_pagado: Decimal = Field(..., gt=0, description="Monto total pagado")
    fecha_pago: date = Field(..., description="Fecha efectiva del pago")
    metodo_pago: str = Field(..., regex="^(EFECTIVO|TRANSFERENCIA|TARJETA|CHEQUE)$")
    
    # Documentación
    numero_operacion: Optional[str] = Field(None, max_length=50, description="Número de operación bancaria")
    comprobante: Optional[str] = Field(None, max_length=50, description="Número de comprobante")
    banco: Optional[str] = Field(None, max_length=50, description="Banco origen")
    
    # Configuración
    aplicar_descuento: bool = Field(False, description="Aplicar descuento por pronto pago")
    descuento_porcentaje: Optional[Decimal] = Field(None, ge=0, le=100, description="Porcentaje de descuento")
    calcular_mora_automatica: bool = Field(True, description="Calcular mora automáticamente")
    
    # Observaciones
    observaciones: Optional[str] = Field(None, description="Observaciones del pago")


class PagoManualResponse(BaseModel):
    """Schema para respuesta de pago manual"""
    pago_id: int
    cliente_id: int
    cliente_nombre: str
    cuotas_afectadas: list[dict]
    distribucion_pago: dict
    resumen: dict
    mensaje: str
    
    model_config = ConfigDict(from_attributes=True)


class PagoHistorialFilters(BaseModel):
    """Filtros para historial de pagos"""
    # Filtros de cliente
    cliente_id: Optional[int] = None
    cliente_cedula: Optional[str] = None
    cliente_nombre: Optional[str] = None
    
    # Filtros de fecha
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    
    # Filtros de pago
    metodo_pago: Optional[str] = None
    estado_conciliacion: Optional[str] = None
    monto_min: Optional[Decimal] = None
    monto_max: Optional[Decimal] = None
    
    # Filtros de mora
    con_mora: Optional[bool] = None
    dias_mora_min: Optional[int] = None
    
    # Ordenamiento
    order_by: Optional[str] = Field("fecha_pago", regex="^(fecha_pago|monto_pagado|cliente|cuota)$")
    order_direction: Optional[str] = Field("desc", regex="^(asc|desc)$")


class PagoUpdate(BaseModel):
    """Schema para actualizar un pago"""
    monto_pagado: Optional[Decimal] = Field(None, gt=0)
    fecha_pago: Optional[date] = None
    metodo_pago: Optional[str] = None
    numero_operacion: Optional[str] = Field(None, max_length=50)
    comprobante: Optional[str] = Field(None, max_length=50)
    banco: Optional[str] = Field(None, max_length=50)
    observaciones: Optional[str] = None


class PagoAnularRequest(BaseModel):
    """Schema para anular un pago"""
    justificacion: str = Field(..., min_length=10, description="Justificación obligatoria para anulación")
    revertir_amortizacion: bool = Field(True, description="Revertir cambios en amortización")


class CuotasPendientesResponse(BaseModel):
    """Schema para mostrar cuotas pendientes de un cliente"""
    cliente_id: int
    cliente_nombre: str
    prestamos: list[dict]
    total_cuotas_pendientes: int
    total_monto_pendiente: Decimal
    
    model_config = ConfigDict(from_attributes=True)


class DistribucionPagoResponse(BaseModel):
    """Schema para mostrar cómo se distribuye un pago"""
    monto_total: Decimal
    aplicado_a_mora: Decimal
    aplicado_a_interes: Decimal
    aplicado_a_capital: Decimal
    sobrante: Decimal
    cuotas_afectadas: list[dict]
    
    model_config = ConfigDict(from_attributes=True)