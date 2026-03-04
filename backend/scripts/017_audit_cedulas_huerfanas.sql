-- Migration: 017_audit_cedulas_huerfanas.sql
-- Propósito: Auditar cedulas en pagos que NO existen en clientes (datos huérfanos)
-- Requisito previo: Ejecutar para identificar problemas antes de agregar FK

-- 1. Crear tabla temporal para auditoría
CREATE TABLE IF NOT EXISTS public.audit_cedulas_huerfanas (
    id BIGSERIAL PRIMARY KEY,
    cedula_cliente VARCHAR(20) NOT NULL,
    cantidad_pagos INTEGER,
    cantidad_prestamos INTEGER,
    cantidad_clientes INTEGER,
    fecha_audit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notas TEXT
);

-- 2. Auditar: cedulas en pagos sin cliente en BD
INSERT INTO public.audit_cedulas_huerfanas (cedula_cliente, cantidad_pagos, cantidad_prestamos, cantidad_clientes, notas)
SELECT 
    p.cedula_cliente,
    COUNT(DISTINCT p.id) as pagos,
    COUNT(DISTINCT pr.id) as prestamos,
    COUNT(DISTINCT c.id) as clientes,
    'Cedula con pagos pero SIN cliente en BD' as notas
FROM public.pagos p
LEFT JOIN public.clientes c ON p.cedula_cliente = c.cedula
LEFT JOIN public.prestamos pr ON p.cedula_cliente = pr.cedula
WHERE NOT EXISTS (
    SELECT 1 FROM public.clientes c2
    WHERE c2.cedula = p.cedula_cliente
)
GROUP BY p.cedula_cliente
ORDER BY COUNT(DISTINCT p.id) DESC;

-- 3. Ver resultados
SELECT 
    'CEDULAS HUERFANAS EN PAGOS:' as info,
    COUNT(*) as total_cedulas_unicas,
    SUM(cantidad_pagos) as total_pagos_huerfanos
FROM public.audit_cedulas_huerfanas;

-- 4. Listar detalle
SELECT 
    cedula_cliente,
    cantidad_pagos,
    cantidad_prestamos,
    fecha_audit
FROM public.audit_cedulas_huerfanas
ORDER BY cantidad_pagos DESC
LIMIT 20;

-- NOTAS PARA USUARIO:
-- - Si cantidad = 0 → ✅ No hay cedulas huérfanas (seguro agregar FK)
-- - Si cantidad > 0 → ⚠️ Hay cedulas huérfanas (REVISAR ANTES de agregar FK)
--
-- ACCIONES RECOMENDADAS:
-- 1. Revisar registros en audit_cedulas_huerfanas
-- 2. Investigar por qué pagos tienen cedulas sin cliente
-- 3. OPCIÓN A: Crear clientes faltantes
-- 4. OPCIÓN B: Eliminar pagos huérfanos (ej: DELETE FROM pagos WHERE cedula_cliente IN (SELECT cedula FROM audit_cedulas_huerfanas))
-- 5. Luego ejecutar 018_add_fk_cedula_cliente.sql
