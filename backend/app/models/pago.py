"""
Modelo SQLAlchemy para registro de pagos (tabla pagos).
Conectado al frontend /pagos/pagos; lista y CRUD desde BD.
Columnas alineadas con la tabla real en Render (cedula, fecha_pago timestamp, referencia_pago, etc.).
"""
import re

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Boolean, ForeignKey, Date, event
from sqlalchemy.orm import validates
from sqlalchemy.sql import func, text

from app.core.database import Base
from app.core.documento import normalize_documento
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento


class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id", ondelete="SET NULL"), nullable=True, index=True)
    # BD tiene columna "cedula"; en Python/API se expone como cedula_cliente
    cedula_cliente = Column("cedula", String(20), nullable=True, index=True)

    @validates("cedula_cliente")
    def _cedula_cliente_guardado_mayusculas(self, key, value):
        return normalizar_cedula_almacenamiento(value)

    fecha_pago = Column(DateTime(timezone=False), nullable=False)
    # Monto en USD para cartera/cuotas (si el reporte fue en Bs, se convierte con tasa del dia de fecha_pago).
    monto_pagado = Column(Numeric(14, 2), nullable=False)
    # Mismo texto de comprobante puede repetirse en varios pagos; antiduplicado operativo = huella funcional
    # (prestamo_id, fecha, monto, ref_norm) vía conflicto_huella_para_creacion / ux_pagos_fingerprint_activos.
    numero_documento = Column(String(100), nullable=True)
    institucion_bancaria = Column(String(255), nullable=True)
    estado = Column(String(30), nullable=True)
    fecha_registro = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    fecha_conciliacion = Column(DateTime(timezone=False), nullable=True)
    conciliado = Column(Boolean, nullable=False, server_default=text("false"))  # [B2] Siempre boolean, no nullable
    verificado_concordancia = Column(String(10), nullable=False, server_default=text("''"))
    usuario_registro = Column(String(255), nullable=True)
    notas = Column(Text, nullable=True)
    documento_nombre = Column(String(255), nullable=True)
    documento_tipo = Column(String(50), nullable=True)
    documento_ruta = Column(String(255), nullable=True)
    # URL del comprobante (foto/PDF en Drive u otro repositorio); import desde Excel "Link" / Gmail.
    link_comprobante = Column(Text, nullable=True)
    # NOT NULL en BD; obligatorio al insertar
    referencia_pago = Column(String(100), nullable=False, server_default=text("''"))
    # Canónicos de `normalize_documento` (Cobros: duplicados vs pagos con IN indexado; ver sql/041).
    doc_canon_numero = Column(Text, nullable=True)
    doc_canon_referencia = Column(Text, nullable=True)
    # Huella normalizada para prevenir duplicados funcionales (prestamo + fecha + monto + referencia).
    ref_norm = Column(Text, nullable=True)
    # Auditoria moneda (solo datos en BD; monto_pagado siempre USD cuando aplica conversion)
    moneda_registro = Column(String(10), nullable=True)  # USD | BS
    monto_bs_original = Column(Numeric(15, 2), nullable=True)
    tasa_cambio_bs_usd = Column(Numeric(15, 6), nullable=True)
    fecha_tasa_referencia = Column(Date, nullable=True)  # misma fecha de pago usada para buscar tasa
    # Control auditoria 5: duplicado misma fecha+monto autorizado por admin (sufijo en documento + bitacora).
    excluir_control_pagos_mismo_dia_monto = Column(
        Boolean, nullable=False, server_default=text("false")
    )



_REF_PREFIX_PATTERNS = (
    r"^(BS\.?\s*)?BNC\s*/\s*(REF\.?\s*)?",
    r"^BINANCE\s*/\s*",
    r"^BNC\s*/\s*",
    r"^VE\s*/\s*",
)


def _normalizar_referencia_pago(valor: str | None) -> str:
    raw = (valor or "").strip().upper()
    for pattern in _REF_PREFIX_PATTERNS:
        raw = re.sub(pattern, "", raw)
    return raw.strip()


@event.listens_for(Pago, "before_insert")
@event.listens_for(Pago, "before_update")
def _set_ref_norm(_mapper, _connection, target: Pago) -> None:
    # Prioriza numero_documento; si no existe usa referencia_pago.
    base = target.numero_documento or target.referencia_pago
    target.ref_norm = _normalizar_referencia_pago(base)
    target.doc_canon_numero = normalize_documento(target.numero_documento)
    target.doc_canon_referencia = normalize_documento(target.referencia_pago)
