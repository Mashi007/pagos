-- Sincronización de la pestaña CONCILIACIÓN (Google Sheets) → PostgreSQL.
-- Último snapshot: cada sync exitoso reemplaza filas en conciliacion_sheet_rows.
-- Historial ligero: una fila por ejecución en conciliacion_sheet_sync_run (no guarda copias completas pasadas).

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
