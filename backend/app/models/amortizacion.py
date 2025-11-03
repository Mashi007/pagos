"""
Modelo de Amortización - Tabla de cuotas de préstamos
"""

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
)

from app.db.session import Base


class Cuota(Base):
    """
    Modelo para las cuotas de un préstamo
    Representa cada pago periódico que debe hacer el cliente
    """

    __tablename__ = "cuotas"

    # Claves primarias y foráneas
    id = Column(Integer, primary_key=True, index=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False, index=True)
    numero_cuota = Column(Integer, nullable=False)  # 1, 2, 3, etc.

    # Fechas
    fecha_vencimiento = Column(Date, nullable=False)  # YYYY-MM-DD
    fecha_pago = Column(Date, nullable=True)  # YYYY-MM-DD cuando se paga

    # Montos de la cuota
    monto_cuota = Column(Numeric(12, 2), nullable=False)
    monto_capital = Column(Numeric(12, 2), nullable=False)
    monto_interes = Column(Numeric(12, 2), nullable=False)

    # Saldos
    saldo_capital_inicial = Column(Numeric(12, 2), nullable=False)  # Saldo al inicio del período
    saldo_capital_final = Column(Numeric(12, 2), nullable=False)  # Saldo al fin del período

    # Montos pagados
    capital_pagado = Column(Numeric(12, 2), default=Decimal("0.00"))
    interes_pagado = Column(Numeric(12, 2), default=Decimal("0.00"))
    mora_pagada = Column(Numeric(12, 2), default=Decimal("0.00"))
    total_pagado = Column(Numeric(12, 2), default=Decimal("0.00"))

    # Montos pendientes
    capital_pendiente = Column(Numeric(12, 2), nullable=False)  # Capital que falta pagar de esta cuota
    interes_pendiente = Column(Numeric(12, 2), nullable=False)  # Interés que falta pagar de esta cuota

    # Mora
    dias_mora = Column(Integer, default=0)
    monto_mora = Column(Numeric(12, 2), default=Decimal("0.00"))
    tasa_mora = Column(Numeric(5, 2), default=Decimal("0.00"))  # Tasa de mora aplicada (%)

    # Estado
    estado = Column(
        String(20), nullable=False, default="PENDIENTE", index=True
    )  # PENDIENTE, PAGADO, ATRASADO, PARCIAL, ADELANTADO

    # Información adicional
    observaciones = Column(String(500), nullable=True)
    es_cuota_especial = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Cuota {self.numero_cuota} - Préstamo {self.prestamo_id} - {self.estado}>"

    @property
    def total_pendiente(self) -> Decimal:
        """Calcula el total pendiente de pago"""
        return self.capital_pendiente + self.interes_pendiente + self.monto_mora  # type: ignore[return-value]

    @property
    def esta_vencida(self) -> bool:
        """Verifica si la cuota está vencida"""
        from datetime import date

        if self.fecha_vencimiento:
            return self.fecha_vencimiento < date.today() and self.estado != "PAGADA"  # type: ignore[return-value]
        return False

    def calcular_mora(self, tasa_mora_diaria: Decimal) -> Decimal:
        """
        Calcula la mora acumulada hasta la fecha actual

        Args:
            tasa_mora_diaria: Tasa de mora por día (ej: 0.001 para 0.1% diario)

        Returns:
            Monto de mora calculado
        """
        if self.esta_vencida:
            from datetime import date

            dias_vencido = (date.today() - self.fecha_vencimiento).days

            # Calcular mora sobre el saldo pendiente
            saldo_mora = self.capital_pendiente + self.interes_pendiente
            mora_calculada = saldo_mora * tasa_mora_diaria * dias_vencido

            return mora_calculada
        return Decimal("0.00")


# Tabla de asociación para pagos y cuotas
pago_cuotas = Table(
    "pago_cuotas",
    Base.metadata,
    Column("pago_id", ForeignKey("pagos.id", ondelete="CASCADE"), primary_key=True),
    Column("cuota_id", ForeignKey("cuotas.id", ondelete="CASCADE"), primary_key=True),
    Column("monto_aplicado", Numeric(12, 2), nullable=False),
    Column("aplicado_a_capital", Numeric(12, 2), default=Decimal("0.00")),
    Column("aplicado_a_interes", Numeric(12, 2), default=Decimal("0.00")),
    Column("aplicado_a_mora", Numeric(12, 2), default=Decimal("0.00")),
)
