-- =============================================================================
-- Conciliacion Bancos — DDL completo para DBeaver (idempotente)
-- Excel: Banco | Fecha | Referencia(=serial) | Monto
-- BD historica: conciliacion_banco_extracto
-- Unicidad: banco + fecha + serial + monto  (clave = banco|serial|fecha|monto)
-- Ejecutar entero en DBeaver contra la BD de pagos. Se puede correr mas de una vez.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Lotes de conciliacion (sesion de trabajo)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conciliacion_banco_ocr_lote (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER NULL,
    archivo_nombre  VARCHAR(255) NOT NULL,
    fecha_desde     DATE NOT NULL,
    fecha_hasta     DATE NOT NULL,
    estado          VARCHAR(30) NOT NULL DEFAULT 'CARGADO',
    moneda_carga    VARCHAR(3) NOT NULL DEFAULT 'USD',
    notas           TEXT NULL,
    creado_en       TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_ocr_lote_estado
    ON conciliacion_banco_ocr_lote (estado);
CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_ocr_lote_creado
    ON conciliacion_banco_ocr_lote (creado_en DESC);

COMMENT ON TABLE conciliacion_banco_ocr_lote IS
    'Sesion/lote de conciliacion (Excel o BD historica)';

-- ---------------------------------------------------------------------------
-- 2) Filas del lote (workset a comparar)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conciliacion_banco_ocr_banco (
    id                    SERIAL PRIMARY KEY,
    lote_id               INTEGER NOT NULL
        REFERENCES conciliacion_banco_ocr_lote(id) ON DELETE CASCADE,
    fila_excel            INTEGER NOT NULL,
    fecha_banco           DATE NULL,
    referencia_banco      TEXT NOT NULL,
    ref_banco_norm        TEXT NULL,
    monto_banco           NUMERIC(14, 2) NULL,
    monto_banco_original  NUMERIC(14, 2) NULL,
    moneda_fila           VARCHAR(3) NULL
);

CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_ocr_banco_lote
    ON conciliacion_banco_ocr_banco (lote_id);
CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_ocr_banco_ref_norm
    ON conciliacion_banco_ocr_banco (ref_banco_norm);

COMMENT ON TABLE conciliacion_banco_ocr_banco IS
    'Filas del lote (no es BD historica; se regeneran al cargar)';

-- ---------------------------------------------------------------------------
-- 3) Resultados de comparacion / decisiones
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conciliacion_banco_ocr_resultado (
    id                   SERIAL PRIMARY KEY,
    lote_id              INTEGER NOT NULL
        REFERENCES conciliacion_banco_ocr_lote(id) ON DELETE CASCADE,
    banco_id             INTEGER NULL
        REFERENCES conciliacion_banco_ocr_banco(id) ON DELETE SET NULL,
    pago_id              INTEGER NULL
        REFERENCES pagos(id) ON DELETE SET NULL,
    fecha_banco          DATE NULL,
    fecha_bd             DATE NULL,
    referencia_banco     TEXT NULL,
    referencia_bd        TEXT NULL,
    monto_banco          NUMERIC(14, 2) NULL,
    monto_bd             NUMERIC(14, 2) NULL,
    similitud_pct        NUMERIC(5, 2) NULL,
    tipo_novedad         VARCHAR(40) NOT NULL,
    decision             VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    fuente_elegida       VARCHAR(10) NULL,
    aplicado             BOOLEAN NOT NULL DEFAULT FALSE,
    detalle_aplicacion   TEXT NULL,
    usuario_decision_id  INTEGER NULL,
    decidido_en          TIMESTAMP WITHOUT TIME ZONE NULL,
    valores_antes        TEXT NULL,
    valores_despues      TEXT NULL,
    creado_en            TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_ocr_resultado_lote
    ON conciliacion_banco_ocr_resultado (lote_id);
CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_ocr_resultado_pago
    ON conciliacion_banco_ocr_resultado (pago_id);
CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_ocr_resultado_decision
    ON conciliacion_banco_ocr_resultado (decision);
CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_ocr_resultado_tipo
    ON conciliacion_banco_ocr_resultado (tipo_novedad);

COMMENT ON TABLE conciliacion_banco_ocr_resultado IS
    'Match Excel/historica vs pagos + decision (VISTO/CORREGIR/OMITIR)';

-- ---------------------------------------------------------------------------
-- 4) BD historica (persistente entre sesiones)
--    Unicidad: NO puede haber 2 filas con mismo banco+fecha+serial+monto
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conciliacion_banco_extracto (
    id              SERIAL PRIMARY KEY,
    banco           VARCHAR(40) NOT NULL,
    fecha           DATE NULL,
    referencia      TEXT NOT NULL,
    referencia_norm TEXT NULL,
    monto           NUMERIC(14, 2) NULL,
    moneda          VARCHAR(3) NOT NULL DEFAULT 'USD',
    -- banco|serial|fecha|monto  (upsert al re-subir Excel)
    clave_natural   TEXT NOT NULL,
    lote_origen_id  INTEGER NULL
        REFERENCES conciliacion_banco_ocr_lote(id) ON DELETE SET NULL,
    archivo_nombre  VARCHAR(255) NULL,
    creado_en       TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE conciliacion_banco_extracto IS
    'Extracto bancario persistente (BD historica). Reconciliar sin re-subir Excel.';
COMMENT ON COLUMN conciliacion_banco_extracto.banco IS
    'Categoria: Mercantil, BNC, Binance, BNV, Recibos, Drive, Otros';
COMMENT ON COLUMN conciliacion_banco_extracto.referencia IS
    'Serial / documento del extracto (= numero_documento en pagos)';
COMMENT ON COLUMN conciliacion_banco_extracto.referencia_norm IS
    'Referencia normalizada para match';
COMMENT ON COLUMN conciliacion_banco_extracto.clave_natural IS
    'banco|serial|fecha|monto — UNA sola fila por banco+fecha+serial+monto';

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

CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_extracto_moneda
    ON conciliacion_banco_extracto (moneda);

-- ---------------------------------------------------------------------------
-- 5) Migrar claves viejas (serial|fecha|monto) -> banco|serial|fecha|monto
--    y eliminar duplicados exactos (queda el id mayor)
-- ---------------------------------------------------------------------------
UPDATE conciliacion_banco_extracto
SET clave_natural =
    TRIM(banco)
    || '|' || COALESCE(NULLIF(TRIM(referencia_norm), ''), TRIM(referencia), '')
    || '|' || COALESCE(to_char(fecha, 'YYYY-MM-DD'), '')
    || '|' || CASE
        WHEN monto IS NULL THEN ''
        ELSE TRIM(to_char(monto, 'FM999999999990.00'))
    END;

DELETE FROM conciliacion_banco_extracto a
USING conciliacion_banco_extracto b
WHERE a.clave_natural = b.clave_natural
  AND a.id < b.id;

COMMIT;

-- =============================================================================
-- Controles (ejecutar aparte si quiere)
-- =============================================================================
-- Tablas:
-- SELECT table_name FROM information_schema.tables
-- WHERE table_name LIKE 'conciliacion_banco%'
-- ORDER BY 1;

-- Resumen BD historica:
SELECT banco, moneda, COUNT(*) AS filas,
       MIN(fecha) AS min_f, MAX(fecha) AS max_f,
       COUNT(DISTINCT archivo_nombre) AS archivos
FROM conciliacion_banco_extracto
GROUP BY banco, moneda
ORDER BY 1, 2;

-- Duplicados exactos (debe dar 0 filas):
SELECT clave_natural, COUNT(*) AS n
FROM conciliacion_banco_extracto
GROUP BY clave_natural
HAVING COUNT(*) > 1;

-- =============================================================================
-- Backfill opcional desde un lote OCR (si historica=0).
-- Cambiar banco y lote_id. ocr_banco NO tiene columna banco.
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
    COALESCE(b.monto_banco_original, b.monto_banco),
    COALESCE(NULLIF(TRIM(b.moneda_fila), ''), l.moneda_carga, 'USD'),
    'Mercantil'
        || '|' || COALESCE(NULLIF(TRIM(b.ref_banco_norm), ''), b.referencia_banco)
        || '|' || COALESCE(to_char(b.fecha_banco, 'YYYY-MM-DD'), '')
        || '|' || CASE
            WHEN COALESCE(b.monto_banco_original, b.monto_banco) IS NULL THEN ''
            ELSE TRIM(to_char(COALESCE(b.monto_banco_original, b.monto_banco), 'FM999999999990.00'))
        END
        AS clave_natural,
    l.id,
    l.archivo_nombre,
    NOW(),
    NOW()
FROM conciliacion_banco_ocr_banco b
JOIN conciliacion_banco_ocr_lote l ON l.id = b.lote_id
WHERE b.lote_id = 50
ON CONFLICT (clave_natural) DO UPDATE SET
    banco = EXCLUDED.banco,
    fecha = EXCLUDED.fecha,
    referencia = EXCLUDED.referencia,
    referencia_norm = EXCLUDED.referencia_norm,
    monto = EXCLUDED.monto,
    moneda = EXCLUDED.moneda,
    lote_origen_id = EXCLUDED.lote_origen_id,
    archivo_nombre = COALESCE(EXCLUDED.archivo_nombre, conciliacion_banco_extracto.archivo_nombre),
    actualizado_en = EXCLUDED.actualizado_en;
*/
