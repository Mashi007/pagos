from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text, func  # type: ignore[import-untyped]

from app.db.session import Base

CEDULA_LENGTH = 20
DOCUMENTO_LENGTH = 100
DOCUMENTO_NOMBRE_LENGTH = 255
DOCUMENTO_TIPO_LENGTH = 10
DOCUMENTO_RUTA_LENGTH = 500
NUMERIC_PRECISION = 12
NUMERIC_SCALE = 2


class PagoStaging(Base):
    """
    Modelo para pagos_staging
    Representa pagos temporales/pre-procesamiento antes de migrar a la tabla pagos
    """

    __tablename__ = "pagos_staging"

    id = Column("id_stg", Integer, primary_key=True, index=True)  # En BD se llama id_stg

    # DATOS DEL CLIENTE
    cedula_cliente = Column(String(CEDULA_LENGTH), nullable=True, index=True)
    # ⚠️ NOTA: No hay columna 'cedula' en pagos_staging, solo 'cedula_cliente'

    # DATOS DEL PAGO
    prestamo_id = Column(Integer, nullable=True, index=True)  # ID del crédito (puede ser NULL en staging)
    numero_cuota = Column(Integer, nullable=True)  # Número de cuota asociada (opcional)
    # ⚠️ IMPORTANTE: fecha_pago y monto_pagado son TEXT en la BD real
    fecha_pago = Column(String(50), nullable=True)  # Fecha de pago (TEXT en BD: 'YYYY-MM-DD HH24:MI:SS')
    fecha_registro = Column(DateTime, default=func.now(), nullable=True, index=True)  # Fecha de registro (automático)
    monto_pagado = Column(String(50), nullable=True)  # Monto pagado (TEXT en BD, se convierte a numeric en queries)
    numero_documento = Column(String(DOCUMENTO_LENGTH), nullable=True, index=True)
    institucion_bancaria = Column(String(100), nullable=True)  # Institución bancaria

    # DOCUMENTO ADJUNTO
    documento_nombre = Column(String(DOCUMENTO_NOMBRE_LENGTH), nullable=True)
    documento_tipo = Column(String(DOCUMENTO_TIPO_LENGTH), nullable=True)  # PNG, JPG, PDF
    documento_tamaño = Column(Integer, nullable=True)  # bytes
    documento_ruta = Column(String(DOCUMENTO_RUTA_LENGTH), nullable=True)

    # ESTADO DE CONCILIACIÓN
    conciliado = Column(Boolean, default=False, nullable=True)
    fecha_conciliacion = Column(DateTime, nullable=True)

    # ESTADO DEL PAGO
    estado = Column(String(20), default="PENDIENTE", nullable=True, index=True)  # PENDIENTE, PAGADO, PARCIAL, ADELANTADO

    # CONTROL Y AUDITORÍA
    activo = Column(Boolean, default=True, nullable=True)
    notas = Column(Text, nullable=True)
    usuario_registro = Column(String(100), nullable=True)  # Email del usuario que registró el pago
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=True)

    # VERIFICACIÓN DE CONCORDANCIA
    verificado_concordancia = Column(
        String(2), default="NO", nullable=True
    )  # SI/NO - Se actualiza cuando el número de documento coincide en conciliación

    def __repr__(self):
        return f"<PagoStaging(id={self.id}, cedula={self.cedula_cliente or self.cedula}, monto={self.monto_pagado}, estado={self.estado})>"
