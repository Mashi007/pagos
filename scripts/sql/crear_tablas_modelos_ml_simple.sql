-- ============================================================
-- SQL SIMPLE PARA CREAR TABLAS DE MODELOS ML
-- ============================================================
-- Ejecutar este script directamente en PostgreSQL
-- ============================================================

-- TABLA: modelos_riesgo
CREATE TABLE IF NOT EXISTS modelos_riesgo (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    algoritmo VARCHAR(100) NOT NULL,
    accuracy FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    roc_auc FLOAT,
    ruta_archivo VARCHAR(500) NOT NULL,
    total_datos_entrenamiento INTEGER,
    total_datos_test INTEGER,
    test_size FLOAT,
    random_state INTEGER,
    activo BOOLEAN NOT NULL DEFAULT FALSE,
    usuario_id INTEGER,
    descripcion TEXT,
    features_usadas TEXT,
    entrenado_en TIMESTAMP NOT NULL DEFAULT NOW(),
    activado_en TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_modelos_riesgo_usuario FOREIGN KEY (usuario_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS ix_modelos_riesgo_id ON modelos_riesgo(id);
CREATE INDEX IF NOT EXISTS ix_modelos_riesgo_activo ON modelos_riesgo(activo);
CREATE INDEX IF NOT EXISTS ix_modelos_riesgo_entrenado_en ON modelos_riesgo(entrenado_en);

-- TABLA: modelos_impago_cuotas
CREATE TABLE IF NOT EXISTS modelos_impago_cuotas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    algoritmo VARCHAR(100) NOT NULL,
    accuracy FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    roc_auc FLOAT,
    ruta_archivo VARCHAR(500) NOT NULL,
    total_datos_entrenamiento INTEGER,
    total_datos_test INTEGER,
    test_size FLOAT,
    random_state INTEGER,
    activo BOOLEAN NOT NULL DEFAULT FALSE,
    usuario_id INTEGER,
    descripcion TEXT,
    features_usadas TEXT,
    entrenado_en TIMESTAMP NOT NULL DEFAULT NOW(),
    activado_en TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_modelos_impago_cuotas_usuario FOREIGN KEY (usuario_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS ix_modelos_impago_cuotas_id ON modelos_impago_cuotas(id);
CREATE INDEX IF NOT EXISTS ix_modelos_impago_cuotas_activo ON modelos_impago_cuotas(activo);
CREATE INDEX IF NOT EXISTS ix_modelos_impago_cuotas_entrenado_en ON modelos_impago_cuotas(entrenado_en);

