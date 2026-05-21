-- Modulo Cobranzas: casos de gestion, imagenes por prestamo (max 10) y bitacora de acuerdos.
-- Ejecutar en la BD de produccion/staging antes de usar el modulo.

CREATE TABLE IF NOT EXISTS cobranza_casos (
    id SERIAL PRIMARY KEY,
    prestamo_id INTEGER NOT NULL REFERENCES prestamos(id) ON DELETE CASCADE,
    cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
    cedula VARCHAR(20) NOT NULL,
    nombres VARCHAR(255),
    motivo VARCHAR(40) NOT NULL DEFAULT 'OTRO',
    estado VARCHAR(20) NOT NULL DEFAULT 'ABIERTO',
    observaciones TEXT,
    monto_financiamiento NUMERIC(14, 2),
    saldo_pendiente_snapshot NUMERIC(14, 2),
    cuotas_atrasadas_snapshot INTEGER,
    user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_cobranza_caso_prestamo_abierto
    ON cobranza_casos (prestamo_id)
    WHERE estado IN ('ABIERTO', 'EN_GESTION');

CREATE INDEX IF NOT EXISTS ix_cobranza_casos_cedula ON cobranza_casos (cedula);
CREATE INDEX IF NOT EXISTS ix_cobranza_casos_estado ON cobranza_casos (estado);

CREATE TABLE IF NOT EXISTS cobranza_imagenes (
    id VARCHAR(32) PRIMARY KEY,
    caso_id INTEGER NOT NULL REFERENCES cobranza_casos(id) ON DELETE CASCADE,
    content_type VARCHAR(80) NOT NULL,
    imagen_data BYTEA NOT NULL,
    descripcion VARCHAR(255),
    user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_cobranza_imagenes_caso ON cobranza_imagenes (caso_id);

CREATE TABLE IF NOT EXISTS cobranza_acuerdos (
    id SERIAL PRIMARY KEY,
    caso_id INTEGER NOT NULL REFERENCES cobranza_casos(id) ON DELETE CASCADE,
    fecha_acuerdo DATE NOT NULL,
    fecha_compromiso DATE,
    mensaje TEXT NOT NULL,
    cantidad NUMERIC(14, 2),
    moneda VARCHAR(10) NOT NULL DEFAULT 'USD',
    notas TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    monto_compromiso NUMERIC(14, 2),
    user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_cobranza_acuerdos_caso ON cobranza_acuerdos (caso_id);
