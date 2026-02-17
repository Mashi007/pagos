"""
Schemas Pydantic para Cliente (request/response).
Alineados con la tabla public.clientes en la BD.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ClienteBase(BaseModel):
    cedula: str

    @field_validator("cedula", mode="before")
    @classmethod
    def cedula_empty_default(cls, v: str) -> str:
        """Celda vacía → Z999999999 por defecto."""
        if v is None:
            return "Z999999999"
        s = str(v).strip()
        return s if s else "Z999999999"

    nombres: str

    @field_validator("nombres", mode="before")
    @classmethod
    def nombres_empty_default(cls, v: str) -> str:
        """Si está vacío → "Revisar Nombres"."""
        if v is None:
            return "Revisar Nombres"
        s = str(v).strip()
        return s if s else "Revisar Nombres"

    telefono: str

    @field_validator("telefono", mode="before")
    @classmethod
    def telefono_10_digitos(cls, v: str) -> str:
        """Formato: 10 dígitos, primer dígito 1-9. Si vacío o no cumple formato → +589999999999."""
        if v is None or not str(v).strip():
            return "+589999999999"
        import re
        digits = re.sub(r"\D", "", str(v).strip())
        if digits.startswith("58") and len(digits) > 10:
            digits = digits[2:]
        if not digits or len(digits) != 10 or not re.match(r"^[1-9]\d{9}$", digits):
            return "+589999999999"
        return "+58" + digits
    email: str
    direccion: str
    fecha_nacimiento: date
    ocupacion: str
    estado: str = "ACTIVO"
    usuario_registro: str
    notas: str


class ClienteCreate(ClienteBase):
    """Campos para crear cliente."""


class ClienteUpdate(BaseModel):
    """Campos opcionales para actualizar."""
    cedula: Optional[str] = None
    nombres: Optional[str] = None

    @field_validator("nombres", mode="before")
    @classmethod
    def nombres_empty_default(cls, v: str) -> Optional[str]:
        """Si se envía vacío → "Revisar Nombres"."""
        if v is None:
            return None
        s = str(v).strip()
        return "Revisar Nombres" if not s else s

    telefono: Optional[str] = None

    @field_validator("telefono", mode="before")
    @classmethod
    def telefono_10_digitos(cls, v: str) -> Optional[str]:
        """Si se envía vacío o no cumple formato (10 dígitos, 1-9 inicial) → +589999999999."""
        if v is None:
            return None
        import re
        digits = re.sub(r"\D", "", str(v).strip())
        if digits.startswith("58") and len(digits) > 10:
            digits = digits[2:]
        if not digits or len(digits) != 10 or not re.match(r"^[1-9]\d{9}$", digits):
            return "+589999999999"
        return "+58" + digits

    email: Optional[str] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = None
    estado: Optional[str] = None
    usuario_registro: Optional[str] = None
    notas: Optional[str] = None


class ClienteResponse(BaseModel):
    """Respuesta de cliente (columnas de la tabla clientes). Tolerante a NULLs en BD."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cedula: str = ""
    nombres: str = ""

    @field_validator("nombres", mode="before")
    @classmethod
    def nombres_empty_default(cls, v: str) -> str:
        """Si está vacío → "Revisar Nombres"."""
        if v is None or not str(v).strip():
            return "Revisar Nombres"
        return str(v).strip()
    telefono: str = ""
    email: str = ""
    direccion: str = ""
    fecha_nacimiento: Optional[date] = None
    ocupacion: str = ""
    estado: str = "ACTIVO"
    fecha_registro: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None
    usuario_registro: str = ""
    notas: str = ""
