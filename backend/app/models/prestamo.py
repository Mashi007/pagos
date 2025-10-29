from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Date,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.db.session import Base


class Prestamo(Base):
    __tablename__ = "prestamos"

    id = Column(Integer, primary_key=True, index=True)

    # ============================================
    # DATOS DEL CLIENTE (vinculado por cédula)
    # ============================================
    cliente_id = Column(Integer, nullable=False, index=True)  # FK a clientes.id
    cedula = Column(String(20), nullable=False, index=True)  # Cédula del cliente
    nombres = Column(String(100), nullable=False)  # Nombre del cliente

    # ============================================
    # DATOS DEL PRÉSTAMO
    # ============================================
    total_financiamiento = Column(Numeric(15, 2), nullable=False)  # Monto total
    fecha_requerimiento = Column(Date, nullable=False)  # Fecha que necesita el préstamo
    modalidad_pago = Column(String(20), nullable=False)  # MENSUAL, QUINCENAL, SEMANAL
    numero_cuotas = Column(Integer, nullable=False)  # Calculado automáticamente
    cuota_periodo = Column(
        Numeric(15, 2), nullable=False
    )  # Cuota por período según modalidad

    # Tasa de interés (0% por defecto hasta que Admin la asigne)
    tasa_interes = Column(Numeric(5, 2), nullable=False, default=0.00)
    fecha_base_calculo = Column(
        Date, nullable=True
    )  # Fecha desde la cual se genera tabla de amortizaciones

    # Producto financiero
    producto = Column(String(100), nullable=False)  # Modelo de vehículo
    producto_financiero = Column(String(100), nullable=False)  # Analista asignado

    # ============================================
    # INFORMACIÓN ADICIONAL
    # ============================================
    concesionario = Column(String(100), nullable=True)  # Concesionario
    analista = Column(String(100), nullable=True)  # Analista
    modelo_vehiculo = Column(String(100), nullable=True)  # Modelo del vehículo

    # ============================================
    # ESTADO Y APROBACIÓN
    # ============================================
    estado = Column(String(20), nullable=False, default="DRAFT", index=True)
    # DRAFT → EN_REVISION → APROBADO/RECHAZADO

    # Usuarios del proceso
    usuario_proponente = Column(String(100), nullable=False)  # Email del analista
    usuario_aprobador = Column(
        String(100), nullable=True
    )  # Email del admin (se llena al aprobar)
    usuario_autoriza = Column(
        String(100), nullable=True
    )  # Email del usuario que autoriza crear nuevo préstamo cuando ya existe uno
    observaciones = Column(Text, nullable=True)  # Observaciones de aprobación/rechazo

    # Fechas de aprobación
    fecha_registro = Column(TIMESTAMP, nullable=False, default=func.now())
    fecha_aprobacion = Column(TIMESTAMP, nullable=True)

    # ============================================
    # INFORMACIÓN COMPLEMENTARIA
    # ============================================
    informacion_desplegable = Column(
        Boolean, nullable=False, default=False
    )  # Si ha desplegado info adicional

    # Auditoría
    fecha_actualizacion = Column(
        TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return (
            f"<Prestamo(id={self.id}, cedula='{self.cedula}', "
            f"nombres='{self.nombres}', estado='{self.estado}', "
            f"total={self.total_financiamiento})>"
        )
