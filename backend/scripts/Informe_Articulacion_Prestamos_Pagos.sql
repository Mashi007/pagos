-- ============================================
-- INFORME COMPLETO: ARTICULACIÓN PRESTAMOS - MÓDULO PAGOS
-- Verifica toda la estructura, relaciones e integridad
-- ============================================

-- ============================================
-- PARTE 1: ESTRUCTURA DE LA TABLA PRESTAMOS
-- ============================================

SELECT 
    '=== PARTE 1: ESTRUCTURA DE PRESTAMOS ===' AS seccion,
    column_name,
    data_type,
    character_maximum_length,
    numeric_precision,
    numeric_scale,
    is_nullable,
    column_default,
    CASE 
        WHEN column_name IN ('id', 'cliente_id', 'cedula') THEN '🔑 Clave de Articulación'
        WHEN column_name LIKE '%fecha%' THEN '📅 Fecha'
        WHEN data_type IN ('numeric', 'decimal', 'money') THEN '💰 Monetario'
        WHEN column_name IN ('estado', 'modalidad_pago') THEN '📋 Estado/Configuración'
        WHEN column_name IN ('nombres', 'cedula') THEN '👤 Datos Cliente'
        ELSE '📝 Otro'
    END AS categoria
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'prestamos'
ORDER BY ordinal_position;

-- ============================================
-- PARTE 2: CLAVES DE ARTICULACIÓN
-- ============================================

-- 2.1 Relación cliente_id → clientes.id
SELECT 
    '=== PARTE 2.1: Relación cliente_id → clientes.id ===' AS verificacion,
    COUNT(*) AS total_prestamos,
    COUNT(CASE WHEN p.cliente_id IS NOT NULL THEN 1 END) AS con_cliente_id,
    COUNT(CASE WHEN p.cliente_id IS NOT NULL AND c.id IS NOT NULL THEN 1 END) AS cliente_id_valido,
    COUNT(CASE WHEN p.cliente_id IS NOT NULL AND c.id IS NULL THEN 1 END) AS cliente_id_invalido,
    ROUND(100.0 * COUNT(CASE WHEN p.cliente_id IS NOT NULL AND c.id IS NOT NULL THEN 1 END) / 
          NULLIF(COUNT(CASE WHEN p.cliente_id IS NOT NULL THEN 1 END), 0), 2) AS porcentaje_valido
FROM prestamos p
LEFT JOIN clientes c ON p.cliente_id = c.id;

-- 2.2 Relación cedula → clientes.cedula
SELECT 
    '=== PARTE 2.2: Relación cedula → clientes.cedula ===' AS verificacion,
    COUNT(*) AS total_prestamos,
    COUNT(CASE WHEN p.cedula IS NOT NULL THEN 1 END) AS con_cedula,
    COUNT(CASE WHEN p.cedula IS NOT NULL AND c_match.cedula IS NOT NULL THEN 1 END) AS cedula_valida,
    COUNT(CASE WHEN p.cedula IS NOT NULL AND c_match.cedula IS NULL THEN 1 END) AS cedula_invalida,
    ROUND(100.0 * COUNT(CASE WHEN p.cedula IS NOT NULL AND c_match.cedula IS NOT NULL THEN 1 END) / 
          NULLIF(COUNT(CASE WHEN p.cedula IS NOT NULL THEN 1 END), 0), 2) AS porcentaje_valido
FROM prestamos p
LEFT JOIN clientes c_match ON p.cedula = c_match.cedula;

-- 2.3 Relación id → cuotas.prestamo_id
SELECT 
    '=== PARTE 2.3: Relación id → cuotas.prestamo_id ===' AS verificacion,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT c.prestamo_id) AS prestamos_con_cuotas,
    COUNT(DISTINCT CASE WHEN c.prestamo_id IS NOT NULL THEN p.id END) AS con_cuotas,
    COUNT(DISTINCT CASE WHEN c.prestamo_id IS NULL THEN p.id END) AS sin_cuotas,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN c.prestamo_id IS NOT NULL THEN p.id END) / 
          NULLIF(COUNT(DISTINCT p.id), 0), 2) AS porcentaje_con_cuotas
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id;

-- 2.4 Relación id → pagos.prestamo_id
SELECT 
    '=== PARTE 2.4: Relación id → pagos.prestamo_id ===' AS verificacion,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT pag.prestamo_id) AS prestamos_con_pagos,
    COUNT(DISTINCT CASE WHEN pag.prestamo_id IS NOT NULL THEN p.id END) AS con_pagos,
    COUNT(DISTINCT CASE WHEN pag.prestamo_id IS NULL THEN p.id END) AS sin_pagos,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN pag.prestamo_id IS NOT NULL THEN p.id END) / 
          NULLIF(COUNT(DISTINCT p.id), 0), 2) AS porcentaje_con_pagos
FROM prestamos p
LEFT JOIN pagos pag ON p.id = pag.prestamo_id;

-- ============================================
-- PARTE 3: VERIFICACIÓN DE INTEGRIDAD
-- ============================================

-- 3.1 Préstamos con cliente_id inválido
SELECT 
    '=== PARTE 3.1: Préstamos con cliente_id inválido ===' AS verificacion,
    p.id AS prestamo_id,
    p.cliente_id,
    p.cedula,
    p.nombres,
    p.estado,
    CASE 
        WHEN c.id IS NULL THEN '❌ cliente_id no existe en clientes'
        ELSE '✅ cliente_id válido'
    END AS estado_validacion
FROM prestamos p
LEFT JOIN clientes c ON p.cliente_id = c.id
WHERE p.cliente_id IS NOT NULL
  AND c.id IS NULL
ORDER BY p.id
LIMIT 20;

-- 3.2 Préstamos con cedula inválida
SELECT 
    '=== PARTE 3.2: Préstamos con cedula inválida ===' AS verificacion,
    p.id AS prestamo_id,
    p.cliente_id,
    p.cedula,
    p.nombres AS nombres_prestamo,
    c_match.cedula AS cedula_cliente,
    c_match.nombres AS nombres_cliente,
    CASE 
        WHEN c_match.cedula IS NULL THEN '❌ cédula no existe en clientes'
        WHEN p.cedula != c_match.cedula THEN '⚠️ cédulas no coinciden'
        ELSE '✅ cédula válida'
    END AS estado_validacion
FROM prestamos p
LEFT JOIN clientes c_match ON p.cedula = c_match.cedula
WHERE p.cedula IS NOT NULL
  AND (c_match.cedula IS NULL OR p.cedula != c_match.cedula)
ORDER BY p.id
LIMIT 20;

-- 3.3 Préstamos sin cuotas (deberían tener si están APROBADO)
SELECT 
    '=== PARTE 3.3: Préstamos APROBADOS sin cuotas ===' AS verificacion,
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.estado,
    p.fecha_aprobacion,
    p.fecha_base_calculo,
    p.numero_cuotas,
    (SELECT COUNT(*) FROM cuotas WHERE prestamo_id = p.id) AS cuotas_existentes,
    CASE 
        WHEN p.fecha_base_calculo IS NOT NULL AND NOT EXISTS (SELECT 1 FROM cuotas WHERE prestamo_id = p.id) THEN '❌ Debería tener cuotas'
        WHEN p.fecha_base_calculo IS NULL THEN '⚠️ Falta fecha_base_calculo'
        ELSE '✅ Tiene cuotas'
    END AS estado_validacion
FROM prestamos p
WHERE p.estado = 'APROBADO'
  AND (p.fecha_base_calculo IS NULL OR NOT EXISTS (SELECT 1 FROM cuotas WHERE prestamo_id = p.id))
ORDER BY p.id
LIMIT 20;

-- 3.4 Inconsistencias entre cedula y cliente_id
SELECT 
    '=== PARTE 3.4: Inconsistencias cedula vs cliente_id ===' AS verificacion,
    p.id AS prestamo_id,
    p.cliente_id,
    p.cedula AS cedula_prestamo,
    c_id.cedula AS cedula_por_cliente_id,
    c_cedula.cedula AS cedula_por_cedula,
    CASE 
        WHEN p.cliente_id IS NOT NULL AND c_id.cedula IS NULL THEN '❌ cliente_id no encuentra cédula'
        WHEN p.cedula IS NOT NULL AND p.cliente_id IS NOT NULL 
             AND c_id.cedula != p.cedula THEN '❌ cliente_id y cedula no coinciden'
        WHEN p.cedula IS NOT NULL AND c_cedula.cedula IS NULL THEN '❌ cedula no existe en clientes'
        ELSE '✅ Coinciden'
    END AS estado_validacion
FROM prestamos p
LEFT JOIN clientes c_id ON p.cliente_id = c_id.id
LEFT JOIN clientes c_cedula ON p.cedula = c_cedula.cedula
WHERE (p.cliente_id IS NOT NULL AND c_id.cedula IS NULL)
   OR (p.cliente_id IS NOT NULL AND p.cedula IS NOT NULL AND c_id.cedula != p.cedula)
   OR (p.cedula IS NOT NULL AND c_cedula.cedula IS NULL)
ORDER BY p.id
LIMIT 20;

-- ============================================
-- PARTE 4: MUESTRAS DE PROBLEMAS
-- ============================================

-- 4.1 Ejemplos de préstamos con cliente_id inválido
SELECT 
    '=== PARTE 4.1: Ejemplo - cliente_id inválido ===' AS problema,
    p.id AS prestamo_id,
    p.cliente_id,
    p.cedula,
    p.nombres,
    'El cliente_id no existe en la tabla clientes' AS descripcion
FROM prestamos p
LEFT JOIN clientes c ON p.cliente_id = c.id
WHERE p.cliente_id IS NOT NULL
  AND c.id IS NULL
LIMIT 5;

-- 4.2 Ejemplos de préstamos con cedula inválida
SELECT 
    '=== PARTE 4.2: Ejemplo - cedula inválida ===' AS problema,
    p.id AS prestamo_id,
    p.cedula,
    p.nombres AS nombres_prestamo,
    'La cédula no existe en la tabla clientes' AS descripcion
FROM prestamos p
LEFT JOIN clientes c_match ON p.cedula = c_match.cedula
WHERE p.cedula IS NOT NULL
  AND c_match.cedula IS NULL
LIMIT 5;

-- 4.3 Ejemplos de préstamos aprobados sin cuotas
SELECT 
    '=== PARTE 4.3: Ejemplo - Aprobados sin cuotas ===' AS problema,
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.estado,
    p.fecha_aprobacion,
    p.fecha_base_calculo,
    'Préstamo aprobado debería tener tabla de amortización' AS descripcion
FROM prestamos p
WHERE p.estado = 'APROBADO'
  AND p.fecha_base_calculo IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM cuotas WHERE prestamo_id = p.id)
LIMIT 5;

-- 4.4 Ejemplos de préstamos con pagos pero sin cédula coincidente
SELECT 
    '=== PARTE 4.4: Ejemplo - Pagos con cédula no coincidente ===' AS problema,
    p.id AS prestamo_id,
    p.cedula AS cedula_prestamo,
    pag.cedula_cliente AS cedula_pago,
    COUNT(pag.id) AS cantidad_pagos,
    'Los pagos tienen cédula diferente al préstamo' AS descripcion
FROM prestamos p
INNER JOIN pagos pag ON p.id = pag.prestamo_id
WHERE p.cedula IS NOT NULL
  AND pag.cedula_cliente IS NOT NULL
  AND p.cedula != pag.cedula_cliente
GROUP BY p.id, p.cedula, pag.cedula_cliente
LIMIT 5;

-- ============================================
-- PARTE 5: FOREIGN KEYS Y CONSTRAINTS
-- ============================================

SELECT 
    '=== PARTE 5: Foreign Keys y Constraints ===' AS verificacion,
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    tc.constraint_type,
    CASE 
        WHEN tc.constraint_type = 'FOREIGN KEY' THEN '🔗 Relación definida'
        WHEN tc.constraint_type = 'PRIMARY KEY' THEN '🔑 Clave Primaria'
        WHEN tc.constraint_type = 'UNIQUE' THEN '✨ Restricción única'
        ELSE '📋 Otro'
    END AS tipo_descripcion
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
LEFT JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.table_name = 'prestamos'
  AND tc.table_schema = 'public'
ORDER BY tc.constraint_type, tc.constraint_name;

-- ============================================
-- PARTE 6: ÍNDICES
-- ============================================

SELECT 
    '=== PARTE 6: Índices en PRESTAMOS ===' AS verificacion,
    indexname AS nombre_indice,
    indexdef AS definicion,
    CASE 
        WHEN indexdef LIKE '%cliente_id%' THEN '🔗 Articulación con clientes'
        WHEN indexdef LIKE '%cedula%' THEN '🔗 Articulación por cédula'
        WHEN indexdef LIKE '%estado%' THEN '📋 Filtrado por estado'
        WHEN indexdef LIKE '%PRIMARY%' THEN '🔑 Clave primaria'
        ELSE '📊 Otro'
    END AS proposito
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'prestamos'
ORDER BY indexname;

-- ============================================
-- PARTE 7: ESTADÍSTICAS DE ARTICULACIÓN
-- ============================================

SELECT 
    '=== PARTE 7: Estadísticas de Articulación ===' AS verificacion,
    (SELECT COUNT(*) FROM prestamos) AS total_prestamos,
    (SELECT COUNT(*) FROM prestamos WHERE cliente_id IS NOT NULL) AS con_cliente_id,
    (SELECT COUNT(*) FROM prestamos WHERE cedula IS NOT NULL) AS con_cedula,
    (SELECT COUNT(*) FROM prestamos p INNER JOIN clientes c ON p.cliente_id = c.id) AS cliente_id_valido,
    (SELECT COUNT(*) FROM prestamos p INNER JOIN clientes c ON p.cedula = c.cedula) AS cedula_valida,
    (SELECT COUNT(DISTINCT prestamo_id) FROM cuotas) AS prestamos_con_cuotas,
    (SELECT COUNT(DISTINCT prestamo_id) FROM pagos WHERE prestamo_id IS NOT NULL) AS prestamos_con_pagos,
    (SELECT COUNT(*) FROM prestamos p 
     INNER JOIN clientes c_id ON p.cliente_id = c_id.id 
     INNER JOIN clientes c_cedula ON p.cedula = c_cedula.cedula
     WHERE c_id.cedula = c_cedula.cedula) AS totalmente_articulados,
    ROUND(100.0 * (SELECT COUNT(*) FROM prestamos p INNER JOIN clientes c ON p.cliente_id = c.id) / 
          NULLIF((SELECT COUNT(*) FROM prestamos WHERE cliente_id IS NOT NULL), 0), 2) AS porcentaje_cliente_id_valido,
    ROUND(100.0 * (SELECT COUNT(*) FROM prestamos p INNER JOIN clientes c ON p.cedula = c.cedula) / 
          NULLIF((SELECT COUNT(*) FROM prestamos WHERE cedula IS NOT NULL), 0), 2) AS porcentaje_cedula_valida;

-- ============================================
-- PARTE 8: RECOMENDACIONES
-- ============================================

SELECT 
    '=== PARTE 8: Recomendaciones ===' AS verificacion,
    1 AS numero,
    'Agregar FOREIGN KEY constraint para cliente_id → clientes.id' AS recomendacion,
    'Asegura integridad referencial automática' AS beneficio
UNION ALL
SELECT 
    '=== PARTE 8: Recomendaciones ===',
    2,
    'Agregar FOREIGN KEY constraint para pagos.prestamo_id → prestamos.id',
    'Garantiza que los pagos siempre apunten a préstamos válidos'
UNION ALL
SELECT 
    '=== PARTE 8: Recomendaciones ===',
    3,
    'Sincronizar automáticamente cedula y cliente_id al crear préstamo',
    'Evita inconsistencias entre ambos campos'
UNION ALL
SELECT 
    '=== PARTE 8: Recomendaciones ===',
    4,
    'Validar que cédula del pago coincida con cédula del préstamo antes de aplicar',
    'Ya implementado en aplicar_pago_a_cuotas()'
UNION ALL
SELECT 
    '=== PARTE 8: Recomendaciones ===',
    5,
    'Generar automáticamente tabla de amortización al aprobar préstamo',
    'Ya implementado en procesar_cambio_estado() cuando estado = APROBADO'
UNION ALL
SELECT 
    '=== PARTE 8: Recomendaciones ===',
    6,
    'Aplicar pagos automáticamente a cuotas al registrar pago',
    'Ya implementado en crear_pago()'
UNION ALL
SELECT 
    '=== PARTE 8: Recomendaciones ===',
    7,
    'Ordenar cuotas pendientes primero en visualización',
    'Ya implementado en obtener_cuotas_prestamo()'
ORDER BY numero;

-- ============================================
-- PARTE 9: FLUJO DE ARTICULACIÓN
-- ============================================

SELECT 
    '=== PARTE 9: Flujo de Articulación ===' AS verificacion,
    'PASO 1: Cliente' AS paso,
    'Tabla: clientes' AS tabla,
    'Claves: id (PK), cedula (unique)' AS claves,
    'Relación: Cliente es la entidad base' AS relacion
UNION ALL
SELECT 
    '=== PARTE 9: Flujo de Articulación ===',
    'PASO 2: Préstamo',
    'Tabla: prestamos',
    'Claves: id (PK), cliente_id (FK → clientes.id), cedula (texto → clientes.cedula)',
    'Relación: Un cliente puede tener múltiples préstamos'
UNION ALL
SELECT 
    '=== PARTE 9: Flujo de Articulación ===',
    'PASO 3: Cuotas (Amortización)',
    'Tabla: cuotas',
    'Claves: id (PK), prestamo_id (FK → prestamos.id)',
    'Relación: Un préstamo tiene múltiples cuotas (tabla de amortización)'
UNION ALL
SELECT 
    '=== PARTE 9: Flujo de Articulación ===',
    'PASO 4: Pagos',
    'Tabla: pagos',
    'Claves: id (PK), prestamo_id (FK → prestamos.id), cedula_cliente (texto → prestamos.cedula)',
    'Relación: Un préstamo puede tener múltiples pagos. Se aplican a cuotas vía pago_cuotas'
UNION ALL
SELECT 
    '=== PARTE 9: Flujo de Articulación ===',
    'PASO 5: Aplicación',
    'Tabla: pago_cuotas (many-to-many)',
    'Claves: pago_id (FK → pagos.id), cuota_id (FK → cuotas.id)',
    'Relación: Vincula pagos con cuotas específicas, registra monto_aplicado'
ORDER BY paso;

-- ============================================
-- RESUMEN EJECUTIVO
-- ============================================

SELECT 
    '=== RESUMEN EJECUTIVO ===' AS verificacion,
    (SELECT COUNT(*) FROM prestamos) AS total_prestamos,
    (SELECT COUNT(*) FROM prestamos p INNER JOIN clientes c ON p.cliente_id = c.id) AS prestamos_articulados_cliente_id,
    (SELECT COUNT(*) FROM prestamos p INNER JOIN clientes c ON p.cedula = c.cedula) AS prestamos_articulados_cedula,
    (SELECT COUNT(DISTINCT prestamo_id) FROM cuotas) AS prestamos_con_cuotas,
    (SELECT COUNT(DISTINCT prestamo_id) FROM pagos WHERE prestamo_id IS NOT NULL) AS prestamos_con_pagos,
    (SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO' 
     AND fecha_base_calculo IS NOT NULL 
     AND EXISTS (SELECT 1 FROM cuotas WHERE prestamo_id = prestamos.id)) AS prestamos_completamente_configurados;

