"""
Destinatarios seleccionados por campaña CRM.
Si la campaña tiene filas aquí: se envía solo a esos clientes. Si no: a todos (emails de clientes).
"""
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint

from app.core.database import Base


class CampanaDestinatarioCrm(Base):
    __tablename__ = "crm_campana_destinatario"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campana_id = Column(Integer, ForeignKey("crm_campana.id", ondelete="CASCADE"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (UniqueConstraint("campana_id", "cliente_id", name="uq_crm_campana_dest_campana_cliente"),)
