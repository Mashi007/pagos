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
    # ⚠️ IMPORTANTE: pagos_staging solo tiene estas columnas básicas en la BD real:
    # - id_stg (ya mapeado arriba)
    # - cedula_cliente (ya mapeado arriba)
    # - fecha_pago (TEXT en BD: 'YYYY-MM-DD HH24:MI:SS')
    # - monto_pagado (TEXT en BD)
    # - numero_documento
    # Las demás columnas NO EXISTEN en la BD real y causan errores
    fecha_pago = Column(String(50), nullable=True)  # Fecha de pago (TEXT en BD)
    monto_pagado = Column(String(50), nullable=True)  # Monto pagado (TEXT en BD)
    numero_documento = Column(String(DOCUMENTO_LENGTH), nullable=True, index=True)

    def __repr__(self):
        return f"<PagoStaging(id={self.id}, cedula={self.cedula_cliente}, monto={self.monto_pagado})>"
