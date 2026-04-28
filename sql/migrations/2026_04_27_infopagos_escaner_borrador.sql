-- Borrador persistente del escáner Infopagos (comprobante + metadatos).
-- Aplicar en PostgreSQL antes de usar el escáner con persistencia de borrador.

CREATE TABLE IF NOT EXISTS infopagos_escaner_borrador (
    id VARCHAR(32) PRIMARY KEY,
    cliente_id INTEGER REFERENCES clientes (id) ON DELETE SET NULL,
    usuario_id INTEGER REFERENCES usuarios (id) ON DELETE SET NULL,
    tipo_cedula VARCHAR(2) NOT NULL,
    numero_cedula VARCHAR(13) NOT NULL,
    cedula_normalizada VARCHAR(20) NOT NULL,
    fuente_tasa_cambio VARCHAR(16),
    comprobante_imagen_id VARCHAR(32) NOT NULL REFERENCES pago_comprobante_imagen (id) ON DELETE RESTRICT,
    comprobante_nombre VARCHAR(255) NOT NULL,
    payload_json TEXT,
    estado VARCHAR(24) NOT NULL DEFAULT 'borrador',
    pago_reportado_id INTEGER REFERENCES pagos_reportados (id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_infopagos_escaner_borrador_cedula_estado
    ON infopagos_escaner_borrador (cedula_normalizada, estado);

CREATE INDEX IF NOT EXISTS idx_infopagos_escaner_borrador_created
    ON infopagos_escaner_borrador (created_at);

COMMENT ON TABLE infopagos_escaner_borrador IS
    'Escáner Infopagos: borrador tras extraer con Gemini; confirmado al enviar reporte (reutiliza pago_comprobante_imagen).';
