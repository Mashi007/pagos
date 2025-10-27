from sqlalchemy import TIMESTAMP, Column, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class PrestamoAuditoria(Base):
    """
    Auditoría completa de cambios en préstamos.
    Registra cada vez que se guarda información: fecha/usuario/campo modificado.
    """
    __tablename__ = "prestamos_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    
    # Referencia al préstamo
    prestamo_id = Column(Integer, nullable=False, index=True)
    cedula = Column(String(20), nullable=False, index=True)  # Para búsqueda rápida
    
    # Usuario que realiza el cambio
    usuario = Column(String(100), nullable=False)  # Email del usuario
    
    # Campo modificado
    campo_modificado = Column(String(100), nullable=False)  # Ej: "total_financiamiento"
    valor_anterior = Column(Text, nullable=True)  # Valor antes del cambio
    valor_nuevo = Column(Text, nullable=False)  # Valor después del cambio
    
    # Contexto del cambio
    accion = Column(String(50), nullable=False)  # "CREAR", "EDITAR", "APROBAR", "RECHAZAR", "CAMBIO_ESTADO"
    estado_anterior = Column(String(20), nullable=True)  # Si cambió el estado
    estado_nuevo = Column(String(20), nullable=True)  # Nuevo estado
    
    # Observaciones adicionales (si las hay)
    observaciones = Column(Text, nullable=True)
    
    # Fecha del cambio
    fecha_cambio = Column(TIMESTAMP, nullable=False, default=func.now())
    
    def __repr__(self):
        return (
            f"<PrestamoAuditoria(id={self.id}, prestamo_id={self.prestamo_id}, "
            f"campo='{self.campo_modificado}', accion='{self.accion}', "
            f"usuario='{self.usuario}')>"
        )
