-- =============================================================================
-- Informes: tablas y objetos auxiliares (PostgreSQL)
-- =============================================================================
-- Los Excel del Centro de Reportes leen sobre todo tablas núcleo ya existentes
-- en la app: prestamos, cuotas, pagos, clientes, etc. (no se recrean aquí).
--
-- Este script agrupa SOLO lo que es específico de:
--   - Sincronización Google Sheets CONCILIACIÓN → BD (Fecha Drive, Clientes hoja,
--     Préstamos Drive, Análisis financiamiento, estado / diagnóstico hoja).
--   - Snapshot plano columnas A..S (tabla drive).
--   - Carga asistida del informe Conciliación (Excel → conciliacion_temporal).
--   - Caché del reporte Contable (reporte_contable_cache; requiere cuotas).
--
-- Idempotente: CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS.
-- Ejecutar con un rol que pueda crear tablas e índices en el esquema objetivo.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1) Hoja CONCILIACIÓN (JSON por fila + metadatos + log de sync)
-- (equivalente a sql/migrations/conciliacion_sheet_hoja.sql)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS conciliacion_sheet_meta (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    spreadsheet_id TEXT NOT NULL DEFAULT '',
    sheet_title TEXT NOT NULL DEFAULT '',
    headers JSONB NOT NULL DEFAULT '[]'::jsonb,
    header_row_index INTEGER NOT NULL DEFAULT 1,
    row_count INTEGER NOT NULL DEFAULT 0,
    col_count INTEGER NOT NULL DEFAULT 0,
    synced_at TIMESTAMPTZ,
    last_error TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO conciliacion_sheet_meta (id, spreadsheet_id, sheet_title, headers, header_row_index, row_count, col_count)
VALUES (1, '', '', '[]'::jsonb, 1, 0, 0)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS conciliacion_sheet_rows (
    row_index INTEGER NOT NULL,
    cells JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (row_index)
);

CREATE INDEX IF NOT EXISTS idx_conciliacion_sheet_rows_gin ON conciliacion_sheet_rows USING GIN (cells);

CREATE TABLE IF NOT EXISTS conciliacion_sheet_sync_run (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    message TEXT,
    row_count INTEGER NOT NULL DEFAULT 0,
    col_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_conciliacion_sheet_sync_run_started ON conciliacion_sheet_sync_run (started_at DESC);

-- -----------------------------------------------------------------------------
-- 2) Tabla drive: snapshot plano A..S (misma corrida de sync que rellena JSON)
-- (equivalente a sql/migrations/create_drive_snapshot_a_s.sql)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS drive (
    sheet_row_number INTEGER NOT NULL PRIMARY KEY,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    col_a TEXT,
    col_b TEXT,
    col_c TEXT,
    col_d TEXT,
    col_e TEXT,
    col_f TEXT,
    col_g TEXT,
    col_h TEXT,
    col_i TEXT,
    col_j TEXT,
    col_k TEXT,
    col_l TEXT,
    col_m TEXT,
    col_n TEXT,
    col_o TEXT,
    col_p TEXT,
    col_q TEXT,
    col_r TEXT,
    col_s TEXT
);

CREATE INDEX IF NOT EXISTS idx_drive_synced_at ON drive (synced_at DESC);

-- -----------------------------------------------------------------------------
-- 3) Conciliación masiva desde Excel (informe Conciliación en UI)
-- (equivalente a sql/conciliacion_temporal.sql)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS conciliacion_temporal (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL,
    total_financiamiento NUMERIC(14, 2) NOT NULL,
    total_abonos NUMERIC(14, 2) NOT NULL,
    columna_e VARCHAR(255) NULL,
    columna_f VARCHAR(255) NULL,
    creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_conciliacion_temporal_cedula ON conciliacion_temporal (cedula);

COMMENT ON TABLE conciliacion_temporal IS
    'Datos de Excel de conciliación por cédula; se eliminan al descargar el reporte.';

-- -----------------------------------------------------------------------------
-- 4) Caché del reporte Contable (app.models.reporte_contable_cache)
-- Requiere que exista la tabla cuotas (FK cuota_id → cuotas.id).
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS reporte_contable_cache (
    id SERIAL PRIMARY KEY,
    cuota_id INTEGER NOT NULL UNIQUE REFERENCES cuotas (id) ON DELETE CASCADE,
    cedula VARCHAR(20) NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    tipo_documento VARCHAR(50) NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    fecha_pago DATE NOT NULL,
    importe_md NUMERIC(14, 2) NOT NULL,
    moneda_documento VARCHAR(10) NOT NULL DEFAULT 'USD',
    tasa NUMERIC(14, 4) NOT NULL,
    importe_ml NUMERIC(14, 2) NOT NULL,
    moneda_local VARCHAR(10) NOT NULL DEFAULT 'Bs.',
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_reporte_contable_cache_cuota_id ON reporte_contable_cache (cuota_id);

CREATE INDEX IF NOT EXISTS ix_reporte_contable_cache_cedula ON reporte_contable_cache (cedula);

CREATE INDEX IF NOT EXISTS ix_reporte_contable_cache_fecha_pago ON reporte_contable_cache (fecha_pago);

CREATE INDEX IF NOT EXISTS idx_reporte_contable_cache_fecha_cedula ON reporte_contable_cache (fecha_pago, cedula);

COMMENT ON TABLE reporte_contable_cache IS
    'Caché del Excel contable: una fila por cuota con pago; histórico fijo salvo ventana reciente (ver backend).';
