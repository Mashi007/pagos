from sqlalchemy import TIMESTAMP, Boolean, Column, Date, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base

# Constantes de longitud de campos
CEDULA_LENGTH = 20
NAME_LENGTH = 100
PHONE_LENGTH = 15
EMAIL_LENGTH = 100
OCCUPATION_LENGTH = 100
VEHICLE_MODEL_LENGTH = 100
DEALER_LENGTH = 100
ANALYST_LENGTH = 100
STATE_LENGTH = 20
USER_LENGTH = 100


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)

    # Documento - OBLIGATORIO
    # CORREGIDO: Removido unique=True para permitir múltiples clientes con
    # misma cédula
    cedula = Column(String(CEDULA_LENGTH), nullable=False, index=True)

    # Datos personales - OBLIGATORIOS
    nombres = Column(String(NAME_LENGTH), nullable=False)  # 1-2 palabras \
    máximo
    apellidos = Column(String(NAME_LENGTH), nullable=False)  # 1-2 palabras máximo
    telefono = Column(
        String(PHONE_LENGTH), nullable=False, index=True
    )  # Validado por validadores
    email = Column(
        String(EMAIL_LENGTH), nullable=False, index=True
    )  # Validado por validadores
    direccion = Column(Text, nullable=False)  # Libre
    fecha_nacimiento = Column(Date, nullable=False)  # Validado por validadores
    ocupacion = Column(String(OCCUPATION_LENGTH), nullable=False)  # Texto libre

    # ============================================
    # DATOS DEL VEHÍCULO Y FINANCIAMIENTO - OBLIGATORIOS
    # ============================================
    # Campos de configuración necesarios para formulario y Excel
    modelo_vehiculo = Column(
        String(VEHICLE_MODEL_LENGTH), nullable=False, index=True
    )  # Configuración
    concesionario = Column(
        String(DEALER_LENGTH), nullable=False, index=True
    )  # Configuración
    analista = Column(
        String(ANALYST_LENGTH), nullable=False, index=True
    )  # Configuración

    # Estado y control - OBLIGATORIOS
    estado = Column(
        String(STATE_LENGTH), nullable=False, default="ACTIVO", index=True
    )  # Activo/Inactivo/Finalizado
    activo = Column(Boolean, nullable=False, default=True, index=True)

    # Auditoría - OBLIGATORIOS
    fecha_registro = Column(
        TIMESTAMP, nullable=False, default=func.now()
    )  # Validado por validadores
    fecha_actualizacion = Column(
        TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now()
    )  # Automático
    usuario_registro = Column(
        String(USER_LENGTH), nullable=False
    )  # Email del usuario logueado (automático)

    # Notas - OPCIONAL
    notas = Column(Text, nullable=True, default="NA")  # Si no llena "NA"

    # ============================================
    # RELACIONES CON OTROS MODELOS
    # ============================================
    # NOTA: Todas las relaciones comentadas porque las tablas son solo plantillas vacías
    # asesor_config_rel = relationship("Analista", back_populates="clientes")
    # prestamos = relationship("Prestamo", back_populates="cliente", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Cliente(id={self.id}, cedula='{self.cedula}', nombres='{self.nombres}', apellidos='{self.apellidos}')>"
