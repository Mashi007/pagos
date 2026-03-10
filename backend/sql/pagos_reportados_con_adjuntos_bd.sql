-- =============================================================================
-- Módulo Cobros: pagos reportados con datos e imágenes en BD
-- Todos los datos (incl. comprobante e imagen/PDF del recibo) se almacenan en BD.
-- =============================================================================

-- Opción A: Si la tabla pagos_reportados NO existe, crear desde cero:
-- (Descomentar si aplica)

/*
CREATE TABLE IF NOT EXISTS pagos_reportados (
    id SERIAL PRIMARY KEY,
    referencia_interna VARCHAR(32) NOT NULL UNIQUE,
    nombres VARCHAR(200) NOT NULL,
    apellidos VARCHAR(200) NOT NULL,
    tipo_cedula VARCHAR(2) NOT NULL,
    numero_cedula VARCHAR(13) NOT NULL,
    fecha_pago DATE NOT NULL,
    institucion_financiera VARCHAR(100) NOT NULL,
    numero_operacion VARCHAR(100) NOT NULL,
    monto NUMERIC(15,2) NOT NULL,
    moneda VARCHAR(10) NOT NULL DEFAULT 'BS',
    -- Comprobante (imagen/PDF) en BD
    comprobante BYTEA,
    comprobante_nombre VARCHAR(255),
    comprobante_tipo VARCHAR(100),
    -- Recibo PDF generado en BD
    recibo_pdf BYTEA,
    -- Rutas legacy (opcionales, para compatibilidad)
    ruta_comprobante VARCHAR(512),
    ruta_recibo_pdf VARCHAR(512),
    observacion TEXT,
    correo_enviado_a VARCHAR(255),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    motivo_rechazo TEXT,
    usuario_gestion_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    gemini_coincide_exacto VARCHAR(10),
    gemini_comentario TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_pagos_reportados_referencia ON pagos_reportados(referencia_interna);
CREATE INDEX ix_pagos_reportados_numero_cedula ON pagos_reportados(numero_cedula);
CREATE INDEX ix_pagos_reportados_tipo_cedula ON pagos_reportados(tipo_cedula);
CREATE INDEX ix_pagos_reportados_estado ON pagos_reportados(estado);
CREATE INDEX ix_pagos_reportados_created_at ON pagos_reportados(created_at);
-- Búsqueda por cédula concatenada (tipo+numero) y por solo número
CREATE INDEX ix_pagos_reportados_cedula_concat ON pagos_reportados((tipo_cedula || numero_cedula));

CREATE TABLE IF NOT EXISTS pagos_reportados_historial (
    id SERIAL PRIMARY KEY,
    pago_reportado_id INTEGER NOT NULL REFERENCES pagos_reportados(id) ON DELETE CASCADE,
    estado_anterior VARCHAR(20),
    estado_nuevo VARCHAR(20) NOT NULL,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    usuario_email VARCHAR(255),
    motivo TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_pagos_reportados_historial_pago_id ON pagos_reportados_historial(pago_reportado_id);
*/

-- =============================================================================
-- Opción B: Si la tabla pagos_reportados YA existe (ej. creada por 009),
-- añadir columnas para almacenar comprobante y recibo en BD:
-- =============================================================================

ALTER TABLE pagos_reportados
  ADD COLUMN IF NOT EXISTS comprobante BYTEA,
  ADD COLUMN IF NOT EXISTS comprobante_nombre VARCHAR(255),
  ADD COLUMN IF NOT EXISTS comprobante_tipo VARCHAR(100),
  ADD COLUMN IF NOT EXISTS recibo_pdf BYTEA;

-- Hacer opcionales las rutas (por si se migra todo a BD)
ALTER TABLE pagos_reportados
  ALTER COLUMN ruta_comprobante DROP NOT NULL;

-- Índice para búsqueda por cédula (todas las concatenaciones posibles)
CREATE INDEX IF NOT EXISTS ix_pagos_reportados_cedula_concat
  ON pagos_reportados((tipo_cedula || numero_cedula));

COMMENT ON COLUMN pagos_reportados.comprobante IS 'Contenido binario del comprobante (imagen o PDF) subido por el usuario';
COMMENT ON COLUMN pagos_reportados.recibo_pdf IS 'Contenido binario del recibo PDF generado';
COMMENT ON COLUMN pagos_reportados.comprobante_nombre IS 'Nombre original del archivo comprobante';
COMMENT ON COLUMN pagos_reportados.comprobante_tipo IS 'MIME type del comprobante (image/jpeg, application/pdf, etc.)';
