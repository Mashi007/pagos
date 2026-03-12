-- =============================================================================
-- CRM Campañas: tablas para envío de correos masivos a clientes (por lotes).
-- Ejecutar en DBeaver sobre PostgreSQL.
-- Destinatarios: todos los correos registrados en tabla clientes (sin duplicados).
-- =============================================================================

-- 1) Campaña (cabecera)
-- ---------------------
CREATE TABLE IF NOT EXISTS crm_campana (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    asunto VARCHAR(500) NOT NULL,
    cuerpo_texto TEXT NOT NULL,
    cuerpo_html TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'borrador',
    total_destinatarios INTEGER NOT NULL DEFAULT 0,
    enviados INTEGER NOT NULL DEFAULT 0,
    fallidos INTEGER NOT NULL DEFAULT 0,
    batch_size INTEGER NOT NULL DEFAULT 25,
    delay_entre_batches_seg INTEGER NOT NULL DEFAULT 3,
    fecha_creacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_envio_inicio TIMESTAMP WITHOUT TIME ZONE,
    fecha_envio_fin TIMESTAMP WITHOUT TIME ZONE,
    usuario_creacion VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS ix_crm_campana_estado ON crm_campana (estado);
CREATE INDEX IF NOT EXISTS ix_crm_campana_fecha_creacion ON crm_campana (fecha_creacion);

COMMENT ON TABLE crm_campana IS 'Campañas de email CRM: envío por lotes a correos de tabla clientes';
COMMENT ON COLUMN crm_campana.estado IS 'borrador | programada | enviando | completada | cancelada';
COMMENT ON COLUMN crm_campana.batch_size IS 'Correos por lote (ej. 25 para no saturar Gmail)';
COMMENT ON COLUMN crm_campana.delay_entre_batches_seg IS 'Segundos de espera entre lotes';


-- 2) Detalle de envío por destinatario (registro por correo enviado/fallido)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_campana_envio (
    id SERIAL PRIMARY KEY,
    campana_id INTEGER NOT NULL REFERENCES crm_campana(id) ON DELETE CASCADE,
    cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
    email VARCHAR(255) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    fecha_envio TIMESTAMP WITHOUT TIME ZONE,
    error_mensaje TEXT
);

CREATE INDEX IF NOT EXISTS ix_crm_campana_envio_campana_id ON crm_campana_envio (campana_id);
CREATE INDEX IF NOT EXISTS ix_crm_campana_envio_estado ON crm_campana_envio (estado);
CREATE INDEX IF NOT EXISTS ix_crm_campana_envio_cliente_id ON crm_campana_envio (cliente_id);

COMMENT ON TABLE crm_campana_envio IS 'Registro de cada envío por campaña (éxito/fallo)';
COMMENT ON COLUMN crm_campana_envio.estado IS 'pendiente | enviado | fallido';
