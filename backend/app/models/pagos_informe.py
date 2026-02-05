"""
Modelo para digitalización de papeletas (OCR): cedula, fecha, banco, numero_deposito, cantidad, link_imagen.
Se vuelca a Google Sheets por periodo (6am, 1pm, 4h30).
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import text

from app.core.database import Base


class PagosInforme(Base):
    __tablename__ = "pagos_informes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cedula = Column(String(20), nullable=False, index=True)
    fecha_deposito = Column(String(50), nullable=True)
    nombre_banco = Column(String(255), nullable=True)
    numero_deposito = Column(String(100), nullable=True)
    numero_documento = Column(String(100), nullable=True)  # Nº doc/recibo; formato variable (números, letras o mixto); se ubica por palabras clave configurables
    cantidad = Column(String(50), nullable=True)
    humano = Column(String(20), nullable=True)  # "HUMANO" cuando >80% del texto es de baja confianza (manuscrito/ilegible); no se inventan datos
    link_imagen = Column(Text, nullable=False)
    observacion = Column(Text, nullable=True)
    pagos_whatsapp_id = Column(Integer, ForeignKey("pagos_whatsapp.id", ondelete="SET NULL"), nullable=True)
    periodo_envio = Column(String(20), nullable=False, index=True)
    fecha_informe = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    # Columnas alineadas con Google Sheets G, H, J (I = fecha_informe)
    nombre_cliente = Column(String(255), nullable=True)
    estado_conciliacion = Column(String(50), nullable=True)  # CONCILIADO, REVISAR, REVISAR_MONTO
    telefono = Column(String(30), nullable=True, index=True)
