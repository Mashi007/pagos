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
    telefono = Column(String(15), nullable=True, index=True)  # Indexado para búsqueda
    email = Column(String(100), nullable=True, index=True)   # Indexado para búsqueda
    direccion = Column(Text, nullable=True)
    fecha_nacimiento = Column(Date, nullable=True)
    ocupacion = Column(String(100), nullable=True)
    
    # ============================================
    # DATOS DEL VEHÍCULO Y FINANCIAMIENTO
    # ============================================
    modelo_vehiculo = Column(String(100), nullable=True, index=True)
    marca_vehiculo = Column(String(50), nullable=True, index=True)
    anio_vehiculo = Column(Integer, nullable=True)
    color_vehiculo = Column(String(30), nullable=True)
    chasis = Column(String(50), nullable=True, unique=True)
    motor = Column(String(50), nullable=True)
    
    # Concesionario
    concesionario = Column(String(100), nullable=True, index=True)
    vendedor_concesionario = Column(String(100), nullable=True)
    
    # Financiamiento
    total_financiamiento = Column(Numeric(12, 2), nullable=True)
    cuota_inicial = Column(Numeric(12, 2), nullable=True, default=0.00)
    monto_financiado = Column(Numeric(12, 2), nullable=True)  # total - cuota_inicial
    fecha_entrega = Column(Date, nullable=True)  # Inicio de amortización
    numero_amortizaciones = Column(Integer, nullable=True)
    modalidad_pago = Column(String(20), nullable=True, default="MENSUAL", index=True)
    
    # ============================================
    # ASIGNACIÓN Y GESTIÓN
    # ============================================
    asesor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    fecha_asignacion = Column(Date, nullable=True)
    
    # Estado - CON VALORES POR DEFECTO
    estado = Column(String(20), nullable=False, default="ACTIVO", server_default="ACTIVO", index=True)
    activo = Column(Boolean, nullable=False, default=True, server_default="true")
    
    # Estados específicos del financiamiento
    estado_financiero = Column(String(20), nullable=True, default="AL_DIA")  # AL_DIA, MORA, VENCIDO
    dias_mora = Column(Integer, default=0)
    
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
    
    @property
    def nombre_completo(self) -> str:
        """Retorna el nombre completo del cliente"""
        return f"{self.nombres} {self.apellidos}"
    
    @property
    def tiene_financiamiento(self) -> bool:
        """Verifica si el cliente tiene datos de financiamiento"""
        return self.total_financiamiento is not None and self.total_financiamiento > 0
    
    @property
    def vehiculo_completo(self) -> str:
        """Retorna descripción completa del vehículo"""
        if not self.modelo_vehiculo:
            return "Sin vehículo"
        
        parts = []
        if self.marca_vehiculo:
            parts.append(self.marca_vehiculo)
        parts.append(self.modelo_vehiculo)
        if self.anio_vehiculo:
            parts.append(str(self.anio_vehiculo))
        if self.color_vehiculo:
            parts.append(self.color_vehiculo)
        
        return " ".join(parts)
    
    @property
    def esta_en_mora(self) -> bool:
        """Verifica si el cliente está en mora"""
        return self.estado_financiero == "MORA" and self.dias_mora > 0
    
    def calcular_resumen_financiero(self, db_session):
        """Calcula resumen financiero del cliente"""
        from decimal import Decimal
        
        if not self.tiene_financiamiento:
            return {
                "total_financiado": Decimal("0.00"),
                "total_pagado": Decimal("0.00"),
                "saldo_pendiente": Decimal("0.00"),
                "cuotas_pagadas": 0,
                "cuotas_totales": 0,
                "porcentaje_avance": 0.0
            }
        
        # Obtener préstamos activos del cliente
        prestamos = db_session.query(Prestamo).filter(
            Prestamo.cliente_id == self.id,
            Prestamo.estado.in_(["ACTIVO", "EN_MORA"])
        ).all()
        
        total_financiado = sum(p.monto_total for p in prestamos) or Decimal("0.00")
        total_pagado = sum(p.total_pagado for p in prestamos) or Decimal("0.00")
        saldo_pendiente = sum(p.saldo_pendiente for p in prestamos) or Decimal("0.00")
        cuotas_pagadas = sum(p.cuotas_pagadas for p in prestamos)
        cuotas_totales = sum(p.numero_cuotas for p in prestamos)
        
        porcentaje_avance = (float(total_pagado) / float(total_financiado) * 100) if total_financiado > 0 else 0.0
        
        return {
            "total_financiado": total_financiado,
            "total_pagado": total_pagado,
            "saldo_pendiente": saldo_pendiente,
            "cuotas_pagadas": cuotas_pagadas,
            "cuotas_totales": cuotas_totales,
            "porcentaje_avance": round(porcentaje_avance, 2)
        }
