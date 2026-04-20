"""Registro de envíos del submódulo Recibos (estado de cuenta por cédula tras pagos conciliados)."""

from sqlalchemy import Column, Date, DateTime, Integer, String, UniqueConstraint, func

from app.core.database import Base


class RecibosEmailEnvio(Base):
    """
    Evita reenviar el mismo lote: una fila por (cédula normalizada, día Caracas de corte, slot).
    Slot actual típico: ``dia_00_2345`` (ventana ``fecha_registro`` ese día Caracas 00:00–23:45).
    Puede existir histórico ``hasta_15_24h`` (regla anterior); el backend los trata como envío ya cubierto.
    """

    __tablename__ = "recibos_email_envio"
    __table_args__ = (
        UniqueConstraint(
            "cedula_normalizada",
            "fecha_dia",
            "slot",
            name="uq_recibos_email_envio_cedula_dia_slot",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    cedula_normalizada = Column(String(32), nullable=False, index=True)
    fecha_dia = Column(Date, nullable=False, index=True)
    slot = Column(String(16), nullable=False)
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
