# backend/app/models/amortizacion.py
"""
Modelo de Cuota/Amortización
Representa cada cuota de un préstamo con su detalle de capital, interés y saldos
"""
from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey, DateTime, Boolean, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal

from app.db.base import Base


class Cuota(Base):
    """
    Modelo de Cuota de Préstamo
    Cada registro representa una cuota en la tabla de amortización
    """
    __tablename__ = "cuotas"
    
    # Identificación
    id = Column(Integer, primary_key=True, index=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id", ondelete="CASCADE"), nullable=False, index=True)
    numero_cuota = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    
    # Fechas
    fecha_vencimiento = Column(Date, nullable=False, index=True)
    fecha_pago = Column(Date, nullable=True)  # Fecha real de pago
    
    # Montos originales (plan de amortización)
    monto_cuota = Column(Numeric(12, 2), nullable=False)
    monto_capital = Column(Numeric(12, 2), nullable=False)
    monto_interes = Column(Numeric(12, 2), nullable=False)
    
    # Saldos
    saldo_capital_inicial = Column(Numeric(12, 2), nullable=False)  # Saldo al inicio del período
    saldo_capital_final = Column(Numeric(12, 2), nullable=False)    # Saldo al fin del período
    
    # Pagos realizados
    capital_pagado = Column(Numeric(12, 2), default=Decimal("0.00"))
    interes_pagado = Column(Numeric(12, 2), default=Decimal("0.00"))
    mora_pagada = Column(Numeric(12, 2), default=Decimal("0.00"))
    total_pagado = Column(Numeric(12, 2), default=Decimal("0.00"))
    
    # Saldos pendientes
    capital_pendiente = Column(Numeric(12, 2), nullable=False)  # Capital que falta pagar de esta cuota
    interes_pendiente = Column(Numeric(12, 2), nullable=False)  # Interés que falta pagar de esta cuota
    
    # Mora
    dias_mora = Column(Integer, default=0)
    monto_mora = Column(Numeric(12, 2), default=Decimal("0.00"))
    tasa_mora = Column(Numeric(5, 2), default=Decimal("0.00"))  # Tasa de mora aplicada (%)
    
    # Estado
    estado = Column(
        String(20),
        nullable=False,
        default="PENDIENTE",
        index=True
    )  # PENDIENTE, PAGADA, VENCIDA, PARCIAL
    
    # Información adicional
    observaciones = Column(String(500), nullable=True)
    es_cuota_especial = Column(Boolean, default=False)  # Para cuotas con montos diferentes
    
    # Auditoría
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    prestamo = relationship("Prestamo", back_populates="cuotas")
    pagos = relationship(
        "Pago",
        secondary="pago_cuotas",
        back_populates="cuotas",
        overlaps="cuotas,pago"
    )
    
    def __repr__(self):
        return f"<Cuota {self.numero_cuota} - Préstamo {self.prestamo_id} - {self.estado}>"
    
    @property
    def esta_vencida(self) -> bool:
        """Verifica si la cuota está vencida"""
        from datetime import date
        if self.estado == "PAGADA":
            return False
        return date.today() > self.fecha_vencimiento
    
    @property
    def monto_pendiente_total(self) -> Decimal:
        """Calcula el monto total pendiente (capital + interés + mora)"""
        return self.capital_pendiente + self.interes_pendiente + self.monto_mora
    
    @property
    def porcentaje_pagado(self) -> Decimal:
        """Calcula el porcentaje pagado de la cuota"""
        if self.monto_cuota == 0:
            return Decimal("0")
        return (self.total_pagado / self.monto_cuota) * Decimal("100")
    
    def calcular_mora(self, tasa_mora_diaria: Decimal) -> Decimal:
        """
        Calcula el monto de mora acumulado
        
        Args:
            tasa_mora_diaria: Tasa de mora diaria (%)
            
        Returns:
            Decimal: Monto de mora calculado
        """
        from datetime import date
        
        if self.estado == "PAGADA" or not self.esta_vencida:
            return Decimal("0.00")
        
        dias_mora = (date.today() - self.fecha_vencimiento).days
        if dias_mora <= 0:
            return Decimal("0.00")
        
        # Mora sobre el capital pendiente
        mora = self.capital_pendiente * (tasa_mora_diaria / Decimal("100")) * Decimal(dias_mora)
        
        return mora.quantize(Decimal("0.01"))
    
    def aplicar_pago(self, monto_pago: Decimal) -> dict:
        """
        Aplica un pago a la cuota siguiendo el orden: mora -> interés -> capital
        
        Args:
            monto_pago: Monto del pago a aplicar
            
        Returns:
            dict: Detalle de cómo se aplicó el pago
        """
        detalle = {
            "mora_aplicada": Decimal("0.00"),
            "interes_aplicado": Decimal("0.00"),
            "capital_aplicado": Decimal("0.00"),
            "sobrante": Decimal("0.00")
        }
        
        saldo = monto_pago
        
        # 1. Aplicar a mora
        if saldo > 0 and self.monto_mora > 0:
            aplicado_mora = min(saldo, self.monto_mora)
            self.mora_pagada += aplicado_mora
            self.monto_mora -= aplicado_mora
            detalle["mora_aplicada"] = aplicado_mora
            saldo -= aplicado_mora
        
        # 2. Aplicar a interés pendiente
        if saldo > 0 and self.interes_pendiente > 0:
            aplicado_interes = min(saldo, self.interes_pendiente)
            self.interes_pagado += aplicado_interes
            self.interes_pendiente -= aplicado_interes
            detalle["interes_aplicado"] = aplicado_interes
            saldo -= aplicado_interes
        
        # 3. Aplicar a capital pendiente
        if saldo > 0 and self.capital_pendiente > 0:
            aplicado_capital = min(saldo, self.capital_pendiente)
            self.capital_pagado += aplicado_capital
            self.capital_pendiente -= aplicado_capital
            detalle["capital_aplicado"] = aplicado_capital
            saldo -= aplicado_capital
        
        # 4. Sobrante (si hay)
        if saldo > 0:
            detalle["sobrante"] = saldo
        
        # Actualizar total pagado
        self.total_pagado = self.capital_pagado + self.interes_pagado + self.mora_pagada
        
        # Actualizar estado
        self.actualizar_estado()
        
        return detalle
    
    def actualizar_estado(self):
        """Actualiza el estado de la cuota según los pagos realizados"""
        from datetime import date
        
        if self.capital_pendiente <= 0 and self.interes_pendiente <= 0:
            self.estado = "PAGADA"
            if not self.fecha_pago:
                self.fecha_pago = date.today()
        elif self.total_pagado > 0:
            self.estado = "PARCIAL"
        elif self.esta_vencida:
            self.estado = "VENCIDA"
        else:
            self.estado = "PENDIENTE"


# ============================================
# ALIAS PARA COMPATIBILIDAD
# ============================================
# Algunos endpoints/services pueden referenciar "Amortizacion"
Amortizacion = Cuota


# ============================================
# TABLA DE ASOCIACIÓN PAGO-CUOTAS
# ============================================
pago_cuotas = Table(
    'pago_cuotas',
    Base.metadata,
    Column('pago_id', Integer, ForeignKey('pagos.id', ondelete='CASCADE'), primary_key=True),
    Column('cuota_id', Integer, ForeignKey('cuotas.id', ondelete='CASCADE'), primary_key=True),
    Column('monto_aplicado', Numeric(12, 2), nullable=False),
    Column('aplicado_a_capital', Numeric(12, 2), default=Decimal("0.00")),
    Column('aplicado_a_interes', Numeric(12, 2), default=Decimal("0.00")),
    Column('aplicado_a_mora', Numeric(12, 2), default=Decimal("0.00")),
    Column('creado_en', DateTime(timezone=True), server_default=func.now())
)
