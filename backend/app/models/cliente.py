from sqlalchemy import TIMESTAMP, Column, Date, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base

CEDULA_LENGTH = 20
NAME_LENGTH = 100
PHONE_LENGTH = 100  # Aumentado para aceptar múltiples teléfonos separados por /
EMAIL_LENGTH = 100
OCCUPATION_LENGTH = 100
STATE_LENGTH = 20
USER_LENGTH = 100


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True, nullable=False)  # FASE 1: Sincronizado con BD

    # Documento - OBLIGATORIO
    # CORREGIDO: Removido unique=True para permitir múltiples clientes con
    # misma cédula
    cedula = Column(String(CEDULA_LENGTH), nullable=False, index=True)

    nombres = Column(String(NAME_LENGTH), nullable=False)  # 2-7 palabras (nombres + apellidos unificados)
    telefono = Column(String(PHONE_LENGTH), nullable=False, index=True)  # Validado por validadores
    email = Column(String(EMAIL_LENGTH), nullable=False, index=True)  # Validado por validadores
    direccion = Column(Text, nullable=False)  # Libre
    fecha_nacimiento = Column(Date, nullable=False)  # Validado por validadores
    ocupacion = Column(String(OCCUPATION_LENGTH), nullable=False)  # Texto libre

    # Estado y control - OBLIGATORIOS
    # REGLA DE NEGOCIO ACTUALIZADA:
    # - Por defecto ACTIVO (todos los clientes nuevos)
    # - ACTIVO: Si tiene préstamo aprobado o cuotas pendientes, O tiene 3 o menos cuotas atrasadas sin pagar
    # - INACTIVO: Automático cuando tiene 4 o más cuotas atrasadas sin pagar
    # - ACTIVO: Si está al día o termina de pagar todas las cuotas (siempre permanece ACTIVO, no cambia a FINALIZADO)
    estado = Column(String(STATE_LENGTH), nullable=False, default="ACTIVO", index=True)  # ACTIVO/INACTIVO

    # Auditoría - OBLIGATORIOS
    fecha_registro = Column(
        TIMESTAMP, nullable=False, default=func.now()
    )  # Validado por validadores - Fecha de creación del cliente
    fecha_actualizacion = Column(
        TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now()
    )  # Automático - Se actualiza al editar cualquier campo
    usuario_registro = Column(String(USER_LENGTH), nullable=False)  # Email del usuario logueado (automático)

    # Notas - OBLIGATORIO con default 'NA'
    notas = Column(Text, nullable=False, default="NA")  # Obligatorio pero puede ser "NA"

    # ============================================
    # RELACIONES CON OTROS MODELOS
    # ============================================
    # NOTA: Todas las relaciones comentadas porque
    # las tablas son solo plantillas vacías
    # asesor_config_rel = relationship("Analista", back_populates="clientes")
    #                          cascade="all, delete-orphan")

    def __repr__(self):
        return (
            f"<Cliente(id={self.id}, cedula='{self.cedula}', "
            f"nombres='{self.nombres}', estado='{self.estado}')>"
        )
