-- ============================================
-- SCRIPT DE MIGRACIÓN: MÓDULO DE PRÉSTAMOS
-- ============================================
-- Fecha: 2025-10-27
-- Descripción: Crea las tablas necesarias para el módulo de préstamos
-- Ejecutar en: DBeaver (Producción)
-- ============================================

-- ============================================
-- PASO 1: VERIFICAR Y ELIMINAR TABLAS EXISTENTES (Si existen)
-- ============================================
DROP TABLE IF EXISTS prestamos_evaluacion CASCADE;
DROP TABLE IF EXISTS prestamos_auditoria CASCADE;
DROP TABLE IF EXISTS prestamos CASCADE;

-- ============================================
-- PASO 2: CREAR TABLA prestamos
-- ============================================
CREATE TABLE prestamos (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL,
    cedula VARCHAR(20) NOT NULL,
    nombres VARCHAR(100) NOT NULL,
    total_financiamiento NUMERIC(15, 2) NOT NULL,
    fecha_requerimiento DATE NOT NULL,
    modalidad_pago VARCHAR(20) NOT NULL,
    numero_cuotas INTEGER NOT NULL,
    cuota_periodo NUMERIC(15, 2) NOT NULL,
    tasa_interes NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    fecha_base_calculo DATE,
    producto VARCHAR(100) NOT NULL,
    producto_financiero VARCHAR(100) NOT NULL,
    concesionario VARCHAR(100),
    analista VARCHAR(100),
    modelo_vehiculo VARCHAR(100),
    usuario_autoriza VARCHAR(100),
    estado VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    usuario_proponente VARCHAR(100) NOT NULL,
    usuario_aprobador VARCHAR(100),
    observaciones TEXT,
    informacion_desplegable BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_aprobacion TIMESTAMP,
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- PASO 3: CREAR ÍNDICES PARA prestamos
-- ============================================
CREATE INDEX ix_prestamos_cliente_id ON prestamos(cliente_id);
CREATE INDEX ix_prestamos_cedula ON prestamos(cedula);
CREATE INDEX ix_prestamos_estado ON prestamos(estado);

-- ============================================
-- PASO 4: CREAR TABLA prestamos_auditoria
-- ============================================
CREATE TABLE prestamos_auditoria (
    id SERIAL PRIMARY KEY,
    prestamo_id INTEGER NOT NULL,
    cedula VARCHAR(20) NOT NULL,
    usuario VARCHAR(100) NOT NULL,
    fecha_cambio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    campo_modificado VARCHAR(100) NOT NULL,
    valor_anterior TEXT,
    valor_nuevo TEXT,
    accion VARCHAR(50) NOT NULL,
    estado_anterior VARCHAR(20),
    estado_nuevo VARCHAR(20),
    observaciones TEXT
);

-- ============================================
-- PASO 5: CREAR ÍNDICES PARA prestamos_auditoria
-- ============================================
CREATE INDEX ix_prestamos_auditoria_prestamo_id ON prestamos_auditoria(prestamo_id);

-- ============================================
-- PASO 6: CREAR TABLA prestamos_evaluacion
-- ============================================
CREATE TABLE prestamos_evaluacion (
    id SERIAL PRIMARY KEY,
    prestamo_id INTEGER NOT NULL,
    -- Criterio 1: Ratio de Endeudamiento (25%)
    ratio_endeudamiento_puntos NUMERIC(5, 2) NOT NULL DEFAULT 0,
    ratio_endeudamiento_calculo NUMERIC(10, 4) NOT NULL DEFAULT 0,
    -- Criterio 2: Ratio de Cobertura (20%)
    ratio_cobertura_puntos NUMERIC(5, 2) NOT NULL DEFAULT 0,
    ratio_cobertura_calculo NUMERIC(10, 4) NOT NULL DEFAULT 0,
    -- Criterio 3: Historial Crediticio (20%)
    historial_crediticio_puntos NUMERIC(5, 2) NOT NULL DEFAULT 0,
    historial_crediticio_descripcion VARCHAR(50),
    -- Criterio 4: Estabilidad Laboral (15%)
    estabilidad_laboral_puntos NUMERIC(5, 2) NOT NULL DEFAULT 0,
    anos_empleo NUMERIC(4, 2),
    -- Criterio 5: Tipo de Empleo (10%)
    tipo_empleo_puntos NUMERIC(5, 2) NOT NULL DEFAULT 0,
    tipo_empleo_descripcion VARCHAR(50),
    -- Criterio 6: Enganche y Garantías (10%)
    enganche_garantias_puntos NUMERIC(5, 2) NOT NULL DEFAULT 0,
    enganche_garantias_calculo NUMERIC(10, 4) NOT NULL DEFAULT 0,
    -- Puntuación Total y Clasificación
    puntuacion_total NUMERIC(5, 2) NOT NULL DEFAULT 0,
    clasificacion_riesgo VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    decision_final VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    -- Condiciones según Riesgo
    tasa_interes_aplicada NUMERIC(5, 2),
    plazo_maximo INTEGER,
    enganche_minimo NUMERIC(5, 2),
    requisitos_adicionales VARCHAR(200),
    observaciones_evaluacion TEXT
);

-- ============================================
-- PASO 7: CREAR ÍNDICES PARA prestamos_evaluacion
-- ============================================
CREATE INDEX ix_prestamos_evaluacion_prestamo_id ON prestamos_evaluacion(prestamo_id);

-- ============================================
-- PASO 8: AGREGAR CONSTRAINTS Y RELACIONES
-- ============================================
-- Nota: Si tienes Foreign Keys definidas en clientes, puedes agregarlas aquí
-- ALTER TABLE prestamos ADD CONSTRAINT fk_prestamos_cliente 
--     FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE;

-- ============================================
-- PASO 9: VERIFICAR QUE LAS TABLAS SE CREARON CORRECTAMENTE
-- ============================================
SELECT 
    tablename,
    schemaname
FROM pg_tables
WHERE tablename IN ('prestamos', 'prestamos_auditoria', 'prestamos_evaluacion')
ORDER BY tablename;

-- ============================================
-- PASO 10: VERIFICAR ESTRUCTURA DE LAS TABLAS
-- ============================================
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name IN ('prestamos', 'prestamos_auditoria', 'prestamos_evaluacion')
ORDER BY table_name, ordinal_position;

-- ============================================
-- FIN DEL SCRIPT
-- ============================================

