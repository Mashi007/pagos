-- =============================================================================
-- CRM Campañas: migración para HTML, CC, adjunto (1 archivo jpg/png/pdf) y destinatarios seleccionados.
-- Ejecutar en DBeaver después de crm_campanas_tablas_dbeaver.sql
-- =============================================================================

-- 1) Nuevas columnas en crm_campana: CC, adjunto (To = destinatarios de clientes)
-- -------------------------------------------------------------------------------
ALTER TABLE crm_campana
    ADD COLUMN IF NOT EXISTS cc_emails TEXT,
    ADD COLUMN IF NOT EXISTS adjunto_nombre VARCHAR(255),
    ADD COLUMN IF NOT EXISTS adjunto_contenido BYTEA;

COMMENT ON COLUMN crm_campana.cc_emails IS 'Emails en copia (CC), separados por coma';
COMMENT ON COLUMN crm_campana.adjunto_nombre IS 'Nombre del archivo adjunto (máx. 1: jpg, png o pdf)';
COMMENT ON COLUMN crm_campana.adjunto_contenido IS 'Contenido binario del adjunto';


-- 2) Tabla de destinatarios seleccionados (si vacía = enviar a todos los clientes con email)
-- ------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_campana_destinatario (
    id SERIAL PRIMARY KEY,
    campana_id INTEGER NOT NULL REFERENCES crm_campana(id) ON DELETE CASCADE,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    UNIQUE(campana_id, cliente_id)
);

CREATE INDEX IF NOT EXISTS ix_crm_campana_destinatario_campana_id ON crm_campana_destinatario (campana_id);

COMMENT ON TABLE crm_campana_destinatario IS 'Si tiene filas: enviar solo a estos clientes. Si vacía: enviar a todos (emails de clientes).';
