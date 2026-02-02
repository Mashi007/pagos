-- =============================================================================
-- SQL para crear tablas del backend (PostgreSQL)
-- Ejecutar en orden si NO usas Base.metadata.create_all() al arrancar la app.
-- La tabla "clientes" ya debe existir (tú la tienes).
-- =============================================================================

-- 1) PRESTAMOS (depende de clientes)
-- ----------------------------------
CREATE TABLE IF NOT EXISTS prestamos (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    total_financiamiento NUMERIC(14, 2) NOT NULL,
    monto_programado NUMERIC(14, 2),
    monto_pagado NUMERIC(14, 2),
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    concesionario VARCHAR(255),
    modelo VARCHAR(255),
    analista VARCHAR(255),
    fecha_creacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_prestamos_id ON prestamos (id);
CREATE INDEX IF NOT EXISTS ix_prestamos_cliente_id ON prestamos (cliente_id);
CREATE INDEX IF NOT EXISTS ix_prestamos_estado ON prestamos (estado);
CREATE INDEX IF NOT EXISTS ix_prestamos_concesionario ON prestamos (concesionario);
CREATE INDEX IF NOT EXISTS ix_prestamos_modelo ON prestamos (modelo);
CREATE INDEX IF NOT EXISTS ix_prestamos_analista ON prestamos (analista);

-- 2) CUOTAS (depende de clientes) – notificaciones por fecha_vencimiento y mora
-- -------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cuotas (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    numero_cuota INTEGER NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    monto NUMERIC(14, 2) NOT NULL,
    pagado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_pago TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_cuotas_id ON cuotas (id);
CREATE INDEX IF NOT EXISTS ix_cuotas_cliente_id ON cuotas (cliente_id);
CREATE INDEX IF NOT EXISTS ix_cuotas_fecha_vencimiento ON cuotas (fecha_vencimiento);
CREATE INDEX IF NOT EXISTS ix_cuotas_pagado ON cuotas (pagado);

-- 3) TICKETS (depende de clientes) – CRM
-- ---------------------------------------
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    descripcion TEXT NOT NULL,
    cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'abierto',
    prioridad VARCHAR(20) NOT NULL DEFAULT 'media',
    tipo VARCHAR(30) NOT NULL DEFAULT 'consulta',
    asignado_a VARCHAR(255),
    asignado_a_id INTEGER,
    escalado_a_id INTEGER,
    escalado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_limite TIMESTAMP WITHOUT TIME ZONE,
    conversacion_whatsapp_id INTEGER,
    comunicacion_email_id INTEGER,
    creado_por_id INTEGER,
    fecha_creacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archivos TEXT
);
CREATE INDEX IF NOT EXISTS ix_tickets_id ON tickets (id);
CREATE INDEX IF NOT EXISTS ix_tickets_cliente_id ON tickets (cliente_id);
CREATE INDEX IF NOT EXISTS ix_tickets_estado ON tickets (estado);

-- 4) PAGOS_WHATSAPP – imágenes recibidas por WhatsApp (fecha, cedula_cliente, imagen)
-- -----------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pagos_whatsapp (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cedula_cliente VARCHAR(20),
    imagen BYTEA NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_pagos_whatsapp_id ON pagos_whatsapp (id);
CREATE INDEX IF NOT EXISTS ix_pagos_whatsapp_cedula_cliente ON pagos_whatsapp (cedula_cliente);

-- 5) CONFIGURACION – clave-valor para persistir config (email, etc.)
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS configuracion (
    clave VARCHAR(100) PRIMARY KEY,
    valor TEXT
);

-- =============================================================================
-- MIGRACIÓN: Añadir concesionario y modelo a prestamos (si la tabla ya existía sin las columnas)
-- =============================================================================
-- ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS concesionario VARCHAR(255);
-- CREATE INDEX IF NOT EXISTS ix_prestamos_concesionario ON prestamos (concesionario);
-- ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS modelo VARCHAR(255);
-- CREATE INDEX IF NOT EXISTS ix_prestamos_modelo ON prestamos (modelo);
-- ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS analista VARCHAR(255);
-- CREATE INDEX IF NOT EXISTS ix_prestamos_analista ON prestamos (analista);

-- =============================================================================
-- MIGRACIÓN OPCIONAL: Si en Render falla "column clientes.total_financiamiento
-- does not exist", es porque la BD no tiene estas columnas pero el código
-- desplegado (o una versión anterior del modelo) las espera.
-- Opción A: Ejecutar este ALTER en la BD de Render (psql o panel de Render):
-- Opción B: Redesplegar el código actual (el modelo Cliente ya NO las usa).
-- =============================================================================
-- ALTER TABLE clientes ADD COLUMN IF NOT EXISTS total_financiamiento NUMERIC(14, 2) NULL;
-- ALTER TABLE clientes ADD COLUMN IF NOT EXISTS dias_mora INTEGER NULL DEFAULT 0;
