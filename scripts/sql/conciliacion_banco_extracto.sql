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
    'serial|fecha|monto (referencia_norm) — evita duplicados al re-cargar Excel';

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

-- =============================================================================
-- Backfill desde un lote ya cargado (ocr_banco) cuando historica = 0.
-- ocr_banco NO tiene columna banco: fijar banco (ej. Mercantil) y lote_id.
-- =============================================================================
/*
INSERT INTO conciliacion_banco_extracto (
    banco, fecha, referencia, referencia_norm, monto, moneda,
    clave_natural, lote_origen_id, archivo_nombre, creado_en, actualizado_en
)
SELECT
    'Mercantil' AS banco,
    b.fecha_banco,
    b.referencia_banco,
    COALESCE(NULLIF(TRIM(b.ref_banco_norm), ''), b.referencia_banco),
    b.monto_banco,
    COALESCE(NULLIF(TRIM(b.moneda_fila), ''), l.moneda_carga, 'USD'),
    COALESCE(NULLIF(TRIM(b.ref_banco_norm), ''), b.referencia_banco) || '|' ||
        COALESCE(to_char(b.fecha_banco, 'YYYY-MM-DD'), '') || '|' ||
        COALESCE(TRIM(TO_CHAR(b.monto_banco, 'FM999999999990.00')), '')
        AS clave_natural,
    l.id,
    l.archivo_nombre,
    NOW(),
    NOW()
FROM conciliacion_banco_ocr_banco b
JOIN conciliacion_banco_ocr_lote l ON l.id = b.lote_id
WHERE b.lote_id = 38
ON CONFLICT (clave_natural) DO UPDATE SET
    lote_origen_id = EXCLUDED.lote_origen_id,
    archivo_nombre = COALESCE(EXCLUDED.archivo_nombre, conciliacion_banco_extracto.archivo_nombre),
    actualizado_en = EXCLUDED.actualizado_en;
*/

-- =============================================================================
-- Migrar claves viejas -> serial|fecha|monto y borrar duplicados (id mayor gana).
-- =============================================================================
UPDATE conciliacion_banco_extracto
SET clave_natural =
    COALESCE(NULLIF(TRIM(referencia_norm), ''), TRIM(referencia), '')
    || '|' || COALESCE(to_char(fecha, 'YYYY-MM-DD'), '')
    || '|' || CASE
        WHEN monto IS NULL THEN ''
        ELSE TRIM(to_char(monto, 'FM999999999990.00'))
    END;

DELETE FROM conciliacion_banco_extracto a
USING conciliacion_banco_extracto b
WHERE a.clave_natural = b.clave_natural
  AND a.id < b.id;
