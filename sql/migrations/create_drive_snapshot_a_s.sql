-- Tabla drive: snapshot plano de la hoja CONCILIACIÓN (Google Sheets), columnas A..S por fila de datos.
-- Se rellena en cada sync exitoso (app.services.conciliacion_sheet_sync.run_sync_to_db), mismo origen que conciliacion_sheet_rows.
-- Job diario: 04:01 America/Caracas vía APScheduler si ENABLE_AUTOMATIC_SCHEDULED_JOBS=true (ver app/core/scheduler.py).

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
