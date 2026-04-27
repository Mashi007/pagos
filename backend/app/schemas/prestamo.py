"""
Schemas Pydantic para Préstamo (request/response).
Alineados con la tabla public.prestamos en la BD (columnas confirmadas).
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

PRESTAMO_ESTADOS_VALIDOS = frozenset(
    {"APROBADO", "DRAFT", "EN_REVISION", "EVALUADO", "RECHAZADO", "LIQUIDADO", "DESISTIMIENTO"}
)

def _normalizar_estado_prestamo(v):
    if not v or not str(v).strip(): return "DRAFT"
    s = str(v).strip().upper()
    if s == "PROBADO": return "APROBADO"
    if s == "RAFT": return "DRAFT"
    return s


class PrestamoBase(BaseModel):
    cliente_id: int
    total_financiamiento: Decimal
    estado: str = "DRAFT"
    concesionario: Optional[str] = None
    modelo: Optional[str] = None
    analista: str = ""
    analista_id: Optional[int] = None
    modalidad_pago: Optional[str] = None  # MENSUAL, QUINCENAL, SEMANAL
    numero_cuotas: Optional[int] = None

    @field_validator("numero_cuotas")
    @classmethod
    def numero_cuotas_rango(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 50):
            raise ValueError("numero_cuotas debe ser un entero entre 1 y 50")
        return v

    @field_validator("estado")
    @classmethod
    def estado_normalizado(cls, v: Optional[str]) -> str:
        return _normalizar_estado_prestamo(v or "DRAFT")

    # Regla de sistema: se deriva automáticamente desde fecha_aprobacion (aprobacion - 1 día).
    # Se mantiene opcional solo por compatibilidad de payloads legacy.
    fecha_requerimiento: Optional[date] = None
    cuota_periodo: Optional[Decimal] = None
    producto: Optional[str] = None


class PrestamoCreate(PrestamoBase):
    """Campos para crear préstamo. cedula/nombres se rellenan desde Cliente si no se envían."""
    # Obligatoria: no se infiere de requerimiento, fecha_registro ni fecha del servidor.
    fecha_aprobacion: date
    aprobado_por_carga_masiva: Optional[bool] = False
    # Solo cargas controladas: saltar validacion de huella duplicada (misma cedula + mismos montos/plazos que otro APROBADO).
    omitir_validacion_huella_duplicada: bool = False

    @field_validator("fecha_aprobacion", mode="before")
    @classmethod
    def fecha_aprobacion_create_resiliente(cls, v):
        if v is None or v == "":
            raise ValueError("fecha_aprobacion es obligatoria")
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            s = v.strip()
            if "T" in s:
                s = s.split("T", 1)[0]
            elif " " in s:
                s = s.split(" ", 1)[0]
            return s
        return v

class PrestamoUpdate(BaseModel):
    """Campos opcionales para actualizar."""
    cliente_id: Optional[int] = None
    total_financiamiento: Optional[Decimal] = None
    estado: Optional[str] = None
    concesionario: Optional[str] = None
    modelo: Optional[str] = None
    analista: Optional[str] = None
    analista_id: Optional[int] = None
    modalidad_pago: Optional[str] = None
    numero_cuotas: Optional[int] = None

    @field_validator("numero_cuotas")
    @classmethod
    def numero_cuotas_rango(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 50):
            raise ValueError("numero_cuotas debe ser un entero entre 1 y 50")
        return v

    @field_validator("estado")
    @classmethod
    def estado_normalizado(cls, v: Optional[str]) -> Optional[str]:
        if v is None: return None
        return _normalizar_estado_prestamo(v)

    @field_validator("fecha_requerimiento", "fecha_aprobacion", mode="before")
    @classmethod
    def parse_fechas_resiliente(cls, v):
        """
        Parsea fechas de manera resiliente.
        Acepta múltiples formatos:
        - YYYY-MM-DD (ISO)
        - DD/MM/YYYY (formato local)
        - YYYY-MM-DDTHH:MM:SS (ISO con hora)
        - date/datetime objects
        """
        if v is None or v == "":
            return v
        
        if isinstance(v, date) or isinstance(v, datetime):
            return v
        
        if isinstance(v, str):
            v = v.strip()
            
            # Si tiene hora, extraer solo fecha
            if "T" in v:
                v = v.split("T")[0]
            elif " " in v:
                v = v.split(" ")[0]
            
            # Intentar detectar y convertir DD/MM/YYYY a YYYY-MM-DD
            if "/" in v:
                try:
                    parts = v.split("/")
                    if len(parts) == 3:
                        # Asumir DD/MM/YYYY si los valores parecen serlo
                        day, month, year = parts
                        day_int = int(day)
                        month_int = int(month)
                        year_int = int(year)
                        
                        # Validación básica
                        if 1 <= day_int <= 31 and 1 <= month_int <= 12:
                            # Convertir a YYYY-MM-DD para que Pydantic lo parsee
                            v = f"{year_int:04d}-{month_int:02d}-{day_int:02d}"
                except (ValueError, IndexError):
                    pass  # Si falla, dejar el string original para que Pydantic lo intente
            
            return v  # Pydantic parseará el string correctamente
        
        return v

    fecha_requerimiento: Optional[date] = None
    fecha_aprobacion: Optional[datetime] = None
    cuota_periodo: Optional[Decimal] = None
    producto: Optional[str] = None
    valor_activo: Optional[Decimal] = None
    observaciones: Optional[str] = None
    fecha_base_calculo: Optional[date] = None
    tasa_interes: Optional[Decimal] = None

    @field_validator("tasa_interes")
    @classmethod
    def tasa_interes_solo_cero(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is None:
            return v
        dec = v if isinstance(v, Decimal) else Decimal(str(v))
        if dec.copy_abs() > Decimal("0"):
            raise ValueError(
                "tasa_interes debe ser 0. El producto no admite variación de tasa de interés."
            )
        return Decimal("0")


class PrestamoResponse(BaseModel):
    """Respuesta de préstamo (columnas de la tabla prestamos)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    total_financiamiento: Decimal
    estado: str = "DRAFT"
    estado_gestion_finiquito: Optional[str] = None
    # Plazo visible cuando EN_PROCESO (15 dias laborales lun-vie desde el cambio, Caracas).
    finiquito_tramite_fecha_limite: Optional[date] = None
    concesionario: Optional[str] = None
    modelo: Optional[str] = None
    analista: Optional[str] = None
    analista_id: Optional[int] = None
    modalidad_pago: Optional[str] = None
    numero_cuotas: Optional[int] = None
    fecha_creacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None
    fecha_registro: Optional[datetime] = None
    fecha_aprobacion: Optional[datetime] = None
    # Campos para detalle (cedula/nombres en prestamos; cuota_periodo, etc.)
    cedula: Optional[str] = None
    nombres: Optional[str] = None
    cuota_periodo: Optional[Decimal] = None
    fecha_requerimiento: Optional[date] = None
    fecha_base_calculo: Optional[date] = None  # Amortizacion: misma fecha calendario que fecha_aprobacion (formularios muestran aprobacion; BD usa base para calculo)
    tasa_interes: Optional[Decimal] = Decimal("0.00")  # Siempre 0% por defecto (producto sin interés)
    producto: Optional[str] = None
    valor_activo: Optional[Decimal] = None
    observaciones: Optional[str] = None
    # Fecha calendario (Caracas) en que el prestamo paso a DESISTIMIENTO; inmutable mientras siga en ese estado.
    fecha_desistimiento: Optional[date] = None


class PrestamoListResponse(PrestamoResponse):
    """Préstamo para listado: incluye nombres y cedula del cliente (join)."""
    nombres: Optional[str] = None
    cedula: Optional[str] = None
    fecha_registro: Optional[datetime] = None
    numero_cuotas: Optional[int] = None
    modalidad_pago: Optional[str] = None
    revision_manual_estado: Optional[str] = None  # pendiente | revisando | revisado (None si no tiene)
    # Suma por fila de amortización: max(0, monto - total_pagado); alineado con «Total pendiente pagar» del modal.
    saldo_pendiente: Decimal = Decimal("0")
    # Cuotas contadas como pagadas (misma regla que chip «Pagadas» en tabla de amortización del modal).
    cuotas_pagadas_listado: Optional[int] = None
