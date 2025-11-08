"""
Modelos para las tablas oficiales del dashboard
Estas tablas contienen datos pre-agregados para reporting
"""

from sqlalchemy import TIMESTAMP, Column, Date, Integer, Numeric, String
from sqlalchemy.sql import func

from app.db.session import Base


class DashboardMorosidadMensual(Base):
    """Tabla oficial de morosidad mensual"""

    __tablename__ = "dashboard_morosidad_mensual"

    id = Column(Integer, primary_key=True, index=True)
    año = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    morosidad_total = Column(Numeric(15, 2), nullable=False, default=0)
    cantidad_cuotas_vencidas = Column(Integer, nullable=False, default=0)
    cantidad_prestamos_afectados = Column(Integer, nullable=False, default=0)
    fecha_actualizacion = Column(TIMESTAMP, default=func.now())

    def __repr__(self):
        return f"<DashboardMorosidadMensual {self.año}-{self.mes:02d}: ${self.morosidad_total}>"


class DashboardCobranzasMensuales(Base):
    """Tabla oficial de cobranzas mensuales"""

    __tablename__ = "dashboard_cobranzas_mensuales"

    id = Column(Integer, primary_key=True, index=True)
    año = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    nombre_mes = Column(String(20), nullable=False)
    cobranzas_planificadas = Column(Numeric(15, 2), nullable=False, default=0)
    pagos_reales = Column(Numeric(15, 2), nullable=False, default=0)
    meta_mensual = Column(Numeric(15, 2), nullable=False, default=0)
    fecha_actualizacion = Column(TIMESTAMP, default=func.now())

    def __repr__(self):
        return f"<DashboardCobranzasMensuales {self.nombre_mes} {self.año}>"


class DashboardKPIsDiarios(Base):
    """Tabla oficial de KPIs diarios"""

    __tablename__ = "dashboard_kpis_diarios"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False, unique=True)
    total_prestamos = Column(Integer, nullable=False, default=0)
    total_prestamos_valor = Column(Numeric(15, 2), nullable=False, default=0)
    creditos_nuevos_mes = Column(Integer, nullable=False, default=0)
    creditos_nuevos_mes_valor = Column(Numeric(15, 2), nullable=False, default=0)
    total_clientes = Column(Integer, nullable=False, default=0)
    total_morosidad_usd = Column(Numeric(15, 2), nullable=False, default=0)
    cartera_total = Column(Numeric(15, 2), nullable=False, default=0)
    total_cobrado = Column(Numeric(15, 2), nullable=False, default=0)
    fecha_actualizacion = Column(TIMESTAMP, default=func.now())

    def __repr__(self):
        return f"<DashboardKPIsDiarios {self.fecha}>"


class DashboardFinanciamientoMensual(Base):
    """Tabla oficial de financiamiento mensual"""

    __tablename__ = "dashboard_financiamiento_mensual"

    id = Column(Integer, primary_key=True, index=True)
    año = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    nombre_mes = Column(String(20), nullable=False)
    cantidad_nuevos = Column(Integer, nullable=False, default=0)
    monto_nuevos = Column(Numeric(15, 2), nullable=False, default=0)
    total_acumulado = Column(Numeric(15, 2), nullable=False, default=0)
    fecha_actualizacion = Column(TIMESTAMP, default=func.now())

    def __repr__(self):
        return f"<DashboardFinanciamientoMensual {self.nombre_mes} {self.año}>"


class DashboardMorosidadPorAnalista(Base):
    """Tabla oficial de morosidad por analista"""

    __tablename__ = "dashboard_morosidad_por_analista"

    id = Column(Integer, primary_key=True, index=True)
    analista = Column(String(100), nullable=False, unique=True)
    total_morosidad = Column(Numeric(15, 2), nullable=False, default=0)
    cantidad_clientes = Column(Integer, nullable=False, default=0)
    cantidad_cuotas_atrasadas = Column(Integer, nullable=False, default=0)
    promedio_morosidad_por_cliente = Column(Numeric(15, 2), nullable=False, default=0)
    fecha_actualizacion = Column(TIMESTAMP, default=func.now())

    def __repr__(self):
        return f"<DashboardMorosidadPorAnalista {self.analista}: ${self.total_morosidad}>"


class DashboardPrestamosPorConcesionario(Base):
    """Tabla oficial de préstamos por concesionario"""

    __tablename__ = "dashboard_prestamos_por_concesionario"

    id = Column(Integer, primary_key=True, index=True)
    concesionario = Column(String(100), nullable=False, unique=True)
    total_prestamos = Column(Integer, nullable=False, default=0)
    porcentaje = Column(Numeric(5, 2), nullable=False, default=0)
    fecha_actualizacion = Column(TIMESTAMP, default=func.now())

    def __repr__(self):
        return f"<DashboardPrestamosPorConcesionario {self.concesionario}: {self.total_prestamos}>"


class DashboardPagosMensuales(Base):
    """Tabla oficial de pagos mensuales"""

    __tablename__ = "dashboard_pagos_mensuales"

    id = Column(Integer, primary_key=True, index=True)
    año = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    nombre_mes = Column(String(20), nullable=False)
    cantidad_pagos = Column(Integer, nullable=False, default=0)
    monto_total = Column(Numeric(15, 2), nullable=False, default=0)
    fecha_actualizacion = Column(TIMESTAMP, default=func.now())

    def __repr__(self):
        return f"<DashboardPagosMensuales {self.nombre_mes} {self.año}: ${self.monto_total}>"


class DashboardCobrosPorAnalista(Base):
    """Tabla oficial de cobros por analista"""

    __tablename__ = "dashboard_cobros_por_analista"

    id = Column(Integer, primary_key=True, index=True)
    analista = Column(String(100), nullable=False, unique=True)
    total_cobrado = Column(Numeric(15, 2), nullable=False, default=0)
    cantidad_pagos = Column(Integer, nullable=False, default=0)
    fecha_actualizacion = Column(TIMESTAMP, default=func.now())

    def __repr__(self):
        return f"<DashboardCobrosPorAnalista {self.analista}: ${self.total_cobrado}>"


class DashboardMetricasAcumuladas(Base):
    """Tabla oficial de métricas acumuladas"""

    __tablename__ = "dashboard_metricas_acumuladas"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False, unique=True)
    cartera_total = Column(Numeric(15, 2), nullable=False, default=0)
    morosidad_total = Column(Numeric(15, 2), nullable=False, default=0)
    total_cobrado = Column(Numeric(15, 2), nullable=False, default=0)
    total_prestamos = Column(Integer, nullable=False, default=0)
    total_clientes = Column(Integer, nullable=False, default=0)
    fecha_actualizacion = Column(TIMESTAMP, default=func.now())

    def __repr__(self):
        return f"<DashboardMetricasAcumuladas {self.fecha}>"


