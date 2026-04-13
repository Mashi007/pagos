"""
Modelo SQLAlchemy para Préstamo.
Alineado con la tabla real public.prestamos (columnas confirmadas desde BD).
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import validates
from sqlalchemy.sql import func, text

from app.core.database import Base
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento


class Prestamo(Base):
    __tablename__ = "prestamos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    cedula = Column(String(20), nullable=False)

    @validates("cedula")
    def _cedula_guardado_mayusculas(self, key, value):
        if value is None:
            return None
        n = normalizar_cedula_almacenamiento(value)
        return n if n is not None else ""

    nombres = Column(String(255), nullable=False)
    total_financiamiento = Column(Numeric(14, 2), nullable=False)
    fecha_requerimiento = Column(Date, nullable=False)
    modalidad_pago = Column(String(50), nullable=False)
    numero_cuotas = Column(Integer, nullable=False)
    cuota_periodo = Column(Numeric(14, 2), nullable=False)
    tasa_interes = Column(Numeric(10, 4), nullable=False, server_default=text("0.00"))
    fecha_base_calculo = Column(Date, nullable=True)
    producto = Column(String(255), nullable=False)
    estado = Column(String(50), nullable=False, index=True, server_default=text("'DRAFT'"))
    # Fase finiquito visible en listados (ANTIGUO, EN_PROCESO, TERMINADO); no sustituye `estado`.
    estado_gestion_finiquito = Column(String(32), nullable=True, index=True)
    # Ultimo dia laboral (15 desde pasar a EN_PROCESO, lun-vie Caracas) para mensaje en listados.
    finiquito_tramite_fecha_limite = Column(Date, nullable=True)
    # Fecha calendario (America/Caracas) en que el prestamo paso a LIQUIDADO; emails con PDF se programan dias despues.
    fecha_liquidado = Column(Date, nullable=True, index=True)
    usuario_proponente = Column(String(255), nullable=False, server_default=text("'itmaster@rapicreditca.com'"))
    usuario_aprobador = Column(String(255), nullable=True)
    observaciones = Column(Text, nullable=True, server_default=text("'No observaciones'"))
    informacion_desplegable = Column(Boolean, nullable=False, server_default=text("false"))
    # Alta en BD (default al insertar). Si se persiste fecha_aprobacion, el API alinea fecha_registro al día calendario anterior (medianoche naive).
    fecha_registro = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    fecha_aprobacion = Column(DateTime(timezone=False), nullable=True)
    fecha_actualizacion = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())
    concesionario = Column(String(255), nullable=True, index=True)
    analista = Column(String(255), nullable=False)
    modelo_vehiculo = Column(String(255), nullable=True, index=True)
    usuario_autoriza = Column(String(255), nullable=True, server_default=text("'operaciones@rapicreditca.com'"))
    ml_impago_nivel_riesgo_manual = Column(String(50), nullable=True)
    ml_impago_probabilidad_manual = Column(Numeric(10, 4), nullable=True)
    concesionario_id = Column(Integer, nullable=True)
    analista_id = Column(Integer, ForeignKey("analistas.id", ondelete="SET NULL"), nullable=True, index=True)
    modelo_vehiculo_id = Column(Integer, nullable=True)
    valor_activo = Column(Numeric(14, 2), nullable=True)
    ml_impago_nivel_riesgo_calculado = Column(String(50), nullable=True)
    ml_impago_probabilidad_calculada = Column(Numeric(10, 4), nullable=True)
    ml_impago_calculado_en = Column(DateTime(timezone=False), nullable=True)
    ml_impago_modelo_id = Column(Integer, nullable=True)
    requiere_revision = Column(Boolean, nullable=False, server_default=text("false"))
    estado_edicion = Column(String(50), nullable=False, server_default=text("'COMPLETADO'"), index=True)
    # Snapshot de GET comparar-abonos-drive-cuotas (JSON) + marca de tiempo; se invalida al sync de la hoja CONCILIACIÓN.
    abonos_drive_cuotas_cache = Column(JSON, nullable=True)
    abonos_drive_cuotas_cache_at = Column(DateTime(timezone=False), nullable=True)
    # Columna Q (fila CONCILIACIÓN alineada al préstamo) vs fecha_aprobacion en BD; Notificaciones > Fecha.
    fecha_entrega_q_aprobacion_cache = Column(JSON, nullable=True)
    fecha_entrega_q_aprobacion_cache_at = Column(DateTime(timezone=False), nullable=True)

    @property
    def modelo(self):
        """Alias para modelo_vehiculo (usado en listado y filtros)."""
        return self.modelo_vehiculo

    @property
    def fecha_creacion(self):
        """Alias para fecha_registro (usado en listado y respuestas)."""
        return self.fecha_registro
