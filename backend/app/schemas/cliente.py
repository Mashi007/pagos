import re
from datetime import date, datetime
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
        description="2-7 palabras (nombres + apellidos unificados)",
    )
    telefono: str = Field(
        ...,
        min_length=MIN_PHONE_LENGTH,
        max_length=MAX_PHONE_LENGTH,
        description="Teléfono del cliente (formato: +58XXXXXXXXXX, 13 caracteres)",
    )

    @staticmethod
    def _validar_formato_telefono(v: str) -> str:
        """Lógica de validación de teléfono: +58 seguido de 10 dígitos, primero NO puede ser 0"""
        if not v:
            raise ValueError("Teléfono requerido")

        # Limpiar espacios
        telefono_limpio = v.strip()

        # Validar longitud exacta (13 caracteres: +58 + 10 dígitos)
        if len(telefono_limpio) != 13:
            raise ValueError(
                f"Teléfono debe tener exactamente 13 caracteres (formato: +58XXXXXXXXXX). "
                f"Recibido: {len(telefono_limpio)} caracteres"
            )

        # Validar que empiece por +58
        if not telefono_limpio.startswith("+58"):
            raise ValueError("Teléfono debe empezar por '+58'. Ejemplo: +581234567890")

        # Validar que después de +58 tenga exactamente 10 dígitos
        digitos = telefono_limpio[3:]  # Todo después de "+58"
        if not re.match(r"^[0-9]{10}$", digitos):
            raise ValueError("Después de '+58' deben ir exactamente 10 dígitos numéricos. " f"Recibido: '{digitos}'")

        # Validar que el primer dígito después de +58 NO sea 0
        if digitos[0] == "0":
            raise ValueError(
                "El primer dígito después de '+58' NO puede ser 0. " "El número debe empezar por 1-9. Ejemplo: +581234567890"
            )

        return telefono_limpio

    @field_validator("telefono", mode="before")
    @classmethod
    def validate_telefono_format(cls, v: str) -> str:
        """Validar formato de teléfono: +58 seguido de 10 dígitos, primero NO puede ser 0"""
        return cls._validar_formato_telefono(v)

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

    # Estado - OBLIGATORIO
    estado: str = Field(
        ...,
        pattern="^(ACTIVO|INACTIVO|FINALIZADO)$",
        description="Activo/Inactivo/Finalizado",
    )

    # Notas - OBLIGATORIO con default 'No hay observacion'
    notas: str = Field(
        default="No hay observacion",
        max_length=MAX_NOTES_LENGTH,
        description="Notas adicionales (default 'No hay observacion')",
    )

    @classmethod
    def validate_nombres(cls, v):
        """Validar nombres: 2-7 palabras, primera letra mayúscula"""
        if not v:
            raise ValueError("Nombres requeridos")

        words = v.strip().split()
        words = [word for word in words if word]  # Filtrar palabras vacías

        if len(words) < 2:
            raise ValueError("Mínimo 2 palabras requeridas (nombre + apellido)")
        if len(words) > 7:
            raise ValueError("Máximo 7 palabras permitidas")

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
        """Validar y formatear nombres: 2-7 palabras, primera letra mayúscula"""
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
        description="Nombres del cliente",
    )
    telefono: str = Field(
        ...,
        min_length=MIN_PHONE_LENGTH,
        max_length=MAX_PHONE_LENGTH,
        description="Teléfono",
    )
    email: EmailStr = Field(..., description="Email del cliente")
    direccion: str = Field(
        ...,
        min_length=MIN_ADDRESS_LENGTH,
        max_length=MAX_ADDRESS_LENGTH,
        description="Dirección",
    )
    fecha_nacimiento: date = Field(..., description="Fecha de nacimiento")
    ocupacion: str = Field(
        ...,
        min_length=MIN_NAME_LENGTH,
        max_length=MAX_NAME_LENGTH,
        description="Ocupación",
    )
    estado: str = Field(..., pattern="^(ACTIVO|INACTIVO|FINALIZADO)$", description="Estado del cliente")
    activo: Optional[bool] = Field(True, description="Cliente activo")
    notas: Optional[str] = Field("No hay observacion", description="Notas adicionales (default 'No hay observacion')")


class ClienteCreateWithConfirmation(BaseModel):
    """Schema para crear cliente con confirmación de duplicado"""

    cliente_data: ClienteCreate
    confirmacion: bool = Field(False, description="Confirmación de duplicado")
    comentarios: Optional[str] = Field(None, max_length=MAX_COMMENTS_LENGTH, description="Comentarios adicionales")


class ClienteUpdate(BaseModel):

    cedula: Optional[str] = Field(None, min_length=8, max_length=20)
    nombres: Optional[str] = Field(None, min_length=2, max_length=100)  # 2-7 palabras validado
    telefono: Optional[str] = Field(None, min_length=MIN_PHONE_LENGTH, max_length=MAX_PHONE_LENGTH)
    email: Optional[EmailStr] = None
    direccion: Optional[str] = Field(None, min_length=5, max_length=500)
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = Field(None, min_length=2, max_length=100)  # Max 2 palabras validado

    # Estado
    estado: Optional[str] = Field(None, pattern="^(ACTIVO|INACTIVO|FINALIZADO)$")
    activo: Optional[bool] = None

    # Notas - OBLIGATORIO con default 'No hay observacion'
    notas: Optional[str] = Field(None, max_length=1000)

    @classmethod
    def validate_nombres(cls, v):
        """Validar nombres: 2-7 palabras"""
        if v:
            words = v.strip().split()
            words = [word for word in words if word]

            if len(words) < 2:
                raise ValueError("Mínimo 2 palabras requeridas")
            if len(words) > 7:
                raise ValueError("Máximo 7 palabras permitidas")
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

    @field_validator("telefono", mode="before")
    @classmethod
    def validate_telefono_on_update(cls, v: Optional[str]) -> Optional[str]:
        """Validar formato de teléfono en actualización (si se proporciona)"""
        if v:
            # Reutilizar la lógica de validación de ClienteBase
            return ClienteBase._validar_formato_telefono(v)
        return v


class ClienteResponse(ClienteBase):
    """Schema de respuesta para cliente - Validación flexible para datos históricos"""

    id: int
    activo: bool
    usuario_registro: str  # Email del usuario que registró
    fecha_registro: Optional[datetime] = Field(None, description="Fecha de creación del cliente")
    fecha_actualizacion: Optional[datetime] = Field(None, description="Fecha de última actualización del cliente")

    # ✅ Sobrescribir campo email para permitir datos históricos con emails inválidos
    # (en lectura, aceptamos emails con errores menores para no romper datos existentes)
    email: Optional[str] = Field(
        None,
        description="Email del cliente (validación flexible para lectura de datos históricos)",
    )

    # Sobrescribir campo telefono para permitir datos históricos
    # (en lectura, aceptamos formatos no estándar para no romper datos existentes)
    telefono: str = Field(
        ...,
        min_length=10,  # Mínimo 10 caracteres (formato nacional corto)
        max_length=20,  # Máximo 20 caracteres (permite formatos variados)
        description="Teléfono del cliente (formato flexible para lectura de datos históricos)",
    )

    # ✅ Sobrescribir validador de email para permitir datos históricos
    # (en lectura, aceptamos emails con errores menores como puntos antes de @ o dobles puntos)
    @field_validator("email", mode="before")
    @classmethod
    def validate_email_response(cls, v) -> Optional[str]:
        """Validación flexible para respuestas: permite emails con errores menores"""
        if not v:
            return None
        v_str = str(v).strip()
        if not v_str:
            return None
        # Intentar limpiar errores comunes pero no rechazar el email
        # Limpiar puntos antes de @
        v_str = v_str.replace(".@", "@")
        # Limpiar dobles puntos
        v_str = v_str.replace("..", ".")
        # En respuestas, devolvemos el email (limpiado si es posible) sin validación estricta
        return v_str if v_str else None

    # Sobrescribir validador de telefono para permitir datos históricos
    # (en lectura, aceptamos formatos no estándar para no romper datos existentes)
    @field_validator("telefono", mode="before")
    @classmethod
    def validate_telefono_response(cls, v: str) -> str:
        """Validación flexible para respuestas: permite datos históricos"""
        if not v:
            return v
        # En respuestas, solo normalizamos espacios, pero no rechazamos formatos antiguos
        return v.strip()

    # Sobrescribir validador de nombres para permitir datos históricos
    # (en lectura, aceptamos nombres con más de 7 palabras para no romper datos existentes)
    @field_validator("nombres", mode="before")
    @classmethod
    def validate_nombres_response(cls, v: str) -> str:
        """Validación flexible para respuestas: permite datos históricos con más de 7 palabras"""
        if not v:
            return v
        # En respuestas, solo validamos que no esté vacío, permitimos cualquier cantidad de palabras
        # para datos históricos que no cumplen la nueva regla de máximo 7 palabras
        words = v.strip().split()
        words = [word for word in words if word]  # Filtrar palabras vacías

        if len(words) < 1:
            raise ValueError("Nombres requeridos")

        # Permitir cualquier cantidad de palabras en lectura (solo normalizar espacios)
        return " ".join(words)

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

    fecha_registro_desde: Optional[date] = None
    fecha_registro_hasta: Optional[date] = None

    # Ordenamiento
    order_by: Optional[str] = Field(None, description="Campo por el cual ordenar")
    order_direction: Optional[str] = Field("asc", pattern="^(asc|desc)$")


class ClienteDetallado(ClienteResponse):
    """Cliente con información detallada"""

    # Estadísticas

    model_config = ConfigDict(from_attributes=True)


class ClienteCreateWithLoan(ClienteBase):
    """Schema para crear cliente con préstamo automático"""

    total_financiamiento: Decimal = Field(..., description="Total del financiamiento")
    cuota_inicial: Decimal = Field(default=Decimal("0.00"), ge=0)
    fecha_entrega: date = Field(..., description="Fecha de entrega del vehículo")
    numero_amortizaciones: int = Field(..., ge=1, le=MAX_AMORTIZACIONES, description="Número de amortizaciones")
    modalidad_pago: str = Field(..., pattern="^(SEMANAL|QUINCENAL|MENSUAL|BIMENSUAL)$")

    # Configuración del préstamo
    tasa_interes_anual: Optional[Decimal] = Field(
        None,
        ge=0,
        le=MAX_TASA_INTERES,
        description="Tasa de interés anual (%)",
    )
    generar_tabla_automatica: bool = Field(True, description="Generar tabla de amortización automáticamente")


class ClienteQuickActions(BaseModel):
    """Acciones rápidas disponibles para un cliente"""

    puede_registrar_pago: bool
    puede_enviar_recordatorio: bool
    puede_generar_estado_cuenta: bool
    puede_modificar_financiamiento: bool
    puede_reasignar_analista: bool

    model_config = ConfigDict(from_attributes=True)
