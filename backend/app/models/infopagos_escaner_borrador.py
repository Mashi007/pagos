"""
Borrador del escáner Infopagos: comprobante + cédula persistidos en BD tras extraer con Gemini.

- Se crea al terminar OK `POST /cobros/escaner/extraer-comprobante`.
- Se marca `confirmado` y se enlaza `pago_reportado_id` al registrar con
  `POST /cobros/public/infopagos/enviar-reporte` + `borrador_id` (reutiliza el mismo binario en `pago_comprobante_imagen`).
- Filas en `borrador` sin confirmar pueden limpiarse por antigüedad (operación de mantenimiento).
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.sql import func

from app.core.database import Base


class InfopagosEscanerBorrador(Base):
    __tablename__ = "infopagos_escaner_borrador"

    id = Column(String(32), primary_key=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    tipo_cedula = Column(String(2), nullable=False)
    numero_cedula = Column(String(13), nullable=False)
    cedula_normalizada = Column(String(20), nullable=False, index=True)
    fuente_tasa_cambio = Column(String(16), nullable=True)
    comprobante_imagen_id = Column(
        String(32),
        ForeignKey("pago_comprobante_imagen.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    comprobante_nombre = Column(String(255), nullable=False)
    payload_json = Column(Text, nullable=True)
    estado = Column(String(24), nullable=False, server_default=text("'borrador'"), index=True)
    pago_reportado_id = Column(
        Integer,
        ForeignKey("pagos_reportados.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())
