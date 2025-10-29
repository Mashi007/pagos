from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.validators import sanitize_html

# Constantes de validación
MIN_CEDULA_LENGTH = 8
MAX_CEDULA_LENGTH = 20
MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 100
MIN_PHONE_LENGTH = 13
MAX_PHONE_LENGTH = 13
MIN_ADDRESS_LENGTH = 5
MAX_ADDRESS_LENGTH = 500
MAX_NOTES_LENGTH = 1000
MAX_AMORTIZACIONES = 360
MAX_TASA_INTERES = 100
MAX_COMMENTS_LENGTH = 500


class ClienteBase(BaseModel):
    cedula: str = Field(
        ...,
        min_length=MIN_CEDULA_LENGTH,
        max_length=MAX_CEDULA_LENGTH,
        description="Cédula del cliente",
    )
    nombres: str = Field(
        ...,
        min_length=MIN_NAME_LENGTH,
        max_length=MAX_NAME_LENGTH,
        description="2-4 palabras (nombres + apellidos unificados)",
    )
    telefono: str = Field(
        ...,
        min_length=MIN_PHONE_LENGTH,
        max_length=MAX_PHONE_LENGTH,
        description="Teléfono del cliente",
    )
    email: EmailStr = Field(..., description="Validado por validadores")
    direccion: str = Field(
        ...,
        min_length=MIN_ADDRESS_LENGTH,
        max_length=MAX_ADDRESS_LENGTH,
        description="Dirección del cliente",
    )
    fecha_nacimiento: date = Field(..., description="Validado por validadores")
    ocupacion: str = Field(
        ...,
        min_length=MIN_NAME_LENGTH,
        max_length=MAX_NAME_LENGTH,
        description="Ocupación del cliente (máximo 2 palabras)",
    )

    modelo_vehiculo: str = Field(
        ..., min_length=1, max_length=100, description="Modelo del vehículo"
    )
    concesionario: str = Field(
        ..., min_length=1, max_length=100, description="Concesionario"
    )
    analista: str = Field(
        ..., min_length=1, max_length=100, description="Analista asignado"
    )

    # Estado - OBLIGATORIO
    estado: str = Field(
        ...,
        pattern="^(ACTIVO|INACTIVO|FINALIZADO)$",
        description="Activo/Inactivo/Finalizado",
    )

    # Notas - OBLIGATORIO con default 'NA'
    notas: str = Field(
        default="NA",
        max_length=MAX_NOTES_LENGTH,
        description="Notas adicionales (default 'NA')",
    )

    @classmethod
    def validate_nombres(cls, v):
        """Validar nombres: 2-4 palabras, primera letra mayúscula"""
        if not v:
            raise ValueError("Nombres requeridos")

        words = v.strip().split()
        words = [word for word in words if word]  # Filtrar palabras vacías

        if len(words) < 2:
            raise ValueError("Mínimo 2 palabras requeridas (nombre + apellido)")
        if len(words) > 4:
            raise ValueError("Máximo 4 palabras permitidas")

        return v

    @classmethod
    def validate_ocupacion(cls, v):
        """Validar ocupacion: máximo 2 palabras, primera letra mayúscula"""
        if not v:
            raise ValueError("Ocupación requerida")

        words = v.strip().split()
        words = [word for word in words if word]  # Filtrar palabras vacías

        if len(words) > 2:
            raise ValueError("Máximo 2 palabras permitidas en ocupación")

        return v

    @field_validator("notas", "direccion", mode="before")
    @classmethod
    def sanitize_html_fields(cls, v):
        if v is None or v == "":
            return "NA" if v is None else v
        return sanitize_html(v)

    @field_validator("nombres", mode="before")
    @classmethod
    def validate_nombres_words(cls, v):
        """Validar y formatear nombres: 2-4 palabras, primera letra mayúscula"""
        if not v:
            raise ValueError("Nombres requeridos")
        return cls.validate_nombres(v)

    @field_validator("ocupacion", mode="before")
    @classmethod
    def validate_ocupacion_words(cls, v):
        """Validar y formatear ocupacion: max 2 palabras"""
        if not v:
            raise ValueError("Ocupación requerida")
        return cls.validate_ocupacion(v)

    @field_validator("estado", mode="before")
    @classmethod
    def normalize_estado(cls, v):
        """Normalizar estado a mayúsculas"""
        if v:
            return v.upper()
        return v


class ClienteCreate(BaseModel):
    cedula: str = Field(..., min_length=MIN_CEDULA_LENGTH, max_length=MAX_CEDULA_LENGTH, description="Cédula del cliente")
    nombres: str = Field(..., min_length=MIN_NAME_LENGTH, max_length=MAX_NAME_LENGTH, description="Nombres del cliente")
    telefono: str = Field(..., min_length=MIN_PHONE_LENGTH, max_length=MAX_PHONE_LENGTH, description="Teléfono")
    email: EmailStr = Field(..., description="Email del cliente")
    direccion: str = Field(..., min_length=MIN_ADDRESS_LENGTH, max_length=MAX_ADDRESS_LENGTH, description="Dirección")
    fecha_nacimiento: date = Field(..., description="Fecha de nacimiento")
    ocupacion: str = Field(..., min_length=MIN_NAME_LENGTH, max_length=MAX_NAME_LENGTH, description="Ocupación")
    modelo_vehiculo: Optional[str] = Field(None, description="Modelo del vehículo")
    concesionario: Optional[str] = Field(None, description="Concesionario")
    analista: Optional[str] = Field(None, description="Analista asignado")
    estado: str = Field(..., pattern="^(ACTIVO|INACTIVO|FINALIZADO)$", description="Estado del cliente")
    activo: Optional[bool] = Field(True, description="Cliente activo")
    notas: Optional[str] = Field("NA", description="Notas adicionales")
    confirm_duplicate: bool = Field(False, description="Confirmar si es duplicado")


class ClienteCreateWithConfirmation(BaseModel):
    """Schema para crear cliente con confirmación de duplicado"""

    cliente_data: ClienteCreate
    confirmacion: bool = Field(False, description="Confirmación de duplicado")
    comentarios: Optional[str] = Field(
        None, max_length=MAX_COMMENTS_LENGTH, description="Comentarios adicionales"
    )


class ClienteUpdate(BaseModel):

    cedula: Optional[str] = Field(None, min_length=8, max_length=20)
    nombres: Optional[str] = Field(
        None, min_length=2, max_length=100
    )  # 2-4 palabras validado
    telefono: Optional[str] = Field(
        None, min_length=MIN_PHONE_LENGTH, max_length=MAX_PHONE_LENGTH
    )
    email: Optional[EmailStr] = None
    direccion: Optional[str] = Field(None, min_length=5, max_length=500)
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = Field(
        None, min_length=2, max_length=100
    )  # Max 2 palabras validado

    modelo_vehiculo: Optional[str] = Field(None, min_length=1, max_length=100)
    concesionario: Optional[str] = Field(None, min_length=1, max_length=100)
    analista: Optional[str] = Field(None, min_length=1, max_length=100)

    # Estado
    estado: Optional[str] = Field(None, pattern="^(ACTIVO|INACTIVO|FINALIZADO)$")
    activo: Optional[bool] = None

    # Notas - OBLIGATORIO con default 'NA'
    notas: Optional[str] = Field(None, max_length=1000)

    @classmethod
    def validate_nombres(cls, v):
        """Validar nombres: 2-4 palabras"""
        if v:
            words = v.strip().split()
            words = [word for word in words if word]

            if len(words) < 2:
                raise ValueError("Mínimo 2 palabras requeridas")
            if len(words) > 4:
                raise ValueError("Máximo 4 palabras permitidas")
        return v

    @classmethod
    def validate_ocupacion(cls, v):
        """Validar ocupacion: máximo 2 palabras"""
        if v:
            words = v.strip().split()
            words = [word for word in words if word]

            if len(words) > 2:
                raise ValueError("Máximo 2 palabras permitidas en ocupación")
        return v

    @field_validator("notas", "direccion", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_html(v)
        return v

    @field_validator("nombres", mode="before")
    @classmethod
    def validate_nombres_on_update(cls, v):
        if v:
            return ClienteBase.validate_nombres(v)
        return v

    @field_validator("ocupacion", mode="before")
    @classmethod
    def validate_ocupacion_on_update(cls, v):
        if v:
            return ClienteBase.validate_ocupacion(v)
        return v


class ClienteResponse(ClienteBase):
    """Schema de respuesta para cliente"""

    id: int
    activo: bool
    usuario_registro: str  # Email del usuario que registró

    model_config = ConfigDict(from_attributes=True)


class ClienteList(BaseModel):
    """Schema para lista de clientes con paginación"""

    items: List[ClienteResponse]
    total: int
    page: int = 1
    page_size: int = 10
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class ClienteSearchFilters(BaseModel):

    # Búsqueda de texto
    search_text: Optional[str] = Field(None, description="Texto de búsqueda")

    estado: Optional[str] = Field(None, pattern="^(ACTIVO|INACTIVO|FINALIZADO)$")
    activo: Optional[bool] = None
    analista: Optional[str] = None
    concesionario: Optional[str] = None
    modelo_vehiculo: Optional[str] = None

    fecha_registro_desde: Optional[date] = None
    fecha_registro_hasta: Optional[date] = None

    # Ordenamiento
    order_by: Optional[str] = Field(None, description="Campo por el cual ordenar")
    order_direction: Optional[str] = Field("asc", pattern="^(asc|desc)$")


class ClienteDetallado(ClienteResponse):
    """Cliente con información detallada"""

    # Información del analista
    analista_nombre: Optional[str] = None

    # Estadísticas

    model_config = ConfigDict(from_attributes=True)


class ClienteCreateWithLoan(ClienteBase):
    """Schema para crear cliente con préstamo automático"""

    total_financiamiento: Decimal = Field(..., description="Total del financiamiento")
    cuota_inicial: Decimal = Field(default=Decimal("0.00"), ge=0)
    fecha_entrega: date = Field(..., description="Fecha de entrega del vehículo")
    numero_amortizaciones: int = Field(
        ..., ge=1, le=MAX_AMORTIZACIONES, description="Número de amortizaciones"
    )
    modalidad_pago: str = Field(..., pattern="^(SEMANAL|QUINCENAL|MENSUAL|BIMENSUAL)$")

    # Configuración del préstamo
    tasa_interes_anual: Optional[Decimal] = Field(
        None,
        ge=0,
        le=MAX_TASA_INTERES,
        description="Tasa de interés anual (%)",
    )
    generar_tabla_automatica: bool = Field(
        True, description="Generar tabla de amortización automáticamente"
    )


class ClienteQuickActions(BaseModel):
    """Acciones rápidas disponibles para un cliente"""

    puede_registrar_pago: bool
    puede_enviar_recordatorio: bool
    puede_generar_estado_cuenta: bool
    puede_modificar_financiamiento: bool
    puede_reasignar_analista: bool

    model_config = ConfigDict(from_attributes=True)
