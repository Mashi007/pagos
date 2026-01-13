-- ============================================
-- CREAR TABLA TEMPORAL PRESTAMOS (FORZAR CREACIÓN)
-- ============================================
-- Este script fuerza la creación de la tabla en el esquema PUBLIC
-- y asegura que sea visible en el índice de DBeaver
-- ============================================

-- Asegurar que estamos en el esquema correcto
SET search_path TO public;

-- Eliminar tabla si existe (en cualquier esquema)
DROP TABLE IF EXISTS public.prestamos_temporal CASCADE;

-- Crear tabla temporal en esquema PUBLIC explícitamente
CREATE TABLE public.prestamos_temporal (
    -- IDENTIFICACIÓN
    id SERIAL PRIMARY KEY,
    
    -- DATOS DEL CLIENTE (para mapeo)
    cliente_id INTEGER,  -- Se mapeará después de validar
    cedula VARCHAR(20) NOT NULL,  -- Cédula del cliente (clave para mapeo)
    nombres VARCHAR(100) NOT NULL,  -- Nombre del cliente
    
    -- DATOS DEL PRÉSTAMO
    valor_activo NUMERIC(15, 2),  -- Valor del activo (vehículo)
    total_financiamiento NUMERIC(15, 2) NOT NULL,  -- Monto total del préstamo
    fecha_requerimiento DATE NOT NULL,  -- Fecha que necesita el préstamo
    modalidad_pago VARCHAR(20) NOT NULL,  -- MENSUAL, QUINCENAL, SEMANAL
    numero_cuotas INTEGER NOT NULL,  -- Número de cuotas
    cuota_periodo NUMERIC(15, 2) NOT NULL,  -- Monto por cuota
    -- tasa_interes ELIMINADO - se usa 0.00 por defecto en la tabla final
    fecha_base_calculo DATE,  -- Fecha base para generar tabla de amortización
    
    -- PRODUCTO
    producto VARCHAR(100) NOT NULL,  -- Modelo de vehículo
    
    -- INFORMACIÓN ADICIONAL (LEGACY)
    concesionario VARCHAR(100),  -- Concesionario (legacy)
    analista VARCHAR(100) NOT NULL,  -- Analista asignado (OBLIGATORIO)
    -- modelo_vehiculo ELIMINADO - usar producto en su lugar
    
    -- RELACIONES NORMALIZADAS (se mapearán después)
    concesionario_id INTEGER,  -- FK a concesionarios.id
    analista_id INTEGER,  -- FK a analistas.id
    modelo_vehiculo_id INTEGER,  -- FK a modelos_vehiculos.id (se mapeará desde producto)
    
    -- ESTADO Y APROBACIÓN
    estado VARCHAR(20) NOT NULL DEFAULT 'DRAFT',  -- DRAFT, EN_REVISION, APROBADO, RECHAZADO
    usuario_proponente VARCHAR(100) NOT NULL,  -- Email del analista
    usuario_aprobador VARCHAR(100),  -- Email del admin (se llena al aprobar)
    usuario_autoriza VARCHAR(100),  -- Email del usuario que autoriza crear nuevo préstamo
    observaciones TEXT,  -- Observaciones de aprobación/rechazo
    
    -- FECHAS
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- Fecha de creación
    fecha_aprobacion TIMESTAMP,  -- Fecha cuando se aprueba el préstamo
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- Fecha de última actualización
    
    -- INFORMACIÓN COMPLEMENTARIA
    informacion_desplegable BOOLEAN NOT NULL DEFAULT FALSE,  -- Si ha desplegado info adicional
    
    -- ML IMPAGO - VALORES MANUALES
    ml_impago_nivel_riesgo_manual VARCHAR(20),  -- Alto, Medio, Bajo (valores manuales)
    ml_impago_probabilidad_manual NUMERIC(5, 3),  -- Probabilidad manual (0.0 a 1.0)
    
    -- ML IMPAGO - VALORES CALCULADOS
    ml_impago_nivel_riesgo_calculado VARCHAR(20),  -- Alto, Medio, Bajo (valores calculados)
    ml_impago_probabilidad_calculada NUMERIC(5, 3),  -- Probabilidad calculada (0.0 a 1.0)
    ml_impago_calculado_en TIMESTAMP,  -- Fecha de última predicción calculada
    ml_impago_modelo_id INTEGER,  -- ID del modelo ML usado
    
    -- REVISIÓN DE DIFERENCIAS DE ABONOS
    requiere_revision BOOLEAN NOT NULL DEFAULT FALSE,  -- Marca préstamos que requieren revisión manual
    
    -- CAMPOS ADICIONALES PARA VALIDACIÓN Y MAPEO
    -- Estos campos NO se insertarán en la tabla final
    cedula_original VARCHAR(20),  -- Cédula original de la fuente (para validación)
    cliente_id_mapeado INTEGER,  -- cliente_id mapeado después de validar
    concesionario_id_mapeado INTEGER,  -- concesionario_id mapeado después de validar
    analista_id_mapeado INTEGER,  -- analista_id mapeado después de validar
    modelo_vehiculo_id_mapeado INTEGER,  -- modelo_vehiculo_id mapeado desde producto después de validar
    errores_validacion TEXT,  -- Errores encontrados durante la validación
    estado_validacion VARCHAR(20) DEFAULT 'PENDIENTE',  -- PENDIENTE, VALIDADO, ERROR
    fecha_validacion TIMESTAMP,  -- Fecha de validación
    observaciones_importacion TEXT  -- Observaciones específicas de la importación
);

-- Crear índices para mejorar el rendimiento de las consultas de validación
CREATE INDEX idx_prestamos_temporal_cedula ON public.prestamos_temporal(cedula);
CREATE INDEX idx_prestamos_temporal_estado_validacion ON public.prestamos_temporal(estado_validacion);
CREATE INDEX idx_prestamos_temporal_cliente_id_mapeado ON public.prestamos_temporal(cliente_id_mapeado);

-- Comentarios en la tabla
COMMENT ON TABLE public.prestamos_temporal IS 'Tabla temporal para importación de préstamos desde otra base de datos';
COMMENT ON COLUMN public.prestamos_temporal.cedula_original IS 'Cédula original de la fuente (para validación)';
COMMENT ON COLUMN public.prestamos_temporal.cliente_id_mapeado IS 'cliente_id mapeado después de validar existencia en tabla clientes';
COMMENT ON COLUMN public.prestamos_temporal.errores_validacion IS 'Errores encontrados durante la validación (JSON o texto)';
COMMENT ON COLUMN public.prestamos_temporal.estado_validacion IS 'Estado de validación: PENDIENTE, VALIDADO, ERROR';
COMMENT ON COLUMN public.prestamos_temporal.observaciones_importacion IS 'Observaciones específicas de la importación';

-- Verificar creación en esquema PUBLIC
SELECT 
    'public.prestamos_temporal' as tabla_completa,
    COUNT(*) as total_columnas,
    '✅ Tabla creada en esquema PUBLIC' as estado
FROM information_schema.columns 
WHERE table_schema = 'public'
  AND table_name = 'prestamos_temporal';

-- Instrucciones para refrescar en DBeaver
SELECT 
    'INSTRUCCIONES' as tipo,
    '1. Clic derecho en la carpeta "Tables" del esquema "public"' as paso1,
    '2. Seleccionar "Refresh"' as paso2,
    '3. O presionar F5 para refrescar' as paso3,
    '4. La tabla prestamos_temporal debería aparecer ahora' as paso4;
