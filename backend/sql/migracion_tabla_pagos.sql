-- Tabla pagos: registro de pagos (módulo Pagos en /pagos/pagos).
-- Conectar frontend con GET/POST/PUT/DELETE /api/v1/pagos/

CREATE TABLE IF NOT EXISTS pagos (
    id SERIAL PRIMARY KEY,
    cedula_cliente VARCHAR(20) NOT NULL,
    prestamo_id INTEGER REFERENCES prestamos(id) ON DELETE SET NULL,
    fecha_pago DATE NOT NULL,
    monto_pagado NUMERIC(14, 2) NOT NULL,
    numero_documento VARCHAR(100) NOT NULL,
    institucion_bancaria VARCHAR(255),
    estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
    fecha_registro TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    fecha_conciliacion TIMESTAMP WITHOUT TIME ZONE,
    conciliado BOOLEAN NOT NULL DEFAULT FALSE,
    verificado_concordancia VARCHAR(10),
    usuario_registro VARCHAR(255) DEFAULT '',
    notas TEXT,
    documento_nombre VARCHAR(255),
    documento_tipo VARCHAR(50),
    documento_ruta TEXT
);

CREATE INDEX IF NOT EXISTS ix_pagos_id ON pagos (id);
CREATE INDEX IF NOT EXISTS ix_pagos_cedula_cliente ON pagos (cedula_cliente);
CREATE INDEX IF NOT EXISTS ix_pagos_prestamo_id ON pagos (prestamo_id);
CREATE INDEX IF NOT EXISTS ix_pagos_estado ON pagos (estado);
CREATE INDEX IF NOT EXISTS ix_pagos_fecha_pago ON pagos (fecha_pago);
