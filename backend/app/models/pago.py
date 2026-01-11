from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base

CEDULA_LENGTH = 20
DOCUMENTO_LENGTH = 100
DOCUMENTO_NOMBRE_LENGTH = 255
DOCUMENTO_TIPO_LENGTH = 10
DOCUMENTO_RUTA_LENGTH = 500
NUMERIC_PRECISION = 12
NUMERIC_SCALE = 2


class Pago(Base):
    """
    Modelo para pagos
    Representa los pagos realizados por los clientes
    """

    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)

    # DATOS DEL CLIENTE
    cedula = Column(String(CEDULA_LENGTH), nullable=False, index=True)  # Unificado con clientes y prestamos
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)  # ✅ FK agregado

    # DATOS DEL PAGO
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=True, index=True)  # ✅ FK agregado
    numero_cuota = Column(Integer, nullable=True)  # Número de cuota asociada (opcional)
    fecha_pago = Column(DateTime, nullable=False)  # Fecha de pago (manual)
    fecha_registro = Column(
        DateTime, default=func.now(), nullable=False, index=True
    )  # Fecha de registro (automático) - INDEXADO para optimización
    monto_pagado = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    numero_documento = Column(String(DOCUMENTO_LENGTH), nullable=False, index=True)
    institucion_bancaria = Column(String(100), nullable=True)  # Institución bancaria

    # DOCUMENTO ADJUNTO
    documento_nombre = Column(String(DOCUMENTO_NOMBRE_LENGTH), nullable=True)
    documento_tipo = Column(String(DOCUMENTO_TIPO_LENGTH), nullable=True)  # PNG, JPG, PDF
    documento_tamaño = Column(Integer, nullable=True)  # bytes
    documento_ruta = Column(String(DOCUMENTO_RUTA_LENGTH), nullable=True)

    # ESTADO DE CONCILIACIÓN
    conciliado = Column(Boolean, default=False, nullable=False)
    fecha_conciliacion = Column(DateTime, nullable=True)

    # ESTADO DEL PAGO
    estado = Column(String(20), default="PAGADO", nullable=False, index=True)  # PENDIENTE, PAGADO, PARCIAL, ADELANTADO

    # CONTROL Y AUDITORÍA
    activo = Column(Boolean, default=True, nullable=False)
    notas = Column(Text, nullable=True)
    usuario_registro = Column(String(100), nullable=False)  # Email del usuario que registró el pago
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # VERIFICACIÓN DE CONCORDANCIA CON MÓDULO DE PAGOS
    verificado_concordancia = Column(
        String(2), default="NO", nullable=False
    )  # SI/NO - Se actualiza cuando el número de documento coincide en conciliación

    # ============================================
    # COLUMNAS ADICIONALES (FASE 3 - Sincronización ORM vs BD)
    # ============================================
    # Información bancaria y método de pago
    banco = Column(String(100), nullable=True)  # Nombre del banco
    metodo_pago = Column(String(50), nullable=True)  # EFECTIVO, TRANSFERENCIA, CHEQUE, TARJETA
    tipo_pago = Column(String(50), nullable=True)  # Tipo de pago adicional
    
    # Códigos y referencias
    codigo_pago = Column(String(30), nullable=True)  # Código único del pago
    numero_operacion = Column(String(50), nullable=True)  # Número de operación bancaria
    referencia_pago = Column(String(100), nullable=True)  # Referencia adicional del pago
    comprobante = Column(String(200), nullable=True)  # Ruta o referencia al comprobante
    
    # Documentación
    documento = Column(String(50), nullable=True)  # Documento adicional
    
    # Montos detallados
    monto = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=True)  # Monto total (legacy)
    monto_capital = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=True)  # Monto de capital pagado
    monto_interes = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=True)  # Monto de interés pagado
    monto_cuota_programado = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=True)  # Monto de cuota programada
    monto_mora = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=True)  # Monto de mora pagado
    monto_total = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=True)  # Monto total del pago
    descuento = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=True)  # Descuento aplicado
    
    # Información de mora y vencimiento
    dias_mora = Column(Integer, nullable=True)  # Días de mora al momento del pago
    tasa_mora = Column(Numeric(5, 2), nullable=True)  # Tasa de mora aplicada (%)
    fecha_vencimiento = Column(DateTime, nullable=True)  # Fecha de vencimiento de la cuota
    
    # Fechas y horas adicionales
    hora_pago = Column(String(10), nullable=True)  # Hora del pago (formato HH:MM)
    creado_en = Column(DateTime, nullable=True)  # Fecha de creación (legacy)
    
    # Observaciones adicionales
    observaciones = Column(Text, nullable=True)  # Observaciones adicionales del pago

    # Relaciones
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    prestamo = relationship("Prestamo", foreign_keys=[prestamo_id])

    def __repr__(self):
        return f"<Pago(id={self.id}, cedula={self.cedula}, monto={self.monto_pagado}, conciliado={self.conciliado})>"
