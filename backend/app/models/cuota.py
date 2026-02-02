"""
Modelo SQLAlchemy para Cuota. Mapeado a la BD real: monto_cuota, prestamo_id;
sin columna pagado: se usa fecha_pago IS NULL para no pagada.
"""
from sqlalchemy import Column, Integer, Numeric, Date, String, ForeignKey

from app.core.database import Base


class Cuota(Base):
    __tablename__ = "cuotas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    numero_cuota = Column(Integer, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    monto = Column("monto_cuota", Numeric(14, 2), nullable=False)
    fecha_pago = Column(Date, nullable=True)
    estado = Column(String(20), nullable=False)  # BD: PAGADO, PENDIENTE, etc.; filtro "pagado" = fecha_pago IS NOT NULL
