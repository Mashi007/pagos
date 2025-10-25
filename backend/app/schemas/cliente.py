# backend/app/schemas/cliente.py

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
        description="Cédula validada por validadores",
    )
    nombres: str = Field(
        ...,
        min_length=MIN_NAME_LENGTH,
        max_length=MAX_NAME_LENGTH,
        description="1-2 palabras máximo",
    )
        ...,
        min_length=MIN_NAME_LENGTH,
        max_length=MAX_NAME_LENGTH,
        description="1-2 palabras máximo",
    )
    telefono: str = Field(
        ...,
        min_length=MIN_PHONE_LENGTH,
        max_length=MAX_PHONE_LENGTH,
        pattern=r"^\+58[1-9]\d{9}$",
    )
    email: EmailStr = Field(..., description="Validado por validadores")
    direccion: str = Field(
        ...,
        min_length=MIN_ADDRESS_LENGTH,
        max_length=MAX_ADDRESS_LENGTH,
        description="Dirección libre",
    )
    fecha_nacimiento: date = Field(..., description="Validado por validadores")
    ocupacion: str = Field(
        ...,
        min_length=MIN_NAME_LENGTH,
        max_length=MAX_NAME_LENGTH,
        description="Texto libre",
    )

    modelo_vehiculo: str = Field(
        ...,
        min_length=1,
        max_length=MAX_NAME_LENGTH,
        description="De configuración",
    )
    concesionario: str = Field(
        ...,
        min_length=1,
        max_length=MAX_NAME_LENGTH,
        description="De configuración",
    )
    analista: str = Field(
        ...,
        min_length=1,
        max_length=MAX_NAME_LENGTH,
        description="De configuración",
    )

    # Estado - OBLIGATORIO
    estado: str = Field(
        ...,
        pattern="^(ACTIVO|INACTIVO|FINALIZADO)$",
        description="Activo/Inactivo/Finalizado",
    )

    # Notas - OPCIONAL
    notas: Optional[str] = Field(
        "NA", max_length=MAX_NOTES_LENGTH, description="Si no llena 'NA'"
    )

    @classmethod
    def validate_name_words(cls, v):
        words = v.strip().split()
        words = [word for word in words if word]  # Filtrar palabras vacías

        if len(words) < 2:
            raise ValueError("Mínimo 2 palabras requeridas")
        if len(words) > 2:
            raise ValueError("Máximo 2 palabras permitidas")

        return v

    @field_validator("notas", "direccion", mode="before")
    @classmethod
    def sanitize_html_fields(cls, v):
        if v is None or v == "":
            return "NA" if v is None else v
        return sanitize_html(v)

    @field_validator("estado", mode="before")
    @classmethod
    def normalize_estado(cls, v):
        """Normalizar estado a mayúsculas"""
        if v:
            return v.upper()
        return v


class ClienteCreate(ClienteBase):

    confirm_duplicate: bool = Field(
        False, description="Indica si el usuario confirma crear un duplicado"
    )


class ClienteCreateWithConfirmation(BaseModel):
    """Schema para crear cliente con confirmación de duplicado"""

    cliente_data: ClienteCreate
    confirmacion: bool = Field(
        True, description="Confirmación del operador"
    )
        "",
        max_length=MAX_COMMENTS_LENGTH,
    )


class ClienteUpdate(BaseModel):

    cedula: Optional[str] = Field(None, min_length=8, max_length=20)
    nombres: Optional[str] = Field(None, min_length=2, max_length=100)
    telefono: Optional[str] = Field(
        None, min_length=13, max_length=13, pattern=r"^\+58[1-9]\d{9}$"
    )
    email: Optional[EmailStr] = None
    direccion: Optional[str] = Field(None, min_length=5, max_length=500)
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = Field(None, min_length=2, max_length=100)

    modelo_vehiculo: Optional[str] = Field(None, min_length=1, max_length=100)
    concesionario: Optional[str] = Field(None, min_length=1, max_length=100)
    analista: Optional[str] = Field(None, min_length=1, max_length=100)

    # Estado
    estado: Optional[str] = Field(
        None, pattern="^(ACTIVO|INACTIVO|FINALIZADO)$"
    )
    activo: Optional[bool] = None

    # Notas
    notas: Optional[str] = Field(None, max_length=1000)

    @classmethod
    def validate_name_words(cls, v):
        if v:
            words = v.strip().split()
            words = [word for word in words if word]  # Filtrar palabras vacías

            if len(words) < 2:
                raise ValueError("Mínimo 2 palabras requeridas")
            if len(words) > 2:
                raise ValueError("Máximo 2 palabras permitidas")

        return v

    @field_validator("notas", "direccion", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_html(v)
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
    search_text: Optional[str] = Field(
        None, description="Búsqueda en nombre, cédula o móvil"
    )

    estado: Optional[str] = Field(
        None, pattern="^(ACTIVO|INACTIVO|FINALIZADO)$"
    )
    activo: Optional[bool] = None
    analista: Optional[str] = None
    concesionario: Optional[str] = None
    modelo_vehiculo: Optional[str] = None

    fecha_registro_desde: Optional[date] = None
    fecha_registro_hasta: Optional[date] = None

    # Ordenamiento
    order_by: Optional[str] = Field(
    )
    order_direction: Optional[str] = Field("asc", pattern="^(asc|desc)$")


class ClienteDetallado(ClienteResponse):
    """Cliente con información detallada"""

    # Información del analista
    analista_nombre: Optional[str] = None

    # Estadísticas

    model_config = ConfigDict(from_attributes=True)


class ClienteCreateWithLoan(ClienteBase):
    """Schema para crear cliente con préstamo automático"""


    total_financiamiento: Decimal = Field(
        ..., gt=0, description="Total del financiamiento"
    )
    cuota_inicial: Decimal = Field(default=Decimal("0.00"), ge=0)
    fecha_entrega: date = Field(
        ..., description="Fecha de entrega del vehículo"
    )
    numero_amortizaciones: int = Field(
        ..., ge=1, le=MAX_AMORTIZACIONES, description="Número de cuotas"
    )
    modalidad_pago: str = Field(
        ..., pattern="^(SEMANAL|QUINCENAL|MENSUAL|BIMENSUAL)$"
    )

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
