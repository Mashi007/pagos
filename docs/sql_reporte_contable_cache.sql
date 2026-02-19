-- =============================================================================
-- SQL para DBeaver: Reporte Contable - Tabla cache e histórico
-- Base de datos: PostgreSQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. CREAR TABLA reporte_contable_cache
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reporte_contable_cache (
    id SERIAL PRIMARY KEY,
    cuota_id INTEGER NOT NULL UNIQUE REFERENCES cuotas(id) ON DELETE CASCADE,
    cedula VARCHAR(20) NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    tipo_documento VARCHAR(50) NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    fecha_pago DATE NOT NULL,
    importe_md NUMERIC(14, 2) NOT NULL,
    moneda_documento VARCHAR(10) NOT NULL DEFAULT 'USD',
    tasa NUMERIC(14, 4) NOT NULL,
    importe_ml NUMERIC(14, 2) NOT NULL,
    moneda_local VARCHAR(10) NOT NULL DEFAULT 'Bs.',
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMPTZ
);

-- Índices para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_reporte_contable_cache_cuota ON reporte_contable_cache(cuota_id);
CREATE INDEX IF NOT EXISTS idx_reporte_contable_cache_cedula ON reporte_contable_cache(cedula);
CREATE INDEX IF NOT EXISTS idx_reporte_contable_cache_fecha ON reporte_contable_cache(fecha_pago);
CREATE INDEX IF NOT EXISTS idx_reporte_contable_cache_fecha_cedula ON reporte_contable_cache(fecha_pago, cedula);


-- -----------------------------------------------------------------------------
-- 2. INSERTAR HISTÓRICO (cuotas con pago, clientes ACTIVOS, préstamos APROBADOS)
-- Tasa por defecto: 36.0 (ajustar si tienes tabla de tasas o TASA_USD_BS_DEFAULT)
-- -----------------------------------------------------------------------------
INSERT INTO reporte_contable_cache (
    cuota_id,
    cedula,
    nombre,
    tipo_documento,
    fecha_vencimiento,
    fecha_pago,
    importe_md,
    moneda_documento,
    tasa,
    importe_ml,
    moneda_local
)
SELECT
    c.id AS cuota_id,
    COALESCE(p.cedula, '') AS cedula,
    COALESCE(TRIM(p.nombres), '') AS nombre,
    CASE
        WHEN COALESCE(NULLIF(c.total_pagado, 0), c.monto_cuota) >= COALESCE(c.monto_cuota, 0) - 0.01
        THEN 'Cuota ' || c.numero_cuota
        ELSE 'Abono'
    END AS tipo_documento,
    c.fecha_vencimiento,
    COALESCE(c.fecha_pago, (pago.fecha_pago)::DATE) AS fecha_pago,
    ROUND(COALESCE(NULLIF(c.total_pagado, 0), c.monto_cuota)::NUMERIC, 2) AS importe_md,
    'USD' AS moneda_documento,
    36.0 AS tasa,  -- Ajustar según TASA_USD_BS_DEFAULT o tabla de tasas
    ROUND((COALESCE(NULLIF(c.total_pagado, 0), c.monto_cuota) * 36.0)::NUMERIC, 2) AS importe_ml,
    'Bs.' AS moneda_local
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
JOIN clientes cl ON p.cliente_id = cl.id
LEFT JOIN pagos pago ON c.pago_id = pago.id
WHERE cl.estado = 'ACTIVO'
  AND p.estado = 'APROBADO'
  AND c.fecha_pago IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM reporte_contable_cache rcc WHERE rcc.cuota_id = c.id
  );


-- -----------------------------------------------------------------------------
-- 3. OPCIONAL: Actualizar tasas si tienes tabla de tasas por fecha
-- Ejemplo (descomentar y adaptar si aplica):
--
-- UPDATE reporte_contable_cache rcc
-- SET tasa = t.tasa,
--     importe_ml = ROUND((rcc.importe_md * t.tasa)::NUMERIC, 2)
-- FROM tasas_cambio t
-- WHERE t.fecha = rcc.fecha_pago
--   AND rcc.fecha_pago = t.fecha;
-- -----------------------------------------------------------------------------


-- -----------------------------------------------------------------------------
-- 4. CONSULTAS ÚTILES
-- -----------------------------------------------------------------------------

-- Ver total de filas en cache
-- SELECT COUNT(*) FROM reporte_contable_cache;

-- Ver rango de fechas en cache
-- SELECT MIN(fecha_pago) AS desde, MAX(fecha_pago) AS hasta FROM reporte_contable_cache;

-- Filtrar por año y mes (ej: 2025, enero)
-- SELECT * FROM reporte_contable_cache
-- WHERE EXTRACT(YEAR FROM fecha_pago) = 2025
--   AND EXTRACT(MONTH FROM fecha_pago) = 1
-- ORDER BY fecha_pago, cedula;

-- Filtrar por cédulas
-- SELECT * FROM reporte_contable_cache
-- WHERE cedula IN ('V12345678', 'V87654321')
-- ORDER BY fecha_pago, cedula;


-- -----------------------------------------------------------------------------
-- 5. LIMPIAR Y REGENERAR (solo si necesitas empezar de cero)
-- -----------------------------------------------------------------------------
-- TRUNCATE reporte_contable_cache RESTART IDENTITY;
-- Luego ejecutar de nuevo el INSERT del punto 2.
