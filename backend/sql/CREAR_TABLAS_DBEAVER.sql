-- =============================================================================
-- SQL para crear todas las tablas del sistema (PostgreSQL)
-- Ejecutar en DBeaver en el orden indicado (respetar dependencias FK).
-- Base de datos: PostgreSQL.
-- =============================================================================

-- 1) CLIENTES (tabla base; sin FK a otras tablas del sistema)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL,
    nombres VARCHAR(100) NOT NULL,
    telefono VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    direccion TEXT NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    ocupacion VARCHAR(100) NOT NULL,
    estado VARCHAR(20) NOT NULL,
    fecha_registro TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuario_registro VARCHAR(50) NOT NULL,
    notas TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_clientes_id ON clientes (id);
CREATE INDEX IF NOT EXISTS ix_clientes_cedula ON clientes (cedula);
CREATE INDEX IF NOT EXISTS ix_clientes_estado ON clientes (estado);

-- 2) USUARIOS (auth; sin FK a clientes/prestamos)
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL DEFAULT '',
    cargo VARCHAR(100),
    rol VARCHAR(20) NOT NULL DEFAULT 'operativo',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios (email);

-- 3) PRESTAMOS (depende de clientes)
-- -----------------------------------
CREATE TABLE IF NOT EXISTS prestamos (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    cedula VARCHAR(20) NOT NULL,
    nombres VARCHAR(255) NOT NULL,
    total_financiamiento NUMERIC(14, 2) NOT NULL,
    fecha_requerimiento DATE NOT NULL,
    modalidad_pago VARCHAR(50) NOT NULL,
    numero_cuotas INTEGER NOT NULL,
    cuota_periodo NUMERIC(14, 2) NOT NULL,
    tasa_interes NUMERIC(10, 4) NOT NULL DEFAULT 0.00,
    fecha_base_calculo DATE,
    producto VARCHAR(255) NOT NULL,
    estado VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
    usuario_proponente VARCHAR(255) NOT NULL DEFAULT 'itmaster@rapicreditca.com',
    usuario_aprobador VARCHAR(255),
    observaciones TEXT DEFAULT 'No observaciones',
    informacion_desplegable BOOLEAN NOT NULL DEFAULT false,
    fecha_registro TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_aprobacion TIMESTAMP WITHOUT TIME ZONE,
    fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    concesionario VARCHAR(255),
    analista VARCHAR(255) NOT NULL,
    modelo_vehiculo VARCHAR(255),
    usuario_autoriza VARCHAR(255) DEFAULT 'operaciones@rapicreditca.com',
    ml_impago_nivel_riesgo_manual VARCHAR(50),
    ml_impago_probabilidad_manual NUMERIC(10, 4),
    concesionario_id INTEGER,
    analista_id INTEGER,
    modelo_vehiculo_id INTEGER,
    valor_activo NUMERIC(14, 2),
    ml_impago_nivel_riesgo_calculado VARCHAR(50),
    ml_impago_probabilidad_calculada NUMERIC(10, 4),
    ml_impago_calculado_en TIMESTAMP WITHOUT TIME ZONE,
    ml_impago_modelo_id INTEGER,
    requiere_revision BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS ix_prestamos_id ON prestamos (id);
CREATE INDEX IF NOT EXISTS ix_prestamos_cliente_id ON prestamos (cliente_id);
CREATE INDEX IF NOT EXISTS ix_prestamos_estado ON prestamos (estado);
CREATE INDEX IF NOT EXISTS ix_prestamos_concesionario ON prestamos (concesionario);
CREATE INDEX IF NOT EXISTS ix_prestamos_modelo_vehiculo ON prestamos (modelo_vehiculo);
CREATE INDEX IF NOT EXISTS ix_prestamos_analista ON prestamos (analista);

-- 4) PAGOS (depende de prestamos)
-- --------------------------------
CREATE TABLE IF NOT EXISTS pagos (
    id SERIAL PRIMARY KEY,
    prestamo_id INTEGER REFERENCES prestamos(id) ON DELETE SET NULL,
    cedula VARCHAR(20),
    fecha_pago TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    monto_pagado NUMERIC(14, 2) NOT NULL,
    numero_documento VARCHAR(100) UNIQUE,
    institucion_bancaria VARCHAR(255),
    estado VARCHAR(30),
    fecha_registro TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_conciliacion TIMESTAMP WITHOUT TIME ZONE,
    conciliado BOOLEAN NOT NULL DEFAULT false,
    verificado_concordancia VARCHAR(10) NOT NULL DEFAULT '',
    usuario_registro VARCHAR(255),
    notas TEXT,
    documento_nombre VARCHAR(255),
    documento_tipo VARCHAR(50),
    documento_ruta VARCHAR(255),
    referencia_pago VARCHAR(100) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_pagos_id ON pagos (id);
CREATE INDEX IF NOT EXISTS ix_pagos_cedula ON pagos (cedula);
CREATE INDEX IF NOT EXISTS ix_pagos_prestamo_id ON pagos (prestamo_id);
CREATE INDEX IF NOT EXISTS ix_pagos_estado ON pagos (estado);
CREATE INDEX IF NOT EXISTS ix_pagos_fecha_pago ON pagos (fecha_pago);

-- 5) CUOTAS (depende de prestamos, pagos, clientes)
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS cuotas (
    id SERIAL PRIMARY KEY,
    prestamo_id INTEGER NOT NULL REFERENCES prestamos(id) ON DELETE CASCADE,
    pago_id INTEGER REFERENCES pagos(id) ON DELETE SET NULL,
    cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
    numero_cuota INTEGER NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    fecha_pago DATE,
    monto_cuota NUMERIC(14, 2) NOT NULL,
    saldo_capital_inicial NUMERIC(14, 2) NOT NULL,
    saldo_capital_final NUMERIC(14, 2) NOT NULL,
    monto_capital NUMERIC(14, 2) NOT NULL DEFAULT 0,
    monto_interes NUMERIC(14, 2) NOT NULL DEFAULT 0,
    total_pagado NUMERIC(14, 2),
    dias_mora INTEGER,
    dias_morosidad INTEGER,
    estado VARCHAR(20) NOT NULL,
    observaciones VARCHAR(255),
    es_cuota_especial BOOLEAN,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_cuotas_id ON cuotas (id);
CREATE INDEX IF NOT EXISTS ix_cuotas_prestamo_id ON cuotas (prestamo_id);
CREATE INDEX IF NOT EXISTS ix_cuotas_pago_id ON cuotas (pago_id);
CREATE INDEX IF NOT EXISTS ix_cuotas_cliente_id ON cuotas (cliente_id);
CREATE INDEX IF NOT EXISTS ix_cuotas_fecha_vencimiento ON cuotas (fecha_vencimiento);

-- 6) CUOTA_PAGOS (depende de cuotas, pagos)
-- -----------------------------------------
CREATE TABLE IF NOT EXISTS cuota_pagos (
    id SERIAL PRIMARY KEY,
    cuota_id INTEGER NOT NULL REFERENCES cuotas(id) ON DELETE CASCADE,
    pago_id INTEGER NOT NULL REFERENCES pagos(id) ON DELETE CASCADE,
    monto_aplicado NUMERIC(14, 2) NOT NULL,
    fecha_aplicacion TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    orden_aplicacion INTEGER NOT NULL DEFAULT 0,
    es_pago_completo BOOLEAN NOT NULL DEFAULT false,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (cuota_id, pago_id)
);
CREATE INDEX IF NOT EXISTS idx_cuota_pagos_cuota_id ON cuota_pagos (cuota_id);
CREATE INDEX IF NOT EXISTS idx_cuota_pagos_pago_id ON cuota_pagos (pago_id);

-- 7) PAGOS_CON_ERRORES (depende de prestamos)
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS pagos_con_errores (
    id SERIAL PRIMARY KEY,
    prestamo_id INTEGER REFERENCES prestamos(id) ON DELETE SET NULL,
    cedula VARCHAR(20),
    fecha_pago TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    monto_pagado NUMERIC(14, 2) NOT NULL,
    numero_documento VARCHAR(100),
    institucion_bancaria VARCHAR(255),
    estado VARCHAR(30) DEFAULT 'PENDIENTE',
    fecha_registro TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_conciliacion TIMESTAMP WITHOUT TIME ZONE,
    conciliado BOOLEAN,
    verificado_concordancia VARCHAR(10) NOT NULL DEFAULT '',
    usuario_registro VARCHAR(255),
    notas TEXT,
    documento_nombre VARCHAR(255),
    documento_tipo VARCHAR(50),
    documento_ruta VARCHAR(255),
    referencia_pago VARCHAR(100) NOT NULL DEFAULT '',
    errores_descripcion JSONB,
    observaciones VARCHAR(255),
    fila_origen INTEGER
);
CREATE INDEX IF NOT EXISTS idx_pagos_con_errores_cedula ON pagos_con_errores (cedula);
CREATE INDEX IF NOT EXISTS idx_pagos_con_errores_fecha_pago ON pagos_con_errores (fecha_pago);

-- 8) REVISAR_PAGOS (depende de pagos)
-- ------------------------------------
CREATE TABLE IF NOT EXISTS revisar_pagos (
    id SERIAL PRIMARY KEY,
    pago_id INTEGER NOT NULL REFERENCES pagos(id) ON DELETE CASCADE,
    fecha_exportacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (pago_id)
);
CREATE INDEX IF NOT EXISTS idx_revisar_pagos_pago_id ON revisar_pagos (pago_id);

-- 9) CONFIGURACION (clave-valor; sin FK)
-- --------------------------------------
CREATE TABLE IF NOT EXISTS configuracion (
    clave VARCHAR(100) PRIMARY KEY,
    valor TEXT,
    valor_encriptado BYTEA
);

-- 10) TICKETS (depende de clientes)
-- ----------------------------------
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
    escalado BOOLEAN NOT NULL DEFAULT false,
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

-- 11) PAGOS_WHATSAPP (sin FK)
-- ---------------------------
CREATE TABLE IF NOT EXISTS pagos_whatsapp (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cedula_cliente VARCHAR(20),
    imagen BYTEA NOT NULL,
    link_imagen TEXT
);
CREATE INDEX IF NOT EXISTS ix_pagos_whatsapp_id ON pagos_whatsapp (id);
CREATE INDEX IF NOT EXISTS ix_pagos_whatsapp_cedula_cliente ON pagos_whatsapp (cedula_cliente);

-- 12) PAGOS_REPORTADOS (módulo Cobros; depende de usuarios)
-- --------------------------------------------------------
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
    monto NUMERIC(15, 2) NOT NULL,
    moneda VARCHAR(10) NOT NULL DEFAULT 'BS',
    comprobante BYTEA,
    comprobante_nombre VARCHAR(255),
    comprobante_tipo VARCHAR(100),
    recibo_pdf BYTEA,
    ruta_comprobante VARCHAR(512),
    ruta_recibo_pdf VARCHAR(512),
    observacion TEXT,
    correo_enviado_a VARCHAR(255),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    motivo_rechazo TEXT,
    usuario_gestion_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    gemini_coincide_exacto VARCHAR(10),
    gemini_comentario TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_pagos_reportados_referencia_interna ON pagos_reportados (referencia_interna);
CREATE INDEX IF NOT EXISTS ix_pagos_reportados_numero_cedula ON pagos_reportados (numero_cedula);
CREATE INDEX IF NOT EXISTS ix_pagos_reportados_estado ON pagos_reportados (estado);

-- 13) PAGOS_REPORTADOS_HISTORIAL (depende de pagos_reportados, usuarios)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pagos_reportados_historial (
    id SERIAL PRIMARY KEY,
    pago_reportado_id INTEGER NOT NULL REFERENCES pagos_reportados(id) ON DELETE CASCADE,
    estado_anterior VARCHAR(20),
    estado_nuevo VARCHAR(20) NOT NULL,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    usuario_email VARCHAR(255),
    motivo TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_pagos_reportados_historial_pago_reportado_id ON pagos_reportados_historial (pago_reportado_id);

-- =============================================================================
-- Fin. Tablas listadas en health/db: clientes, prestamos, cuotas, pagos,
-- pagos_con_errores, revisar_pagos, cuota_pagos, pagos_whatsapp, tickets,
-- pagos_reportados, usuarios.
-- =============================================================================
