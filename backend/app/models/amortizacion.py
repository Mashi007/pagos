"""
Modelo de Amortización - Tabla de cuotas de préstamos
"""

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
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
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False, index=True)
    numero_cuota = Column(Integer, nullable=False)  # 1, 2, 3, etc.

    # Fechas
    fecha_vencimiento = Column(Date, nullable=False, index=True)  # YYYY-MM-DD - INDEXADO para optimización de queries de mora
    fecha_pago = Column(Date, nullable=True)  # YYYY-MM-DD cuando se paga

    # Montos de la cuota
    monto_cuota = Column(Numeric(12, 2), nullable=False)  # Monto total programado de la cuota

    # Saldos
    saldo_capital_inicial = Column(Numeric(12, 2), nullable=False)  # Saldo al inicio del período
    saldo_capital_final = Column(Numeric(12, 2), nullable=False)  # Saldo al fin del período

    # Montos pagados
    total_pagado = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=True)  # Suma acumulativa de todos los abonos/pagos aplicados

    # Mora
    dias_mora = Column(Integer, default=0, nullable=True)

    # ✅ COLUMNAS: Morosidad Calculada Automáticamente
    dias_morosidad = Column(Integer, default=0, index=True, nullable=True)  # ✅ Días de atraso (actualización automática)

    # Estado
    estado = Column(
        String(20), nullable=False, default="PENDIENTE", index=True
    )  # PENDIENTE, PAGADO, ATRASADO, PARCIAL, ADELANTADO

    # Información adicional
    observaciones = Column(String(500), nullable=True)
    es_cuota_especial = Column(Boolean, default=False, nullable=True)

    # ============================================
    # COLUMNAS ADICIONALES (FASE 3 - Sincronización ORM vs BD)
    # Tipos de datos ajustados para coincidir exactamente con la BD
    # ============================================
    creado_en = Column(
        DateTime(timezone=True), nullable=True
    )  # Fecha de creación del registro (TIMESTAMP WITH TIME ZONE en BD)
    actualizado_en = Column(
        DateTime(timezone=True), nullable=True
    )  # Fecha de última actualización (TIMESTAMP WITH TIME ZONE en BD)

    def __repr__(self):
        return f"<Cuota {self.numero_cuota} - Préstamo {self.prestamo_id} - {self.estado}>"

    @property
    def total_pendiente(self) -> Decimal:
        """Calcula el total pendiente de pago (monto_cuota - total_pagado)"""
        monto_cuota_val = self.monto_cuota if self.monto_cuota else Decimal("0.00")  # type: ignore[assignment]
        total_pagado_val = self.total_pagado if self.total_pagado else Decimal("0.00")  # type: ignore[assignment]
        return max(Decimal("0.00"), monto_cuota_val - total_pagado_val)

    @property
    def esta_vencida(self) -> bool:
        """Verifica si la cuota está vencida"""
        from datetime import date

        if self.fecha_vencimiento:
            # ✅ CORREGIDO: Estado correcto es "PAGADO" (masculino), no "PAGADA"
            return self.fecha_vencimiento < date.today() and self.estado != "PAGADO"  # type: ignore[return-value]
        return False

    @property
    def monto_pendiente_total(self) -> Decimal:
        """Calcula el monto total pendiente de pago"""
        return self.total_pendiente

    @property
    def porcentaje_pagado(self) -> Decimal:
        """Calcula el porcentaje pagado de la cuota"""
        if self.monto_cuota and self.monto_cuota > 0:
            porcentaje = (self.total_pagado / self.monto_cuota) * Decimal("100.00")  # type: ignore[operator]
            return min(porcentaje, Decimal("100.00"))  # Máximo 100%
        return Decimal("0.00")

    def calcular_mora(self, tasa_mora_diaria: Decimal) -> Decimal:
        """
        ⚠️ DEPRECADO: La mora está desactivada (siempre 0%).
        Esta función se mantiene por compatibilidad pero siempre retorna 0.

        Args:
            tasa_mora_diaria: Tasa de mora por día (no se usa, siempre 0%)

        Returns:
            Siempre Decimal("0.00") porque la mora está desactivada
        """
        # La mora está desactivada, siempre retorna 0
        return Decimal("0.00")
