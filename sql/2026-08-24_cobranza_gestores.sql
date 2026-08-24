-- Gestores de cobranza (idempotente; tambien se crea en cobranzas_schema_startup).
CREATE TABLE IF NOT EXISTS cobranza_gestor_asignaciones (
    id SERIAL PRIMARY KEY,
    prestamo_id INTEGER NOT NULL REFERENCES prestamos(id) ON DELETE CASCADE,
    gestor_slug VARCHAR(64) NOT NULL,
    asignado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_cobranza_gestor_asignaciones_prestamo UNIQUE (prestamo_id)
);

CREATE INDEX IF NOT EXISTS ix_cobranza_gestor_asignaciones_gestor
    ON cobranza_gestor_asignaciones (gestor_slug);

CREATE TABLE IF NOT EXISTS cobranza_gestor_desempeno_diario (
    fecha DATE NOT NULL,
    gestor_slug VARCHAR(64) NOT NULL,
    total_cobranza_usd NUMERIC(14, 2) NOT NULL DEFAULT 0,
    cantidad_casos INTEGER NOT NULL DEFAULT 0,
    actualizado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (fecha, gestor_slug)
);
