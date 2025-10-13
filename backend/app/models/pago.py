# backend/app/models/pago.py
from sqlalchemy import Column, Integer, String, Date, Time, TIMESTAMP, Numeric, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base  # ✅ CORRECTO


class Pago(Base):
    __tablename__ = "pagos"
    
    id = Column(Integer, primary_key=True, index=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False)
    
    # Información del pago
    numero_cuota = Column(Integer, nullable=False)
    codigo_pago = Column(String(30), unique=True, index=True)
    
    # Montos
    monto_cuota_programado = Column(Numeric(12, 2), nullable=False)
    monto_pagado = Column(Numeric(12, 2), nullable=False)
    monto_capital = Column(Numeric(12, 2), default=0.00)
    monto_interes = Column(Numeric(12, 2), default=0.00)
    monto_mora = Column(Numeric(12, 2), default=0.00)
    descuento = Column(Numeric(12, 2), default=0.00)
    monto_total = Column(Numeric(12, 2), nullable=False)
    
    # Fechas
    fecha_pago = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    hora_pago = Column(Time, server_default=func.current_time())
    
    # Mora
    dias_mora = Column(Integer, default=0)
    tasa_mora = Column(Numeric(5, 2), default=0.00)
    
    # Pago
    metodo_pago = Column(String(20), default="EFECTIVO")
    numero_operacion = Column(String(50))
    comprobante = Column(String(50))
    banco = Column(String(50))
    
    # Estado
    estado = Column(String(20), default="CONFIRMADO", index=True)  # CONFIRMADO, PENDIENTE, ANULADO
    tipo_pago = Column(String(20), default="NORMAL")  # NORMAL, PARCIAL, ADELANTO
    
    # Conciliación bancaria
    estado_conciliacion = Column(String(20), default="PENDIENTE")  # PENDIENTE, CONCILIADO, RECHAZADO
    fecha_conciliacion = Column(Date, nullable=True)
    referencia_bancaria = Column(String(100), nullable=True)
    
    # Información adicional
    observaciones = Column(Text)
    usuario_registro = Column(String(50))
    
    # Control de anulación
    anulado = Column(Boolean, default=False)
    fecha_anulacion = Column(TIMESTAMP, nullable=True)
    usuario_anulacion = Column(String(50), nullable=True)
    justificacion_anulacion = Column(Text, nullable=True)
    
    # Auditoría
    creado_en = Column(TIMESTAMP, server_default=func.now())
    actualizado_en = Column(TIMESTAMP, nullable=True, onupdate=func.now())
    
    # Relaciones
    prestamo = relationship("Prestamo", back_populates="pagos")
    cuotas = relationship(
        "Cuota",
        secondary="pago_cuotas",
        back_populates="pagos",
        overlaps="pagos,cuota"
    )
    
    def __repr__(self):
        return f"<Pago {self.codigo_pago} - ${self.monto_pagado} - {self.estado}>"
    
    @property
    def esta_anulado(self) -> bool:
        """Verifica si el pago está anulado"""
        return self.anulado or self.estado == "ANULADO"
    
    @property
    def esta_conciliado(self) -> bool:
        """Verifica si el pago está conciliado"""
        return self.estado_conciliacion == "CONCILIADO"
    
    @property
    def tiene_mora(self) -> bool:
        """Verifica si el pago incluye mora"""
        return self.monto_mora > 0
    
    def anular(self, usuario: str, justificacion: str):
        """Anula el pago"""
        from datetime import datetime
        self.anulado = True
        self.estado = "ANULADO"
        self.fecha_anulacion = datetime.now()
        self.usuario_anulacion = usuario
        self.justificacion_anulacion = justificacion
    
    def generar_codigo_pago(self) -> str:
        """Genera código único de pago"""
        from datetime import datetime
        fecha_str = datetime.now().strftime("%Y%m%d")
        return f"PAG-{fecha_str}-{self.id:04d}"
