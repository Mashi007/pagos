# backend/app/models/cliente.py
from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, Text, Boolean, Numeric, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base  # ✅ CORRECTO

class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Documento
    cedula = Column(String(20), unique=True, nullable=False, index=True)
    
    # Datos personales
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    telefono = Column(String(15), nullable=True, index=True)  # ✅ Agregado índice para búsqueda
    email = Column(String(100), nullable=True, index=True)   # ✅ Agregado índice para búsqueda
    direccion = Column(Text, nullable=True)
    fecha_nacimiento = Column(Date, nullable=True)
    ocupacion = Column(String(100), nullable=True)
    
    # ============================================
    # DATOS DE FINANCIAMIENTO (NUEVOS)
    # ============================================
    modelo_vehiculo = Column(String(100), nullable=True, index=True)
    concesionario = Column(String(100), nullable=True, index=True)
    total_financiamiento = Column(Numeric(12, 2), nullable=True)
    cuota_inicial = Column(Numeric(12, 2), default=0.00)
    fecha_entrega = Column(Date, nullable=True, comment="Fecha de entrega del vehículo (inicio amortización)")
    numero_amortizaciones = Column(Integer, nullable=True)
    modalidad_financiamiento = Column(String(20), nullable=True, default="MENSUAL", index=True)  # SEMANAL/QUINCENAL/MENSUAL
    
    # ============================================
    # ASIGNACIÓN (NUEVO)
    # ============================================
    asesor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Estado - CON VALORES POR DEFECTO
    estado = Column(String(20), nullable=False, default="ACTIVO", server_default="ACTIVO", index=True)
    activo = Column(Boolean, nullable=False, default=True, server_default="true")
    
    # ============================================
    # CAMPOS CALCULADOS (NUEVOS)
    # ============================================
    # Estos se calcularán dinámicamente pero los agregamos para índices
    dias_mora = Column(Integer, default=0, index=True)
    saldo_pendiente_total = Column(Numeric(12, 2), default=0.00)
    
    # Auditoría
    fecha_registro = Column(TIMESTAMP, nullable=False, server_default=func.now())
    fecha_actualizacion = Column(TIMESTAMP, nullable=True, onupdate=func.now())
    usuario_registro = Column(String(50), nullable=True)
    
    # Notas
    notas = Column(Text, nullable=True)
    
    # Relaciones
    prestamos = relationship("Prestamo", back_populates="cliente")
    notificaciones = relationship("Notificacion", back_populates="cliente")
    asesor = relationship("User", foreign_keys=[asesor_id], back_populates="clientes_asignados")
    
    def __repr__(self):
        return f"<Cliente {self.nombres} {self.apellidos} - {self.cedula}>"
    
    # ============================================
    # PROPIEDADES CALCULADAS (NUEVAS)
    # ============================================
    @property
    def nombre_completo(self) -> str:
        """Retorna el nombre completo del cliente"""
        return f"{self.nombres} {self.apellidos}"
    
    @property
    def monto_financiado(self) -> float:
        """Calcula el monto financiado (total - cuota inicial)"""
        if self.total_financiamiento and self.cuota_inicial:
            return float(self.total_financiamiento - self.cuota_inicial)
        return float(self.total_financiamiento or 0)
    
    @property
    def tiene_prestamos_activos(self) -> bool:
        """Verifica si tiene préstamos activos"""
        return any(p.estado in ["ACTIVO", "EN_MORA"] for p in self.prestamos)
    
    @property
    def estado_mora(self) -> str:
        """Calcula el estado de mora del cliente"""
        if not self.prestamos:
            return "SIN_PRESTAMOS"
        
        prestamos_activos = [p for p in self.prestamos if p.estado in ["ACTIVO", "EN_MORA"]]
        if not prestamos_activos:
            return "AL_DIA"
        
        max_dias_mora = max((p.dias_mora or 0) for p in prestamos_activos)
        
        if max_dias_mora == 0:
            return "AL_DIA"
        elif max_dias_mora <= 30:
            return "MORA_TEMPRANA"
        elif max_dias_mora <= 90:
            return "MORA_MEDIA"
        else:
            return "MORA_CRITICA"
