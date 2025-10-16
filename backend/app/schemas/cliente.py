# backend/app/schemas/cliente.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class ClienteBase(BaseModel):
    # Datos personales
    cedula: str = Field(..., min_length=8, max_length=20)
    nombres: str = Field(..., min_length=2, max_length=100)
    apellidos: str = Field(..., min_length=2, max_length=100)
    telefono: Optional[str] = Field(None, max_length=15)
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = Field(None, max_length=100)
    
    # Datos del vehículo
    modelo_vehiculo: Optional[str] = Field(None, max_length=100)
    marca_vehiculo: Optional[str] = Field(None, max_length=50)
    anio_vehiculo: Optional[int] = Field(None, ge=1900, le=2030)
    color_vehiculo: Optional[str] = Field(None, max_length=30)
    chasis: Optional[str] = Field(None, max_length=50)
    motor: Optional[str] = Field(None, max_length=50)
    
    # Concesionario - Solo campo legacy (FK comentado en modelo)
    # concesionario_id: Optional[int] = None  # COMENTADO: No existe en modelo Cliente
    concesionario: Optional[str] = Field(None, max_length=100)  # Legacy
    vendedor_concesionario: Optional[str] = Field(None, max_length=100)
    
    # Modelo de vehículo - Solo campo legacy (FK comentado en modelo)
    # modelo_vehiculo_id: Optional[int] = None  # COMENTADO: No existe en modelo Cliente
    
    # Financiamiento
    total_financiamiento: Optional[Decimal] = Field(None, ge=0)
    cuota_inicial: Optional[Decimal] = Field(None, ge=0)
    fecha_entrega: Optional[date] = None
    numero_amortizaciones: Optional[int] = Field(None, ge=1, le=360)
    modalidad_pago: Optional[str] = Field(None, pattern="^(SEMANAL|QUINCENAL|MENSUAL|BIMENSUAL)$")
    
    # Asignación - ForeignKeys
    asesor_config_id: Optional[int] = None  # Asesor de configuración (tabla asesores)
    
    # Notas
    notas: Optional[str] = None
    
    @field_validator('total_financiamiento', 'cuota_inicial', mode='before')
    @classmethod
    def validate_decimal_fields(cls, v):
        """Validar campos decimales"""
        if v is None:
            return v
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal('0.01'))
    
    @field_validator('cuota_inicial', mode='after')
    @classmethod
    def validate_cuota_inicial(cls, v, info):
        """Validar que cuota inicial no sea mayor al total"""
        if v is not None and 'total_financiamiento' in info.data:
            total = info.data['total_financiamiento']
            if total is not None and v > total:
                raise ValueError('La cuota inicial no puede ser mayor al total del financiamiento')
        return v


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    # Datos personales
    cedula: Optional[str] = Field(None, min_length=8, max_length=20)
    nombres: Optional[str] = Field(None, min_length=2, max_length=100)
    apellidos: Optional[str] = Field(None, min_length=2, max_length=100)
    telefono: Optional[str] = Field(None, max_length=15)
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = Field(None, max_length=100)
    
    # Datos del vehículo
    modelo_vehiculo: Optional[str] = Field(None, max_length=100)
    marca_vehiculo: Optional[str] = Field(None, max_length=50)
    anio_vehiculo: Optional[int] = Field(None, ge=1900, le=2030)
    color_vehiculo: Optional[str] = Field(None, max_length=30)
    chasis: Optional[str] = Field(None, max_length=50)
    motor: Optional[str] = Field(None, max_length=50)
    
    # Concesionario
    concesionario: Optional[str] = Field(None, max_length=100)
    vendedor_concesionario: Optional[str] = Field(None, max_length=100)
    
    # Financiamiento
    total_financiamiento: Optional[Decimal] = Field(None, ge=0)
    cuota_inicial: Optional[Decimal] = Field(None, ge=0)
    fecha_entrega: Optional[date] = None
    numero_amortizaciones: Optional[int] = Field(None, ge=1, le=360)
    modalidad_pago: Optional[str] = Field(None, pattern="^(SEMANAL|QUINCENAL|MENSUAL|BIMENSUAL)$")
    
    # Asignación y estado
    asesor_config_id: Optional[int] = None
    estado: Optional[str] = None
    estado_financiero: Optional[str] = None
    
    # Notas
    notas: Optional[str] = None


class ClienteResponse(ClienteBase):
    id: int
    estado: str
    activo: bool
    estado_financiero: Optional[str] = None
    dias_mora: int = 0
    fecha_asignacion: Optional[date] = None
    fecha_registro: datetime
    fecha_actualizacion: Optional[datetime] = None
    usuario_registro: Optional[str] = None
    
    # Campos calculados
    monto_financiado: Optional[Decimal] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('monto_financiado', mode='before')
    @classmethod
    def calculate_monto_financiado(cls, v, info):
        """Calcular monto financiado (total - cuota inicial)"""
        if 'total_financiamiento' in info.data and 'cuota_inicial' in info.data:
            total = info.data.get('total_financiamiento', 0) or 0
            inicial = info.data.get('cuota_inicial', 0) or 0
            return total - inicial
        return v


class ClienteList(BaseModel):
    """Schema para lista de clientes con paginación"""
    items: List[ClienteResponse]
    total: int
    page: int = 1
    page_size: int = 10
    total_pages: int
    
    model_config = ConfigDict(from_attributes=True)


class ClienteSearchFilters(BaseModel):
    """Filtros avanzados para búsqueda de clientes"""
    # Búsqueda de texto
    search_text: Optional[str] = Field(None, description="Búsqueda en nombre, cédula o móvil")
    
    # Filtros específicos
    estado: Optional[str] = Field(None, pattern="^(ACTIVO|INACTIVO|MORA)$")
    estado_financiero: Optional[str] = Field(None, pattern="^(AL_DIA|MORA|VENCIDO)$")
    asesor_config_id: Optional[int] = None
    concesionario: Optional[str] = None
    modelo_vehiculo: Optional[str] = None
    modalidad_pago: Optional[str] = Field(None, pattern="^(SEMANAL|QUINCENAL|MENSUAL|BIMENSUAL)$")
    
    # Filtros de fecha
    fecha_registro_desde: Optional[date] = None
    fecha_registro_hasta: Optional[date] = None
    fecha_entrega_desde: Optional[date] = None
    fecha_entrega_hasta: Optional[date] = None
    
    # Filtros de monto
    monto_financiamiento_min: Optional[Decimal] = None
    monto_financiamiento_max: Optional[Decimal] = None
    
    # Filtros de mora
    dias_mora_min: Optional[int] = Field(None, ge=0)
    dias_mora_max: Optional[int] = Field(None, ge=0)
    
    # Ordenamiento
    order_by: Optional[str] = Field(None, pattern="^(nombre|fecha_registro|monto_financiamiento|dias_mora)$")
    order_direction: Optional[str] = Field("asc", pattern="^(asc|desc)$")


class ClienteResumenFinanciero(BaseModel):
    """Resumen financiero del cliente"""
    total_financiado: Decimal
    total_pagado: Decimal
    saldo_pendiente: Decimal
    cuotas_pagadas: int
    cuotas_totales: int
    porcentaje_avance: float
    proxima_cuota: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


class ClienteDetallado(ClienteResponse):
    """Cliente con información detallada"""
    # Información del asesor
    asesor_nombre: Optional[str] = None
    asesor_email: Optional[str] = None
    
    # Resumen financiero
    resumen_financiero: Optional[ClienteResumenFinanciero] = None
    
    # Estadísticas
    total_prestamos: int = 0
    prestamos_activos: int = 0
    ultimo_pago: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


class ClienteCreateWithLoan(ClienteBase):
    """Schema para crear cliente con préstamo automático"""
    # Heredar todos los campos de ClienteBase
    
    # Campos obligatorios para financiamiento
    total_financiamiento: Decimal = Field(..., gt=0, description="Total del financiamiento")
    cuota_inicial: Decimal = Field(default=Decimal("0.00"), ge=0)
    fecha_entrega: date = Field(..., description="Fecha de entrega del vehículo")
    numero_amortizaciones: int = Field(..., ge=1, le=360, description="Número de cuotas")
    modalidad_pago: str = Field(..., pattern="^(SEMANAL|QUINCENAL|MENSUAL|BIMENSUAL)$")
    
    # Datos del vehículo (obligatorios para financiamiento)
    modelo_vehiculo: str = Field(..., min_length=1, max_length=100)
    marca_vehiculo: str = Field(..., min_length=1, max_length=50)
    
    # Asesor asignado
    asesor_config_id: int = Field(..., description="ID del asesor de configuración responsable")
    
    # Configuración del préstamo
    tasa_interes_anual: Optional[Decimal] = Field(None, ge=0, le=100, description="Tasa de interés anual (%)")
    generar_tabla_automatica: bool = Field(True, description="Generar tabla de amortización automáticamente")


class ClienteQuickActions(BaseModel):
    """Acciones rápidas disponibles para un cliente"""
    puede_registrar_pago: bool
    puede_enviar_recordatorio: bool
    puede_generar_estado_cuenta: bool
    puede_modificar_financiamiento: bool
    puede_reasignar_asesor: bool
    
    model_config = ConfigDict(from_attributes=True)
