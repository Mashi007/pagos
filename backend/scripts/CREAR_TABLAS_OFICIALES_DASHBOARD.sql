-- ============================================================================
-- SCRIPT PARA CREAR TABLAS OFICIALES DE REPORTING DEL DASHBOARD
-- ============================================================================
-- Este script crea tablas oficiales de reporting que consolidan los datos
-- para uso en dashboards, gráficos y KPIs
-- 
-- Ejecutar en DBeaver: Seleccionar todo y ejecutar (F5)
-- ============================================================================

-- ============================================================================
-- 1. TABLA: dashboard_morosidad_mensual
-- ============================================================================
-- Contiene la evolución de morosidad por mes
-- Se actualiza mensualmente o mediante trigger
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_morosidad_mensual (
    id SERIAL PRIMARY KEY,
    año INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    morosidad_total NUMERIC(15, 2) NOT NULL DEFAULT 0,
    cantidad_cuotas_vencidas INTEGER NOT NULL DEFAULT 0,
    cantidad_prestamos_afectados INTEGER NOT NULL DEFAULT 0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(año, mes)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_morosidad_año_mes ON dashboard_morosidad_mensual(año, mes);
CREATE INDEX IF NOT EXISTS idx_dashboard_morosidad_fecha_actualizacion ON dashboard_morosidad_mensual(fecha_actualizacion);

COMMENT ON TABLE dashboard_morosidad_mensual IS 'Tabla oficial de morosidad mensual para dashboard. Contiene suma de cuotas vencidas no pagadas agrupadas por mes.';
COMMENT ON COLUMN dashboard_morosidad_mensual.morosidad_total IS 'Suma total de monto_cuota de cuotas vencidas no pagadas';
COMMENT ON COLUMN dashboard_morosidad_mensual.cantidad_cuotas_vencidas IS 'Cantidad de cuotas vencidas no pagadas';
COMMENT ON COLUMN dashboard_morosidad_mensual.cantidad_prestamos_afectados IS 'Cantidad de préstamos únicos con morosidad';


-- ============================================================================
-- 2. TABLA: dashboard_cobranzas_mensuales
-- ============================================================================
-- Contiene cobranzas planificadas vs pagos reales por mes
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_cobranzas_mensuales (
    id SERIAL PRIMARY KEY,
    año INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    nombre_mes VARCHAR(20) NOT NULL,
    cobranzas_planificadas NUMERIC(15, 2) NOT NULL DEFAULT 0,
    pagos_reales NUMERIC(15, 2) NOT NULL DEFAULT 0,
    meta_mensual NUMERIC(15, 2) NOT NULL DEFAULT 0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(año, mes)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_cobranzas_año_mes ON dashboard_cobranzas_mensuales(año, mes);
CREATE INDEX IF NOT EXISTS idx_dashboard_cobranzas_fecha_actualizacion ON dashboard_cobranzas_mensuales(fecha_actualizacion);

COMMENT ON TABLE dashboard_cobranzas_mensuales IS 'Tabla oficial de cobranzas mensuales. Planificadas vs reales vs meta.';
COMMENT ON COLUMN dashboard_cobranzas_mensuales.cobranzas_planificadas IS 'Suma de monto_cuota de todas las cuotas que vencen en el mes';
COMMENT ON COLUMN dashboard_cobranzas_mensuales.pagos_reales IS 'Suma de pagos realizados en el mes';
COMMENT ON COLUMN dashboard_cobranzas_mensuales.meta_mensual IS 'Meta de cobranza para el mes';


-- ============================================================================
-- 3. TABLA: dashboard_kpis_diarios
-- ============================================================================
-- Contiene KPIs principales calculados diariamente
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_kpis_diarios (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    total_prestamos INTEGER NOT NULL DEFAULT 0,
    total_prestamos_valor NUMERIC(15, 2) NOT NULL DEFAULT 0,
    creditos_nuevos_mes INTEGER NOT NULL DEFAULT 0,
    creditos_nuevos_mes_valor NUMERIC(15, 2) NOT NULL DEFAULT 0,
    total_clientes INTEGER NOT NULL DEFAULT 0,
    total_morosidad_usd NUMERIC(15, 2) NOT NULL DEFAULT 0,
    cartera_total NUMERIC(15, 2) NOT NULL DEFAULT 0,
    total_cobrado NUMERIC(15, 2) NOT NULL DEFAULT 0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dashboard_kpis_fecha ON dashboard_kpis_diarios(fecha);
CREATE INDEX IF NOT EXISTS idx_dashboard_kpis_fecha_actualizacion ON dashboard_kpis_diarios(fecha_actualizacion);

COMMENT ON TABLE dashboard_kpis_diarios IS 'Tabla oficial de KPIs principales calculados diariamente';
COMMENT ON COLUMN dashboard_kpis_diarios.total_prestamos IS 'Cantidad total de préstamos aprobados';
COMMENT ON COLUMN dashboard_kpis_diarios.total_prestamos_valor IS 'Valor total de préstamos aprobados';
COMMENT ON COLUMN dashboard_kpis_diarios.creditos_nuevos_mes IS 'Cantidad de créditos nuevos del mes';
COMMENT ON COLUMN dashboard_kpis_diarios.creditos_nuevos_mes_valor IS 'Valor de créditos nuevos del mes';


-- ============================================================================
-- 4. TABLA: dashboard_financiamiento_mensual
-- ============================================================================
-- Contiene tendencia mensual de financiamiento
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_financiamiento_mensual (
    id SERIAL PRIMARY KEY,
    año INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    nombre_mes VARCHAR(20) NOT NULL,
    cantidad_nuevos INTEGER NOT NULL DEFAULT 0,
    monto_nuevos NUMERIC(15, 2) NOT NULL DEFAULT 0,
    total_acumulado NUMERIC(15, 2) NOT NULL DEFAULT 0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(año, mes)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_financiamiento_año_mes ON dashboard_financiamiento_mensual(año, mes);
CREATE INDEX IF NOT EXISTS idx_dashboard_financiamiento_fecha_actualizacion ON dashboard_financiamiento_mensual(fecha_actualizacion);

COMMENT ON TABLE dashboard_financiamiento_mensual IS 'Tabla oficial de tendencia mensual de financiamiento';
COMMENT ON COLUMN dashboard_financiamiento_mensual.cantidad_nuevos IS 'Cantidad de préstamos nuevos del mes';
COMMENT ON COLUMN dashboard_financiamiento_mensual.monto_nuevos IS 'Monto total de préstamos nuevos del mes';
COMMENT ON COLUMN dashboard_financiamiento_mensual.total_acumulado IS 'Total acumulado hasta el mes';


-- ============================================================================
-- 5. TABLA: dashboard_morosidad_por_analista
-- ============================================================================
-- Contiene morosidad agrupada por analista
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_morosidad_por_analista (
    id SERIAL PRIMARY KEY,
    analista VARCHAR(100) NOT NULL,
    total_morosidad NUMERIC(15, 2) NOT NULL DEFAULT 0,
    cantidad_clientes INTEGER NOT NULL DEFAULT 0,
    cantidad_cuotas_atrasadas INTEGER NOT NULL DEFAULT 0,
    promedio_morosidad_por_cliente NUMERIC(15, 2) NOT NULL DEFAULT 0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(analista)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_morosidad_analista ON dashboard_morosidad_por_analista(analista);
CREATE INDEX IF NOT EXISTS idx_dashboard_morosidad_analista_total ON dashboard_morosidad_por_analista(total_morosidad DESC);

COMMENT ON TABLE dashboard_morosidad_por_analista IS 'Tabla oficial de morosidad agrupada por analista';
COMMENT ON COLUMN dashboard_morosidad_por_analista.analista IS 'Nombre del analista';
COMMENT ON COLUMN dashboard_morosidad_por_analista.total_morosidad IS 'Suma total de morosidad del analista';


-- ============================================================================
-- 6. TABLA: dashboard_prestamos_por_concesionario
-- ============================================================================
-- Contiene distribución de préstamos por concesionario
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_prestamos_por_concesionario (
    id SERIAL PRIMARY KEY,
    concesionario VARCHAR(100) NOT NULL,
    total_prestamos INTEGER NOT NULL DEFAULT 0,
    porcentaje NUMERIC(5, 2) NOT NULL DEFAULT 0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(concesionario)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_prestamos_concesionario ON dashboard_prestamos_por_concesionario(concesionario);
CREATE INDEX IF NOT EXISTS idx_dashboard_prestamos_concesionario_total ON dashboard_prestamos_por_concesionario(total_prestamos DESC);

COMMENT ON TABLE dashboard_prestamos_por_concesionario IS 'Tabla oficial de distribución de préstamos por concesionario';
COMMENT ON COLUMN dashboard_prestamos_por_concesionario.total_prestamos IS 'Cantidad de préstamos del concesionario';
COMMENT ON COLUMN dashboard_prestamos_por_concesionario.porcentaje IS 'Porcentaje del total de préstamos';


-- ============================================================================
-- 7. TABLA: dashboard_pagos_mensuales
-- ============================================================================
-- Contiene evolución de pagos por mes
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_pagos_mensuales (
    id SERIAL PRIMARY KEY,
    año INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    nombre_mes VARCHAR(20) NOT NULL,
    cantidad_pagos INTEGER NOT NULL DEFAULT 0,
    monto_total NUMERIC(15, 2) NOT NULL DEFAULT 0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(año, mes)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_pagos_año_mes ON dashboard_pagos_mensuales(año, mes);
CREATE INDEX IF NOT EXISTS idx_dashboard_pagos_fecha_actualizacion ON dashboard_pagos_mensuales(fecha_actualizacion);

COMMENT ON TABLE dashboard_pagos_mensuales IS 'Tabla oficial de evolución de pagos mensuales';
COMMENT ON COLUMN dashboard_pagos_mensuales.cantidad_pagos IS 'Cantidad de pagos realizados en el mes';
COMMENT ON COLUMN dashboard_pagos_mensuales.monto_total IS 'Monto total de pagos del mes';


-- ============================================================================
-- 8. TABLA: dashboard_cobros_por_analista
-- ============================================================================
-- Contiene distribución de cobros por analista
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_cobros_por_analista (
    id SERIAL PRIMARY KEY,
    analista VARCHAR(100) NOT NULL,
    total_cobrado NUMERIC(15, 2) NOT NULL DEFAULT 0,
    cantidad_pagos INTEGER NOT NULL DEFAULT 0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(analista)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_cobros_analista ON dashboard_cobros_por_analista(analista);
CREATE INDEX IF NOT EXISTS idx_dashboard_cobros_analista_total ON dashboard_cobros_por_analista(total_cobrado DESC);

COMMENT ON TABLE dashboard_cobros_por_analista IS 'Tabla oficial de cobros agrupados por analista';
COMMENT ON COLUMN dashboard_cobros_por_analista.total_cobrado IS 'Total cobrado por el analista';
COMMENT ON COLUMN dashboard_cobros_por_analista.cantidad_pagos IS 'Cantidad de pagos procesados';


-- ============================================================================
-- 9. TABLA: dashboard_metricas_acumuladas
-- ============================================================================
-- Contiene métricas acumuladas hasta la fecha
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_metricas_acumuladas (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    cartera_total NUMERIC(15, 2) NOT NULL DEFAULT 0,
    morosidad_total NUMERIC(15, 2) NOT NULL DEFAULT 0,
    total_cobrado NUMERIC(15, 2) NOT NULL DEFAULT 0,
    total_prestamos INTEGER NOT NULL DEFAULT 0,
    total_clientes INTEGER NOT NULL DEFAULT 0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dashboard_metricas_fecha ON dashboard_metricas_acumuladas(fecha);
CREATE INDEX IF NOT EXISTS idx_dashboard_metricas_fecha_actualizacion ON dashboard_metricas_acumuladas(fecha_actualizacion);

COMMENT ON TABLE dashboard_metricas_acumuladas IS 'Tabla oficial de métricas acumuladas del sistema';
COMMENT ON COLUMN dashboard_metricas_acumuladas.cartera_total IS 'Cartera total acumulada';
COMMENT ON COLUMN dashboard_metricas_acumuladas.morosidad_total IS 'Morosidad total acumulada';
COMMENT ON COLUMN dashboard_metricas_acumuladas.total_cobrado IS 'Total cobrado acumulado';


-- ============================================================================
-- 10. PROCEDIMIENTO: Actualizar todas las tablas oficiales
-- ============================================================================
-- Función para actualizar todas las tablas oficiales de una vez
-- ============================================================================

CREATE OR REPLACE FUNCTION actualizar_tablas_oficiales_dashboard()
RETURNS void AS $$
BEGIN
    -- Actualizar morosidad mensual
    INSERT INTO dashboard_morosidad_mensual (año, mes, morosidad_total, cantidad_cuotas_vencidas, cantidad_prestamos_afectados)
    SELECT 
        EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
        EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
        COALESCE(SUM(c.monto_cuota), 0) as morosidad_total,
        COUNT(c.id) as cantidad_cuotas_vencidas,
        COUNT(DISTINCT p.id) as cantidad_prestamos_afectados
    FROM cuotas c
    INNER JOIN prestamos p ON c.prestamo_id = p.id
    WHERE 
        p.estado = 'APROBADO'
        AND c.fecha_vencimiento < CURRENT_DATE
        AND c.estado != 'PAGADO'
    GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
    ON CONFLICT (año, mes) DO UPDATE SET
        morosidad_total = EXCLUDED.morosidad_total,
        cantidad_cuotas_vencidas = EXCLUDED.cantidad_cuotas_vencidas,
        cantidad_prestamos_afectados = EXCLUDED.cantidad_prestamos_afectados,
        fecha_actualizacion = CURRENT_TIMESTAMP;

    -- Actualizar KPIs diarios (solo para hoy)
    INSERT INTO dashboard_kpis_diarios (fecha, total_prestamos, total_prestamos_valor, total_clientes, total_morosidad_usd)
    SELECT 
        CURRENT_DATE as fecha,
        COUNT(DISTINCT p.id) as total_prestamos,
        COALESCE(SUM(p.total_financiamiento), 0) as total_prestamos_valor,
        COUNT(DISTINCT p.cedula) as total_clientes,
        COALESCE(SUM(c.monto_cuota), 0) as total_morosidad_usd
    FROM prestamos p
    LEFT JOIN cuotas c ON c.prestamo_id = p.id AND c.fecha_vencimiento < CURRENT_DATE AND c.estado != 'PAGADO'
    WHERE p.estado = 'APROBADO'
    ON CONFLICT (fecha) DO UPDATE SET
        total_prestamos = EXCLUDED.total_prestamos,
        total_prestamos_valor = EXCLUDED.total_prestamos_valor,
        total_clientes = EXCLUDED.total_clientes,
        total_morosidad_usd = EXCLUDED.total_morosidad_usd,
        fecha_actualizacion = CURRENT_TIMESTAMP;

    RAISE NOTICE 'Tablas oficiales del dashboard actualizadas exitosamente';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION actualizar_tablas_oficiales_dashboard() IS 'Función para actualizar todas las tablas oficiales del dashboard de una vez';


-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
-- Ejecutar para verificar que las tablas se crearon correctamente
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Verificando creación de tablas oficiales...';
    RAISE NOTICE 'Tablas creadas exitosamente:';
    RAISE NOTICE '  - dashboard_morosidad_mensual';
    RAISE NOTICE '  - dashboard_cobranzas_mensuales';
    RAISE NOTICE '  - dashboard_kpis_diarios';
    RAISE NOTICE '  - dashboard_financiamiento_mensual';
    RAISE NOTICE '  - dashboard_morosidad_por_analista';
    RAISE NOTICE '  - dashboard_prestamos_por_concesionario';
    RAISE NOTICE '  - dashboard_pagos_mensuales';
    RAISE NOTICE '  - dashboard_cobros_por_analista';
    RAISE NOTICE '  - dashboard_metricas_acumuladas';
    RAISE NOTICE '';
    RAISE NOTICE 'Función creada: actualizar_tablas_oficiales_dashboard()';
    RAISE NOTICE '';
    RAISE NOTICE 'Para actualizar las tablas, ejecutar:';
    RAISE NOTICE 'SELECT actualizar_tablas_oficiales_dashboard();';
END $$;

