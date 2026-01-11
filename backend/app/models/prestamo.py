from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Prestamo(Base):
    __tablename__ = "prestamos"

    id = Column(Integer, primary_key=True, index=True)

    # ============================================
    # DATOS DEL CLIENTE (vinculado por cédula)
    # ============================================
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    cedula = Column(String(20), nullable=False, index=True)  # Cédula del cliente
    nombres = Column(String(100), nullable=False)  # Nombre del cliente

    # Relación con Cliente
    cliente = relationship("Cliente", backref="prestamos")

    # ============================================
    # DATOS DEL PRÉSTAMO
    # ============================================
    valor_activo = Column(Numeric(15, 2), nullable=True)  # Valor del activo (vehículo)
    total_financiamiento = Column(Numeric(15, 2), nullable=False)  # Monto total
    fecha_requerimiento = Column(Date, nullable=False)  # Fecha que necesita el préstamo
    modalidad_pago = Column(String(20), nullable=False)  # MENSUAL, QUINCENAL, SEMANAL
    numero_cuotas = Column(Integer, nullable=False)  # Calculado automáticamente
    cuota_periodo = Column(Numeric(15, 2), nullable=False)  # Cuota por período según modalidad

    # Tasa de interés (0% por defecto hasta que Admin la asigne)
    tasa_interes = Column(Numeric(5, 2), nullable=False, default=0.00)
    fecha_base_calculo = Column(Date, nullable=True)  # Fecha desde la cual se genera tabla de amortizaciones

    # Producto financiero
    producto = Column(String(100), nullable=False)  # Modelo de vehículo
    producto_financiero = Column(String(100), nullable=False)  # Analista asignado

    # ============================================
    # INFORMACIÓN ADICIONAL
    # ============================================
    # Campos legacy (mantener para compatibilidad durante migración)
    concesionario = Column(String(100), nullable=True)  # Concesionario (legacy - usar concesionario_id)
    analista = Column(String(100), nullable=True)  # Analista (legacy - usar analista_id)
    modelo_vehiculo = Column(String(100), nullable=True)  # Modelo del vehículo (legacy - usar modelo_vehiculo_id)

    # ✅ Nuevas relaciones normalizadas
    concesionario_id = Column(Integer, ForeignKey("concesionarios.id"), nullable=True, index=True)
    analista_id = Column(Integer, ForeignKey("analistas.id"), nullable=True, index=True)
    modelo_vehiculo_id = Column(Integer, ForeignKey("modelos_vehiculos.id"), nullable=True, index=True)

    # ✅ Relaciones normalizadas con catálogos (definidas después de las columnas)
    concesionario_rel = relationship("Concesionario")
    analista_rel = relationship("Analista")
    modelo_vehiculo_rel = relationship("ModeloVehiculo")

    # ============================================
    # ESTADO Y APROBACIÓN
    # ============================================
    estado = Column(String(20), nullable=False, default="DRAFT", index=True)
    # DRAFT → EN_REVISION → APROBADO/RECHAZADO

    # Usuarios del proceso
    usuario_proponente = Column(String(100), nullable=False)  # Email del analista
    usuario_aprobador = Column(String(100), nullable=True)  # Email del admin (se llena al aprobar)
    usuario_autoriza = Column(
        String(100), nullable=True
    )  # Email del usuario que autoriza crear nuevo préstamo cuando ya existe uno
    observaciones = Column(Text, nullable=True)  # Observaciones de aprobación/rechazo

    # Fechas de aprobación
    fecha_registro = Column(
        TIMESTAMP, nullable=False, default=func.now(), index=True
    )  # INDEXADO para optimización de listado y filtros
    fecha_aprobacion = Column(TIMESTAMP, nullable=True)

    # ============================================
    # INFORMACIÓN COMPLEMENTARIA
    # ============================================
    informacion_desplegable = Column(Boolean, nullable=False, default=False)  # Si ha desplegado info adicional

    # ============================================
    # ML IMPAGO - VALORES MANUALES
    # ============================================
    ml_impago_nivel_riesgo_manual = Column(String(20), nullable=True)  # Alto, Medio, Bajo (valores manuales)
    ml_impago_probabilidad_manual = Column(Numeric(5, 3), nullable=True)  # Probabilidad manual (0.0 a 1.0)

    # ============================================
    # ML IMPAGO - VALORES CALCULADOS (persistentes)
    # ============================================
    ml_impago_nivel_riesgo_calculado = Column(String(20), nullable=True)  # Alto, Medio, Bajo (valores calculados por ML)
    ml_impago_probabilidad_calculada = Column(Numeric(5, 3), nullable=True)  # Probabilidad calculada (0.0 a 1.0)
    ml_impago_calculado_en = Column(TIMESTAMP, nullable=True)  # Fecha de última predicción calculada
    ml_impago_modelo_id = Column(Integer, ForeignKey("modelos_impago_cuotas.id"), nullable=True)  # ID del modelo ML usado

    # Auditoría
    fecha_actualizacion = Column(TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return (
            f"<Prestamo(id={self.id}, cedula='{self.cedula}', "
            f"nombres='{self.nombres}', estado='{self.estado}', "
            f"total={self.total_financiamiento})>"
        )
