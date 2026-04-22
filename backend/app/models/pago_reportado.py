"""
Reportes de pago web (misma tabla para todo canal de entrada).

- Formulario publico del deudor y Infopagos escriben aqui; la cola en Cobros > Pagos reportados
  lista y gestiona todos por igual (aprobar, rechazar, editar, import a `pagos`).
- `canal_ingreso`: infopagos | cobros_publico | NULL (historico).
- Binario del comprobante: solo en `pago_comprobante_imagen` (FK `comprobante_imagen_id`);
  `comprobante_nombre` conserva el nombre original del archivo.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Date, LargeBinary
from sqlalchemy.sql import func, text

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
    comprobante_imagen_id = Column(
        String(32),
        ForeignKey("pago_comprobante_imagen.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    comprobante_nombre = Column(String(255), nullable=True)
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
    # infopagos | cobros_publico | NULL (historico u otros)
    canal_ingreso = Column(String(32), nullable=True, index=True)
    # bcv | euro | binance — tasa Bs→USD elegida al validar cédula en cobros/infopagos (defecto euro).
    fuente_tasa_cambio = Column(String(16), nullable=True, server_default=text("'euro'"))
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
