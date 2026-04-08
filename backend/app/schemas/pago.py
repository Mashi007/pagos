"""
Schemas Pydantic para Pago (registro de pagos). Alineados con el frontend.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, field_validator

from app.core.documento import normalize_codigo_documento

# Misma zona que `TZ_NEGOCIO` en endpoints de pagos (fecha calendario del negocio).
TZ_PAGO_CARACAS = "America/Caracas"

# Límite de INTEGER en PostgreSQL (evita 500 cuando se envía número de documento como prestamo_id)
PRESTAMO_ID_MAX = 2147483647


def normalizar_link_comprobante(v: Any) -> Optional[str]:
    """URL publica del comprobante; acepta id de archivo Drive sin prefijo (misma regla que Excel Gmail)."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    if not s.startswith(("http://", "https://")):
        s = "https://drive.google.com/file/d/" + s + "/view"
    return s


class PagoCreate(BaseModel):
    cedula_cliente: str
    prestamo_id: Optional[int] = None
    fecha_pago: date
    monto_pagado: Decimal
    numero_documento: str  # Comprobante visible; con codigo_documento compone clave única en BD.
    codigo_documento: Optional[str] = None  # Opcional: desambigua mismo comprobante (p. ej. cuota/lote).
    institucion_bancaria: Optional[str] = None
    notas: Optional[str] = None
    conciliado: Optional[bool] = None  # Sí/No en carga masiva
    # USD (defecto): monto_pagado en dolares. BS: monto_pagado en bolivares; requiere autorizacion lista Bs + tasa (BD o manual).
    moneda_registro: Optional[str] = "USD"
    tasa_cambio_manual: Optional[Decimal] = None  # Solo si no hay tasa en BD para fecha_pago
    link_comprobante: Optional[str] = None

    @field_validator("link_comprobante", mode="before")
    @classmethod
    def link_comprobante_normalizado(cls, v: object) -> Optional[str]:
        return normalizar_link_comprobante(v)

    @field_validator("numero_documento", mode="before")
    @classmethod
    def numero_documento_cualquier_formato(cls, v: object) -> str:
        """Documento obligatorio para candado antifraude; se normaliza a string."""
        if v is None:
            raise ValueError("numero_documento es obligatorio")
        s = str(v).strip()
        if not s:
            raise ValueError("numero_documento es obligatorio")
        return s

    @field_validator("codigo_documento", mode="before")
    @classmethod
    def codigo_documento_opcional(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        return normalize_codigo_documento(s)

    @field_validator("prestamo_id")
    @classmethod
    def prestamo_id_en_rango(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v < 1 or v > PRESTAMO_ID_MAX:
            raise ValueError(
                f"prestamo_id debe estar entre 1 y {PRESTAMO_ID_MAX}. "
                "Si el valor parece un número de documento (ej. 740087408451411), elija el crédito correcto en la lista."
            )
        return v



    @field_validator("moneda_registro", mode="before")
    @classmethod
    def moneda_registro_opcional(cls, v: object) -> Optional[str]:
        if v is None or v == "":
            return "USD"
        return str(v).strip().upper()


class PagoUpdate(BaseModel):
    cedula_cliente: Optional[str] = None
    prestamo_id: Optional[int] = None
    fecha_pago: Optional[date] = None
    monto_pagado: Optional[Decimal] = None
    numero_documento: Optional[str] = None
    codigo_documento: Optional[str] = None
    institucion_bancaria: Optional[str] = None
    notas: Optional[str] = None
    conciliado: Optional[bool] = None
    verificado_concordancia: Optional[str] = None  # SI / NO
    moneda_registro: Optional[str] = None
    tasa_cambio_manual: Optional[Decimal] = None
    link_comprobante: Optional[str] = None

    @field_validator("link_comprobante", mode="before")
    @classmethod
    def link_comprobante_normalizado_upd(cls, v: object) -> Optional[str]:
        return normalizar_link_comprobante(v)

    @field_validator("numero_documento", mode="before")
    @classmethod
    def numero_documento_cualquier_formato(cls, v: object) -> Optional[str]:
        """Si se envia, debe contener valor no vacio."""
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            raise ValueError("numero_documento no puede estar vacio")
        return s

    @field_validator("codigo_documento", mode="before")
    @classmethod
    def codigo_documento_opcional_upd(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        return normalize_codigo_documento(s)

    @field_validator("prestamo_id")
    @classmethod
    def prestamo_id_en_rango(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v < 1 or v > PRESTAMO_ID_MAX:
            raise ValueError(
                f"prestamo_id debe estar entre 1 y {PRESTAMO_ID_MAX}. "
                "Si el valor parece un número de documento, elija el crédito correcto."
            )
        return v


class PagoResponse(BaseModel):
    """Respuesta de un pago (para GET por id y para items de lista)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cedula_cliente: str
    prestamo_id: Optional[int] = None
    fecha_pago: date
    monto_pagado: Decimal
    numero_documento: str
    codigo_documento: Optional[str] = ""
    institucion_bancaria: Optional[str] = None
    estado: str
    fecha_registro: Optional[datetime] = None
    fecha_conciliacion: Optional[datetime] = None
    conciliado: bool = False
    verificado_concordancia: Optional[str] = None
    usuario_registro: Optional[str] = None
    notas: Optional[str] = None
    documento_nombre: Optional[str] = None
    documento_tipo: Optional[str] = None
    documento_ruta: Optional[str] = None
    link_comprobante: Optional[str] = None
    cuotas_atrasadas: Optional[int] = None  # calculado en listado
    moneda_registro: Optional[str] = None
    monto_bs_original: Optional[Decimal] = None
    tasa_cambio_bs_usd: Optional[Decimal] = None
    fecha_tasa_referencia: Optional[date] = None
