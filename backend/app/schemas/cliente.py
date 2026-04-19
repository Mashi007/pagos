"""
Schemas Pydantic para Cliente (request/response).
Alineados con la tabla public.clientes en la BD.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


class ClienteBase(BaseModel):
    """Base cliente: correo 1 = prioridad (columna email), correo 2 = opcional (email_secundario)."""

    model_config = ConfigDict(populate_by_name=True)

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

    email: str = Field(
        ...,
        max_length=150,
        description="Correo 1 (prioridad). En JSON tambien se acepta la clave correo_1.",
        validation_alias=AliasChoices("email", "correo_1"),
    )
    email_secundario: Optional[str] = Field(
        None,
        max_length=150,
        description="Correo 2 (opcional). En JSON tambien se acepta la clave correo_2.",
        validation_alias=AliasChoices("email_secundario", "correo_2"),
    )
    direccion: str
    fecha_nacimiento: date
    ocupacion: str
    estado: str = "ACTIVO"
    usuario_registro: str
    notas: str

    @field_validator("email_secundario", mode="before")
    @classmethod
    def email_secundario_strip_empty(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


class ClienteCreate(ClienteBase):
    """Campos para crear cliente."""

    @model_validator(mode="after")
    def validar_emails_distintos(self):
        p = (self.email or "").strip().lower()
        s = (self.email_secundario or "").strip().lower() if self.email_secundario else ""
        if s and p and s == p:
            raise ValueError("El correo 2 no puede repetir el correo 1")
        return self


class ClienteUpdate(BaseModel):
    """Campos opcionales para actualizar. correo_1 / correo_2 son alias de email / email_secundario."""

    model_config = ConfigDict(populate_by_name=True)

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

    email: Optional[str] = Field(
        None,
        max_length=150,
        description="Correo 1 (prioridad). Alias JSON: correo_1.",
        validation_alias=AliasChoices("email", "correo_1"),
    )
    email_secundario: Optional[str] = Field(
        None,
        max_length=150,
        description="Correo 2 (opcional). Alias JSON: correo_2.",
        validation_alias=AliasChoices("email_secundario", "correo_2"),
    )
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = None
    estado: Optional[str] = None
    usuario_registro: Optional[str] = None
    notas: Optional[str] = None

    @field_validator("email_secundario", mode="before")
    @classmethod
    def email_secundario_update_strip(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @model_validator(mode="after")
    def validar_correos_distintos_update(self):
        if self.email is None or self.email_secundario is None:
            return self
        p = (self.email or "").strip().lower()
        s = (self.email_secundario or "").strip().lower()
        if s and p and s == p:
            raise ValueError("El correo 2 no puede repetir el correo 1")
        return self


class ClienteResponse(BaseModel):
    """Respuesta de cliente. correo_1 = prioridad (email en BD); correo_2 = opcional (email_secundario)."""
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
    email: str = Field("", description="Igual que correo_1 (columna email en BD).")
    email_secundario: Optional[str] = Field(None, description="Igual que correo_2 (columna email_secundario).")
    direccion: str = ""
    fecha_nacimiento: Optional[date] = None
    ocupacion: str = ""
    estado: str = "ACTIVO"
    fecha_registro: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None
    usuario_registro: str = ""
    notas: str = ""

    @computed_field
    @property
    def correo_1(self) -> str:
        """Correo con prioridad (notificaciones y envios usan esta direccion primero)."""
        return self.email or ""

    @computed_field
    @property
    def correo_2(self) -> Optional[str]:
        """Segundo correo opcional; None si no hay."""
        return self.email_secundario


class ClienteDriveImportarFilaBody(BaseModel):
    """Cuerpo para POST /clientes/drive-import/importar-fila (validación alineada a ClienteCreate)."""

    model_config = ConfigDict(extra="forbid")

    sheet_row_number: int = Field(..., ge=1)
    cedula: str
    nombres: str
    telefono: str
    email: str = Field(..., validation_alias=AliasChoices("email", "correo_1"))
    email_secundario: Optional[str] = Field(
        None, validation_alias=AliasChoices("email_secundario", "correo_2")
    )
    direccion: str
    fecha_nacimiento: date
    ocupacion: str
    estado: str = "ACTIVO"
    notas: Optional[str] = None
    comentario: Optional[str] = Field(None, description="Texto de auditoría (tabla auditoria_cliente_alta_desde_drive).")
