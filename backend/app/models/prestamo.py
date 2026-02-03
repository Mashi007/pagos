"""
Modelo SQLAlchemy para Préstamo.
Alineado con la tabla real public.prestamos (columnas confirmadas desde BD).
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, Boolean, Text
from sqlalchemy.sql import func, text

from app.core.database import Base


class Prestamo(Base):
    __tablename__ = "prestamos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    cedula = Column(String(20), nullable=False)
    nombres = Column(String(255), nullable=False)
    total_financiamiento = Column(Numeric(14, 2), nullable=False)
    fecha_requerimiento = Column(Date, nullable=False)
    modalidad_pago = Column(String(50), nullable=False)
    numero_cuotas = Column(Integer, nullable=False)
    cuota_periodo = Column(Numeric(14, 2), nullable=False)
    tasa_interes = Column(Numeric(10, 4), nullable=False, server_default=text("0.00"))
    fecha_base_calculo = Column(Date, nullable=True)
    producto = Column(String(255), nullable=False)
    estado = Column(String(50), nullable=False, index=True, server_default=text("'DRAFT'"))
    usuario_proponente = Column(String(255), nullable=False, server_default=text("'itmaster@rapicreditca.com'"))
    usuario_aprobador = Column(String(255), nullable=True)
    observaciones = Column(Text, nullable=True, server_default=text("'No observaciones'"))
    informacion_desplegable = Column(Boolean, nullable=False, server_default=text("false"))
    fecha_registro = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    fecha_aprobacion = Column(DateTime(timezone=False), nullable=True)
    fecha_actualizacion = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())
    concesionario = Column(String(255), nullable=True, index=True)
    analista = Column(String(255), nullable=False)
    modelo_vehiculo = Column(String(255), nullable=True, index=True)
    usuario_autoriza = Column(String(255), nullable=True, server_default=text("'operaciones@rapicreditca.com'"))
    ml_impago_nivel_riesgo_manual = Column(String(50), nullable=True)
    ml_impago_probabilidad_manual = Column(Numeric(10, 4), nullable=True)
    concesionario_id = Column(Integer, nullable=True)
    analista_id = Column(Integer, nullable=True)
    modelo_vehiculo_id = Column(Integer, nullable=True)
    valor_activo = Column(Numeric(14, 2), nullable=True)
    ml_impago_nivel_riesgo_calculado = Column(String(50), nullable=True)
    ml_impago_probabilidad_calculada = Column(Numeric(10, 4), nullable=True)
    ml_impago_calculado_en = Column(DateTime(timezone=False), nullable=True)
    ml_impago_modelo_id = Column(Integer, nullable=True)
    requiere_revision = Column(Boolean, nullable=False, server_default=text("false"))

    @property
    def modelo(self):
        """Alias para modelo_vehiculo (usado en listado y filtros)."""
        return self.modelo_vehiculo

    @property
    def fecha_creacion(self):
        """Alias para fecha_registro (usado en listado y respuestas)."""
        return self.fecha_registro
