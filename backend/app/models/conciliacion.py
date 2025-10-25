# ForeignKey, Integer, Numeric, String, Text,)from sqlalchemy.orm import relationshipfrom sqlalchemy.sql import funcfrom
# Column(String(100), nullable=False, index=True) monto_banco = Column(Numeric(12, 2), nullable=False) # Estado del match
# estado_match = Column( String(20), nullable=False, default="PENDIENTE", index=True ) # PENDIENTE, CONCILIADO, RECHAZADO,
# nullable=True, index=True, ) # Información adicional observaciones = Column(Text, nullable=True) tipo_match =
# Column(String(20), nullable=True) # AUTOMATICO, MANUAL confianza_match = Column( Numeric(5, 2), nullable=True ) #
# back_populates="conciliacion") usuario = relationship("User") def __repr__(self): return "<Conciliacion
# Pago:{self.pago_id} - {self.estado_match}>" @property def esta_conciliado(self) -> bool: """Verifica si está conciliado"""
# return self.estado_match == "CONCILIADO" @property def diferencia_monto(self) -> Decimal: """Calcula la diferencia entre
# monto del sistema y banco""" if self.pago: return abs(self.monto_banco - self.pago.monto_pagado) return Decimal("0.00") def
# marcar_conciliado(self, usuario_id: int, observaciones: str = None): """Marca como conciliado""" self.estado_match =
# marcar_rechazado(self, usuario_id: int, motivo: str): """Marca como rechazado""" self.estado_match = "RECHAZADO"

"""
"""