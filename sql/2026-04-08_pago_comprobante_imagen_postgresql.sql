-- Tabla para imagenes de comprobante subidas desde el formulario de registro de pago.
-- Si usa SQLAlchemy create_all en startup, la tabla se crea sola al desplegar con el modelo nuevo.
-- Ejecute manualmente solo si su entorno no corre create_all.

CREATE TABLE IF NOT EXISTS pago_comprobante_imagen (
    id VARCHAR(32) PRIMARY KEY,
    content_type VARCHAR(80) NOT NULL,
    imagen_data BYTEA NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
