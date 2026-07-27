-- =============================================================================
-- Conciliacion Bancos: extracto persistente (reutilizable)
-- Columnas del Excel: Banco | Fecha | Referencia(=documento/serial) | Monto
-- Ejecutar en DBeaver contra la BD de pagos.
-- Idempotente: se puede correr mas de una vez.
-- =============================================================================

CREATE TABLE IF NOT EXISTS conciliacion_banco_extracto (
    id              SERIAL PRIMARY KEY,
    banco           VARCHAR(40) NOT NULL,
    fecha           DATE NULL,
    referencia      TEXT NOT NULL,
    referencia_norm TEXT NULL,
    monto           NUMERIC(14, 2) NULL,
    moneda          VARCHAR(3) NOT NULL DEFAULT 'USD',
    -- Clave estable para upsert al re-subir el mismo Excel
    clave_natural   TEXT NOT NULL,
    lote_origen_id  INTEGER NULL
        REFERENCES conciliacion_banco_ocr_lote(id) ON DELETE SET NULL,
    archivo_nombre  VARCHAR(255) NULL,
    creado_en       TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE conciliacion_banco_extracto IS
    'Extracto bancario persistente (Banco/Fecha/Referencia/Monto) para conciliaciones recurrentes';
COMMENT ON COLUMN conciliacion_banco_extracto.banco IS
    'Categoria banco: Mercantil, BNC, Binance, BNV, Recibos, Drive, Otros';
COMMENT ON COLUMN conciliacion_banco_extracto.referencia IS
    'Serial / documento del extracto (= numero_documento en pagos)';
COMMENT ON COLUMN conciliacion_banco_extracto.referencia_norm IS
    'Referencia normalizada para match';
COMMENT ON COLUMN conciliacion_banco_extracto.clave_natural IS
    'banco|fecha|referencia_norm|monto|moneda — evita duplicados al re-cargar';

CREATE UNIQUE INDEX IF NOT EXISTS uq_conciliacion_banco_extracto_clave
    ON conciliacion_banco_extracto (clave_natural);

CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_extracto_banco
    ON conciliacion_banco_extracto (banco);

CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_extracto_fecha
    ON conciliacion_banco_extracto (fecha);

CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_extracto_referencia_norm
    ON conciliacion_banco_extracto (referencia_norm);

CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_extracto_lote_origen
    ON conciliacion_banco_extracto (lote_origen_id);

-- Control:
-- SELECT banco, COUNT(*), MIN(fecha), MAX(fecha)
-- FROM conciliacion_banco_extracto GROUP BY banco ORDER BY 1;
