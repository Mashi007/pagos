-- Espejo de alembic 024_finiquito_tablas (Finiquito: acceso OTP, casos, historial).
-- Preferir: alembic upgrade head desde backend/

CREATE TABLE IF NOT EXISTS finiquito_usuario_acceso (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_finiquito_usuario_acceso_cedula ON finiquito_usuario_acceso (cedula);
CREATE UNIQUE INDEX IF NOT EXISTS ix_finiquito_usuario_acceso_email ON finiquito_usuario_acceso (email);

CREATE TABLE IF NOT EXISTS finiquito_login_codigos (
    id SERIAL PRIMARY KEY,
    finiquito_usuario_id INTEGER NOT NULL REFERENCES finiquito_usuario_acceso(id) ON DELETE CASCADE,
    codigo VARCHAR(10) NOT NULL,
    expira_en TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    usado BOOLEAN NOT NULL DEFAULT false,
    creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_finiquito_login_codigos_usuario ON finiquito_login_codigos (finiquito_usuario_id);

CREATE TABLE IF NOT EXISTS finiquito_casos (
    id SERIAL PRIMARY KEY,
    prestamo_id INTEGER NOT NULL REFERENCES prestamos(id) ON DELETE CASCADE,
    cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
    cedula VARCHAR(20) NOT NULL,
    total_financiamiento NUMERIC(14, 2) NOT NULL,
    sum_total_pagado NUMERIC(14, 2) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'REVISION',
    ultimo_refresh_utc TIMESTAMP WITHOUT TIME ZONE,
    creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_finiquito_casos_estado CHECK (estado IN ('REVISION','ACEPTADO','RECHAZADO'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_finiquito_casos_prestamo_id ON finiquito_casos (prestamo_id);
CREATE INDEX IF NOT EXISTS ix_finiquito_casos_cliente_id ON finiquito_casos (cliente_id);
CREATE INDEX IF NOT EXISTS ix_finiquito_casos_cedula ON finiquito_casos (cedula);
CREATE INDEX IF NOT EXISTS ix_finiquito_casos_estado ON finiquito_casos (estado);

CREATE TABLE IF NOT EXISTS finiquito_estado_historial (
    id SERIAL PRIMARY KEY,
    caso_id INTEGER NOT NULL REFERENCES finiquito_casos(id) ON DELETE CASCADE,
    estado_anterior VARCHAR(20),
    estado_nuevo VARCHAR(20) NOT NULL,
    user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    finiquito_usuario_id INTEGER REFERENCES finiquito_usuario_acceso(id) ON DELETE SET NULL,
    actor_tipo VARCHAR(20) NOT NULL,
    creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_finiquito_estado_historial_caso_id ON finiquito_estado_historial (caso_id);
