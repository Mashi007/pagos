-- =============================================================================
-- Tabla plantillas_notificacion (plantillas de email/WhatsApp por tipo de recordatorio)
-- Ejecutar en la BD antes de usar Herramientas > Plantillas y Config. Notificaciones.
-- =============================================================================

CREATE TABLE IF NOT EXISTS plantillas_notificacion (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    tipo VARCHAR(80) NOT NULL,
    asunto VARCHAR(500) NOT NULL,
    cuerpo TEXT NOT NULL,
    variables_disponibles TEXT,
    activa BOOLEAN NOT NULL DEFAULT true,
    zona_horaria VARCHAR(80) NOT NULL DEFAULT 'America/Caracas',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_plantillas_notificacion_tipo ON plantillas_notificacion(tipo);
CREATE INDEX IF NOT EXISTS ix_plantillas_notificacion_activa ON plantillas_notificacion(activa);

COMMENT ON TABLE plantillas_notificacion IS 'Plantillas de correo/WhatsApp por tipo: PAGO_5_DIAS_ANTES, PAGO_DIA_0, PREJUDICIAL, MORA_61, etc.';
COMMENT ON COLUMN plantillas_notificacion.cuerpo IS 'Cuerpo del mensaje. Variables: {{nombre}}, {{cedula}}, {{fecha_vencimiento}}, {{numero_cuota}}, {{monto}}, {{dias_atraso}}';
