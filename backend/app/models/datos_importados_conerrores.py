"""
Tabla datos_importados_conerrores: registros que no cumplen validadores
al importar desde "Importar reportados aprobados (Cobros)".
Se acumulan hasta que el usuario descarga Excel; al descargar se vacía la tabla.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class DatosImportadosConErrores(Base):
    __tablename__ = "datos_importados_conerrores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cedula_cliente = Column(String(20), nullable=True, index=True)
    prestamo_id = Column(Integer, nullable=True, index=True)
    fecha_pago = Column(DateTime(timezone=False), nullable=False)
    monto_pagado = Column(Numeric(14, 2), nullable=False)
    numero_documento = Column(String(100), nullable=True)
    estado = Column(String(30), nullable=True, server_default="PENDIENTE")
    referencia_pago = Column(String(100), nullable=False, server_default="")
    errores_descripcion = Column(JSONB, nullable=True)  # lista de strings
    observaciones = Column(String(255), nullable=True)
    fila_origen = Column(Integer, nullable=True)  # pago_reportado.id
    referencia_interna = Column(String(100), nullable=True)  # trazabilidad reportado
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
