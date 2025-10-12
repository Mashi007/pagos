# backend/app/schemas/cliente.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional
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
    
    # ============================================
    # DATOS DE FINANCIAMIENTO (NUEVOS)
    # ============================================
    modelo_vehiculo: Optional[str] = Field(None, max_length=100, description="Modelo del vehículo a financiar")
    concesionario: Optional[str] = Field(None, max_length=100, description="Concesionario donde se compra")
    total_financiamiento: Optional[Decimal] = Field(None, gt=0, description="Total del financiamiento")
    cuota_inicial: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, description="Cuota inicial (se descuenta)")
    fecha_entrega: Optional[date] = Field(None, description="Fecha de entrega del vehículo (inicio amortización)")
    numero_amortizaciones: Optional[int] = Field(None, gt=0, le=360, description="Número de amortizaciones")
    modalidad_financiamiento: Optional[str] = Field(
        default="MENSUAL", 
        description="Modalidad: SEMANAL, QUINCENAL, MENSUAL"
    )
    
    # ============================================
    # ASIGNACIÓN (NUEVO)
    # ============================================
    asesor_id: Optional[int] = Field(None, description="ID del asesor responsable")
    
    # Otros
    notas: Optional[str] = None
    
    @field_validator('modalidad_financiamiento')
    @classmethod
    def validate_modalidad(cls, v):
        """Validar modalidad de financiamiento"""
        if v and v not in ['SEMANAL', 'QUINCENAL', 'MENSUAL']:
            raise ValueError('Modalidad debe ser: SEMANAL, QUINCENAL o MENSUAL')
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
    
    # Datos de financiamiento
    modelo_vehiculo: Optional[str] = Field(None, max_length=100)
    concesionario: Optional[str] = Field(None, max_length=100)
    total_financiamiento: Optional[Decimal] = Field(None, gt=0)
    cuota_inicial: Optional[Decimal] = Field(None, ge=0)
    fecha_entrega: Optional[date] = None
    numero_amortizaciones: Optional[int] = Field(None, gt=0, le=360)
    modalidad_financiamiento: Optional[str] = None
    
    # Asignación
    asesor_id: Optional[int] = None
    
    # Estado y notas
    estado: Optional[str] = None
    notas: Optional[str] = None
    
    @field_validator('modalidad_financiamiento')
    @classmethod
    def validate_modalidad(cls, v):
        """Validar modalidad de financiamiento"""
        if v and v not in ['SEMANAL', 'QUINCENAL', 'MENSUAL']:
            raise ValueError('Modalidad debe ser: SEMANAL, QUINCENAL o MENSUAL')
        return v


class ClienteResponse(ClienteBase):
    id: int
    estado: str
    activo: bool
    fecha_registro: datetime
    fecha_actualizacion: Optional[datetime] = None
    usuario_registro: Optional[str] = None
    
    # ============================================
    # CAMPOS CALCULADOS (NUEVOS)
    # ============================================
    dias_mora: int = 0
    saldo_pendiente_total: Decimal = Decimal("0.00")
    
    # Propiedades calculadas (se llenan desde el modelo)
    nombre_completo: Optional[str] = None
    monto_financiado: Optional[float] = None
    tiene_prestamos_activos: Optional[bool] = None
    estado_mora: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ClienteList(BaseModel):
    """Schema para lista de clientes con paginación"""
    items: list[ClienteResponse]
    total: int
    page: int = 1
    page_size: int = 10
    total_pages: int
    
    model_config = ConfigDict(from_attributes=True)


# ============================================
# SCHEMAS PARA BÚSQUEDA AVANZADA (NUEVOS)
# ============================================

class ClienteSearchFilters(BaseModel):
    """Filtros para búsqueda avanzada de clientes"""
    # Búsqueda por texto
    buscar: Optional[str] = Field(None, description="Buscar por nombre, cédula o móvil")
    
    # Filtros específicos
    estado: Optional[str] = Field(None, description="ACTIVO, INACTIVO, MORA")
    asesor_id: Optional[int] = Field(None, description="ID del asesor asignado")
    concesionario: Optional[str] = Field(None, description="Nombre del concesionario")
    modelo_vehiculo: Optional[str] = Field(None, description="Modelo del vehículo")
    modalidad_financiamiento: Optional[str] = Field(None, description="SEMANAL, QUINCENAL, MENSUAL")
    
    # Filtros por rango
    monto_min: Optional[Decimal] = Field(None, ge=0, description="Monto mínimo de financiamiento")
    monto_max: Optional[Decimal] = Field(None, ge=0, description="Monto máximo de financiamiento")
    dias_mora_min: Optional[int] = Field(None, ge=0, description="Días mínimos de mora")
    dias_mora_max: Optional[int] = Field(None, ge=0, description="Días máximos de mora")
    
    # Filtros por fecha
    fecha_registro_desde: Optional[date] = None
    fecha_registro_hasta: Optional[date] = None
    fecha_entrega_desde: Optional[date] = None
    fecha_entrega_hasta: Optional[date] = None


class ClienteSearchResponse(BaseModel):
    """Respuesta de búsqueda avanzada"""
    clientes: List[ClienteResponse]
    total: int
    filtros_aplicados: ClienteSearchFilters
    estadisticas: dict = Field(default_factory=dict, description="Estadísticas de la búsqueda")


class ClienteFichaDetallada(ClienteResponse):
    """Ficha completa del cliente con información financiera"""
    # Información del asesor
    asesor_nombre: Optional[str] = None
    asesor_email: Optional[str] = None
    
    # Resumen financiero
    resumen_financiero: dict = Field(default_factory=dict)
    
    # Estadísticas de pagos
    estadisticas_pagos: dict = Field(default_factory=dict)
    
    # Próximas acciones
    proximas_cuotas: List[dict] = Field(default_factory=list)
    alertas: List[str] = Field(default_factory=list)
