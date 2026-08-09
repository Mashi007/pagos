"""
Historial de correos de un cliente.

Cada vez que cambia `clientes.email` o `clientes.email_secundario`, el valor anterior
se conserva aqui (un registro por direccion distinta por cliente). Asi la busqueda
por correo pasado o por cedula puede recuperar todos los correos conocidos.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, text

from app.core.database import Base


class ClienteEmailHistorial(Base):
    __tablename__ = "cliente_emails_historial"
    __table_args__ = (
        UniqueConstraint("cliente_id", "email_norm", name="uq_cliente_emails_historial_cliente_email"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cedula = Column(String(20), nullable=False, index=True)
    email = Column(String(150), nullable=False)
    email_norm = Column(String(150), nullable=False, index=True)
    rol = Column(String(20), nullable=False)  # principal | secundario
    registrado_en = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    usuario_cambio = Column(String(50), nullable=True)
