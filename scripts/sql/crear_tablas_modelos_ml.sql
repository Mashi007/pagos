-- ============================================================
-- SQL PARA CREAR TABLAS DE MODELOS ML
-- ============================================================
-- Este script crea las tablas necesarias para almacenar
-- metadatos de modelos de machine learning
-- ============================================================

-- ============================================================
-- TABLA: modelos_riesgo
-- Descripción: Almacena metadatos de modelos ML de riesgo crediticio
-- ============================================================

CREATE TABLE IF NOT EXISTS modelos_riesgo (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    algoritmo VARCHAR(100) NOT NULL,
    
    -- Métricas de rendimiento
    accuracy FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    roc_auc FLOAT,
    
    -- Información de entrenamiento
    ruta_archivo VARCHAR(500) NOT NULL,
    total_datos_entrenamiento INTEGER,
    total_datos_test INTEGER,
    
    -- Parámetros de entrenamiento
    test_size FLOAT,
    random_state INTEGER,
    
    -- Estado
    activo BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Relación con usuario
    usuario_id INTEGER,
    
    -- Metadatos adicionales
    descripcion TEXT,
    features_usadas TEXT,
    
    -- Auditoría
    entrenado_en TIMESTAMP NOT NULL DEFAULT NOW(),
    activado_en TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Foreign key
    CONSTRAINT fk_modelos_riesgo_usuario 
        FOREIGN KEY (usuario_id) 
        REFERENCES users(id)
);

-- Índices para modelos_riesgo
CREATE INDEX IF NOT EXISTS ix_modelos_riesgo_id ON modelos_riesgo(id);
CREATE INDEX IF NOT EXISTS ix_modelos_riesgo_activo ON modelos_riesgo(activo);
CREATE INDEX IF NOT EXISTS ix_modelos_riesgo_entrenado_en ON modelos_riesgo(entrenado_en);

-- ============================================================
-- TABLA: modelos_impago_cuotas
-- Descripción: Almacena metadatos de modelos ML de predicción de impago de cuotas
-- ============================================================

CREATE TABLE IF NOT EXISTS modelos_impago_cuotas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    algoritmo VARCHAR(100) NOT NULL,
    
    -- Métricas de rendimiento
    accuracy FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    roc_auc FLOAT,
    
    -- Información de entrenamiento
    ruta_archivo VARCHAR(500) NOT NULL,
    total_datos_entrenamiento INTEGER,
    total_datos_test INTEGER,
    
    -- Parámetros de entrenamiento
    test_size FLOAT,
    random_state INTEGER,
    
    -- Estado
    activo BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Relación con usuario
    usuario_id INTEGER,
    
    -- Metadatos adicionales
    descripcion TEXT,
    features_usadas TEXT,
    
    -- Auditoría
    entrenado_en TIMESTAMP NOT NULL DEFAULT NOW(),
    activado_en TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Foreign key
    CONSTRAINT fk_modelos_impago_cuotas_usuario 
        FOREIGN KEY (usuario_id) 
        REFERENCES users(id)
);

-- Índices para modelos_impago_cuotas
CREATE INDEX IF NOT EXISTS ix_modelos_impago_cuotas_id ON modelos_impago_cuotas(id);
CREATE INDEX IF NOT EXISTS ix_modelos_impago_cuotas_activo ON modelos_impago_cuotas(activo);
CREATE INDEX IF NOT EXISTS ix_modelos_impago_cuotas_entrenado_en ON modelos_impago_cuotas(entrenado_en);

-- ============================================================
-- COMENTARIOS EN LAS TABLAS
-- ============================================================

COMMENT ON TABLE modelos_riesgo IS 'Almacena metadatos de modelos ML de riesgo crediticio';
COMMENT ON TABLE modelos_impago_cuotas IS 'Almacena metadatos de modelos ML de predicción de impago de cuotas';

COMMENT ON COLUMN modelos_riesgo.ruta_archivo IS 'Ruta al archivo .pkl del modelo entrenado';
COMMENT ON COLUMN modelos_riesgo.activo IS 'Indica si este modelo está activo y se usa para predicciones';
COMMENT ON COLUMN modelos_riesgo.features_usadas IS 'Lista de features separadas por coma usadas en el entrenamiento';

COMMENT ON COLUMN modelos_impago_cuotas.ruta_archivo IS 'Ruta al archivo .pkl del modelo entrenado';
COMMENT ON COLUMN modelos_impago_cuotas.activo IS 'Indica si este modelo está activo y se usa para predicciones';
COMMENT ON COLUMN modelos_impago_cuotas.features_usadas IS 'Lista de features separadas por coma usadas en el entrenamiento';

-- ============================================================
-- VERIFICACIÓN
-- ============================================================

-- Verificar que las tablas se crearon correctamente
SELECT 
    'modelos_riesgo' AS tabla,
    COUNT(*) AS columnas
FROM information_schema.columns 
WHERE table_name = 'modelos_riesgo'
UNION ALL
SELECT 
    'modelos_impago_cuotas' AS tabla,
    COUNT(*) AS columnas
FROM information_schema.columns 
WHERE table_name = 'modelos_impago_cuotas';

