"""
KPIs permanentes del escaneo de rebotes Gmail.
Tabla singleton: auditoria_rebotes_gmail_kpis (id=1). No se limpia al borrar el detalle.
"""
from sqlalchemy import BigInteger, Column, DateTime, SmallInteger, text

from app.core.database import Base


class AuditoriaReboteGmailKpi(Base):
    __tablename__ = "auditoria_rebotes_gmail_kpis"

    id = Column(SmallInteger, primary_key=True, default=1)
    total_escaneados = Column(BigInteger, nullable=False, server_default=text("0"))
    total_guardados = Column(BigInteger, nullable=False, server_default=text("0"))
    total_omitidos = Column(BigInteger, nullable=False, server_default=text("0"))
    total_sin_correo = Column(BigInteger, nullable=False, server_default=text("0"))
    total_sin_cedula = Column(BigInteger, nullable=False, server_default=text("0"))
    total_cedula_duplicada = Column(BigInteger, nullable=False, server_default=text("0"))
    total_ya_existentes = Column(BigInteger, nullable=False, server_default=text("0"))
    total_mal = Column(BigInteger, nullable=False, server_default=text("0"))
    total_lleno = Column(BigInteger, nullable=False, server_default=text("0"))
    total_temporal = Column(BigInteger, nullable=False, server_default=text("0"))
    total_otro = Column(BigInteger, nullable=False, server_default=text("0"))
    total_corridas = Column(BigInteger, nullable=False, server_default=text("0"))
    ultima_corrida_at = Column(DateTime(timezone=False), nullable=True)
    actualizado_en = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
