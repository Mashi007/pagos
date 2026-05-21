-- Adjuntos por nota (acuerdo): max 4 archivos PDF/JPG/PNG por mensaje (limite en app).

CREATE TABLE IF NOT EXISTS cobranza_nota_adjuntos (
    id VARCHAR(32) PRIMARY KEY,
    acuerdo_id INTEGER NOT NULL REFERENCES cobranza_acuerdos(id) ON DELETE CASCADE,
    nombre_archivo VARCHAR(255),
    content_type VARCHAR(80) NOT NULL,
    archivo_data BYTEA NOT NULL,
    user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_cobranza_nota_adjuntos_acuerdo ON cobranza_nota_adjuntos (acuerdo_id);
