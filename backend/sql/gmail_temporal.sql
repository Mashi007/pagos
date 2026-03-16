-- Tabla gmail_temporal para descarga Excel.
-- Cada procesamiento Gmail inserta aqui a continuacion del ultimo.
-- GET /pagos/gmail/download-excel-temporal genera Excel y luego vacia esta tabla (DELETE).

CREATE TABLE IF NOT EXISTS gmail_temporal (
    id SERIAL PRIMARY KEY,
    correo_origen VARCHAR(255) NOT NULL,
    asunto VARCHAR(500),
    fecha_pago VARCHAR(100),
    cedula VARCHAR(50),
    monto VARCHAR(100),
    numero_referencia VARCHAR(200),
    drive_file_id VARCHAR(100),
    drive_link VARCHAR(500),
    drive_email_link VARCHAR(500),
    sheet_name VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_gmail_temporal_created_at ON gmail_temporal (created_at);

COMMENT ON TABLE gmail_temporal IS 'Datos Gmail para exportar a Excel; se vacia al descargar (download-excel-temporal).';
