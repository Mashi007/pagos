"""
Modelo para reportes de pago del formulario público (módulo Cobros).
Tabla: pagos_reportados. Datos e imágenes/PDF almacenados en BD (comprobante, recibo_pdf).
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Date, LargeBinary
from sqlalchemy.sql import func

from app.core.database import Base


class PagoReportado(Base):
    __tablename__ = "pagos_reportados"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    referencia_interna = Column(String(32), nullable=False, unique=True, index=True)  # RPC-YYYYMMDD-XXXXX
    # Datos del cliente (snapshot al momento del reporte; nombres desde clientes)
    nombres = Column(String(200), nullable=False)
    apellidos = Column(String(200), nullable=False)
    tipo_cedula = Column(String(2), nullable=False)   # V, E, J
    numero_cedula = Column(String(13), nullable=False, index=True)
    fecha_pago = Column(Date, nullable=False)
    institucion_financiera = Column(String(100), nullable=False)
    numero_operacion = Column(String(100), nullable=False)
    monto = Column(Numeric(15, 2), nullable=False)
    moneda = Column(String(10), nullable=False, server_default="'BS'")  # BS, USD
    # Comprobante e imagen/PDF en BD
    comprobante = Column(LargeBinary, nullable=True)
    comprobante_nombre = Column(String(255), nullable=True)
    comprobante_tipo = Column(String(100), nullable=True)
    recibo_pdf = Column(LargeBinary, nullable=True)
    # Rutas legacy (opcionales si antes se guardaba en filesystem)
    ruta_comprobante = Column(String(512), nullable=True)
    ruta_recibo_pdf = Column(String(512), nullable=True)
    observacion = Column(Text, nullable=True)
    correo_enviado_a = Column(String(255), nullable=True)
    estado = Column(String(20), nullable=False, index=True, server_default="'pendiente'")
    motivo_rechazo = Column(Text, nullable=True)
    usuario_gestion_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    # Resultado Gemini: coincide_exacto (si True → aprobado automático)
    gemini_coincide_exacto = Column(String(10), nullable=True)  # true/false/null
    gemini_comentario = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())


class PagoReportadoHistorial(Base):
    __tablename__ = "pagos_reportados_historial"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pago_reportado_id = Column(Integer, ForeignKey("pagos_reportados.id", ondelete="CASCADE"), nullable=False, index=True)
    estado_anterior = Column(String(20), nullable=True)
    estado_nuevo = Column(String(20), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    usuario_email = Column(String(255), nullable=True)
    motivo = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
