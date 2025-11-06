-- ============================================================================
-- CONFIRMACIÓN: MÓDULO PAGOS - TABLAS Y CAMPOS UTILIZADOS
-- ============================================================================
-- Este documento confirma de qué tablas y campos toma datos el módulo de pagos
--
-- Autor: Sistema de Pagos
-- Fecha: 2025
-- ============================================================================

-- ============================================================================
-- 📊 RESUMEN EJECUTIVO
-- ============================================================================
-- El módulo de pagos consulta MÚLTIPLES tablas:
--
-- TABLAS PRINCIPALES:
--   ✅ pagos_staging   → Tabla principal para LISTAR y CONSULTAR pagos
--   ✅ pagos           → Tabla para CREAR, ACTUALIZAR y operaciones de escritura
--
-- TABLAS SECUNDARIAS (para cálculos y validaciones):
--   ✅ prestamos       → Para validar préstamos y obtener información relacionada
--   ✅ cuotas          → Para calcular cuotas atrasadas y aplicar pagos
--   ✅ clientes        → Para validar que el cliente existe
--   ✅ pagos_auditoria → Para registrar cambios y auditoría
--
-- ============================================================================

-- ============================================================================
-- 🗄️ TABLA 1: pagos_staging (CONSULTAS PRINCIPALES)
-- ============================================================================
-- Ubicación del modelo: backend/app/models/pago_staging.py
-- Nombre SQL: pagos_staging
-- Uso: Consultas de lectura (listar, estadísticas, KPIs)

-- Campos utilizados:
--   ✅ id_stg (alias id)        → PK, filtros
--   ✅ cedula_cliente           → Búsqueda, filtros, JOIN con clientes
--   ✅ fecha_pago               → Filtros por fecha (TEXT convertido a timestamp)
--   ✅ monto_pagado             → Sumas, cálculos (TEXT convertido a numeric)
--   ✅ numero_documento         → Filtros, validaciones
--   ✅ conciliado               → Filtros (si existe)
--   ✅ fecha_conciliacion       → Filtros (si existe)

-- Campos NO disponibles en la BD real:
--   ❌ prestamo_id              → No existe en pagos_staging
--   ❌ estado                   → No existe en pagos_staging
--   ❌ fecha_registro           → No existe en pagos_staging
--   ❌ usuario_registro          → No existe en pagos_staging
--   ❌ activo                   → No existe en pagos_staging

-- ============================================================================
-- 🗄️ TABLA 2: pagos (OPERACIONES DE ESCRITURA)
-- ============================================================================
-- Ubicación del modelo: backend/app/models/pago.py
-- Nombre SQL: pagos
-- Uso: Crear, actualizar, eliminar pagos

-- Campos utilizados:
--   ✅ id                       → PK
--   ✅ cedula_cliente           → FK a clientes, validaciones
--   ✅ prestamo_id              → FK a prestamos (opcional)
--   ✅ numero_cuota             → Relación con cuotas
--   ✅ fecha_pago               → Filtros, validaciones
--   ✅ fecha_registro           → Auditoría
--   ✅ monto_pagado             → Cálculos, validaciones
--   ✅ numero_documento         → Validaciones, búsqueda
--   ✅ institucion_bancaria      → Información adicional
--   ✅ documento_nombre          → Archivos adjuntos
--   ✅ documento_tipo            → Archivos adjuntos
--   ✅ documento_tamaño         → Archivos adjuntos
--   ✅ documento_ruta            → Archivos adjuntos
--   ✅ conciliado               → Estado de conciliación
--   ✅ fecha_conciliacion        → Fecha de conciliación
--   ✅ estado                   → Estado del pago (PAGADO, PARCIAL, etc.)
--   ✅ activo                   → Filtros (solo activos)
--   ✅ notas                    → Notas adicionales
--   ✅ usuario_registro         → Auditoría
--   ✅ fecha_actualizacion      → Auditoría

-- ============================================================================
-- 🗄️ TABLA 3: prestamos (VALIDACIONES Y JOINS)
-- ============================================================================
-- Ubicación del modelo: backend/app/models/prestamo.py
-- Nombre SQL: prestamos
-- Uso: Validar préstamos, obtener información relacionada

-- Campos utilizados:
--   ✅ id                       → JOIN con pagos.prestamo_id
--   ✅ cedula                   → Validación con pagos.cedula_cliente
--   ✅ estado                   → Filtros (solo APROBADO)
--   ✅ analista                 → Filtros opcionales
--   ✅ concesionario            → Filtros opcionales
--   ✅ producto                 → Filtros opcionales
--   ✅ modelo_vehiculo          → Filtros opcionales

-- ============================================================================
-- 🗄️ TABLA 4: cuotas (CÁLCULOS Y APLICACIÓN DE PAGOS)
-- ============================================================================
-- Ubicación del modelo: backend/app/models/amortizacion.py
-- Nombre SQL: cuotas
-- Uso: Calcular cuotas atrasadas, aplicar pagos a cuotas

-- Campos utilizados:
--   ✅ id                       → Contar cuotas
--   ✅ prestamo_id              → JOIN con prestamos
--   ✅ numero_cuota             → Ordenamiento
--   ✅ fecha_vencimiento        → Calcular cuotas atrasadas
--   ✅ monto_cuota              → Validaciones
--   ✅ total_pagado             → Calcular si está pagada
--   ✅ capital_pendiente        → Calcular saldo por cobrar
--   ✅ interes_pendiente        → Calcular saldo por cobrar
--   ✅ monto_mora               → Calcular saldo por cobrar
--   ✅ estado                   → Filtros (solo != 'PAGADO')

-- ============================================================================
-- 🗄️ TABLA 5: clientes (VALIDACIONES)
-- ============================================================================
-- Ubicación del modelo: backend/app/models/cliente.py
-- Nombre SQL: clientes
-- Uso: Validar que el cliente existe antes de crear un pago

-- Campos utilizados:
--   ✅ cedula                   → Validación con pagos.cedula_cliente

-- ============================================================================
-- 🗄️ TABLA 6: pagos_auditoria (AUDITORÍA)
-- ============================================================================
-- Ubicación del modelo: backend/app/models/pago_auditoria.py
-- Nombre SQL: pagos_auditoria
-- Uso: Registrar cambios y auditoría de pagos

-- Campos utilizados:
--   ✅ pago_id                  → FK a pagos.id
--   ✅ usuario                  → Usuario que hizo el cambio
--   ✅ accion                   → CREATE, UPDATE, DELETE
--   ✅ campo_modificado         → Campo que cambió
--   ✅ valor_anterior           → Valor anterior
--   ✅ valor_nuevo              → Valor nuevo
--   ✅ fecha_cambio             → Fecha del cambio

-- ============================================================================
-- 📝 ENDPOINTS DEL MÓDULO PAGOS Y SUS TABLAS
-- ============================================================================
-- Ubicación: backend/app/api/v1/endpoints/pagos.py

-- ============================================================================
-- 1. GET /api/v1/pagos/
-- ============================================================================
-- Descripción: Listar pagos con filtros y paginación
-- Tablas consultadas:
--   ✅ pagos_staging (PRINCIPAL) → Para obtener la lista de pagos
--   ✅ prestamos (SECUNDARIA)    → Para calcular cuotas atrasadas (JOIN con cuotas)
--   ✅ cuotas (SECUNDARIA)       → Para calcular cuotas atrasadas

-- Query SQL equivalente:
SELECT 
    ps.id_stg as id,
    ps.cedula_cliente,
    ps.fecha_pago,
    ps.monto_pagado,
    ps.numero_documento,
    ps.conciliado,
    ps.fecha_conciliacion
FROM pagos_staging ps
WHERE 
    (ps.cedula_cliente = :cedula OR :cedula IS NULL)
    AND (ps.fecha_pago::timestamp >= :fecha_desde OR :fecha_desde IS NULL)
    AND (ps.fecha_pago::timestamp <= :fecha_hasta OR :fecha_hasta IS NULL)
    AND ps.monto_pagado IS NOT NULL
    AND ps.monto_pagado != ''
    AND ps.monto_pagado ~ '^[0-9]+(\.[0-9]+)?$'
ORDER BY ps.id_stg DESC
LIMIT :per_page OFFSET :offset;

-- Query para calcular cuotas atrasadas (por cédula):
SELECT COUNT(c.id)
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.cedula = :cedula_cliente
  AND p.estado = 'APROBADO'
  AND c.fecha_vencimiento < CURRENT_DATE
  AND c.total_pagado < c.monto_cuota;

-- ============================================================================
-- 2. POST /api/v1/pagos/
-- ============================================================================
-- Descripción: Crear nuevo pago
-- Tablas utilizadas:
--   ✅ clientes (VALIDACIÓN)     → Verificar que el cliente existe
--   ✅ pagos (INSERT)            → Insertar el nuevo pago
--   ✅ cuotas (UPDATE)           → Aplicar pago a cuotas
--   ✅ prestamos (VALIDACIÓN)    → Validar préstamo si existe
--   ✅ pagos_auditoria (INSERT)  → Registrar auditoría

-- Query SQL equivalente (validación cliente):
SELECT COUNT(*)
FROM clientes
WHERE cedula = :cedula_cliente;

-- Query SQL equivalente (inserción):
INSERT INTO pagos (
    cedula_cliente, prestamo_id, numero_cuota,
    fecha_pago, fecha_registro, monto_pagado,
    numero_documento, institucion_bancaria,
    documento_nombre, documento_tipo, documento_tamaño, documento_ruta,
    conciliado, fecha_conciliacion, estado,
    activo, notas, usuario_registro, fecha_actualizacion
) VALUES (
    :cedula_cliente, :prestamo_id, :numero_cuota,
    :fecha_pago, NOW(), :monto_pagado,
    :numero_documento, :institucion_bancaria,
    :documento_nombre, :documento_tipo, :documento_tamaño, :documento_ruta,
    FALSE, NULL, 'PAGADO',
    TRUE, :notas, :usuario_registro, NOW()
);

-- Query SQL equivalente (actualizar cuotas):
UPDATE cuotas
SET 
    total_pagado = total_pagado + :monto_aplicar,
    capital_pagado = capital_pagado + :capital_aplicar,
    interes_pagado = interes_pagado + :interes_aplicar,
    estado = CASE 
        WHEN total_pagado + :monto_aplicar >= monto_cuota THEN 'PAGADO'
        ELSE estado
    END
WHERE prestamo_id = :prestamo_id
  AND numero_cuota = :numero_cuota;

-- ============================================================================
-- 3. PUT /api/v1/pagos/{pago_id}
-- ============================================================================
-- Descripción: Actualizar pago existente
-- Tablas utilizadas:
--   ✅ pagos (UPDATE)            → Actualizar el pago
--   ✅ pagos_auditoria (INSERT)  → Registrar cambios

-- Query SQL equivalente:
UPDATE pagos
SET 
    cedula_cliente = :cedula_cliente,
    prestamo_id = :prestamo_id,
    fecha_pago = :fecha_pago,
    monto_pagado = :monto_pagado,
    numero_documento = :numero_documento,
    fecha_actualizacion = NOW()
WHERE id = :pago_id;

-- ============================================================================
-- 4. DELETE /api/v1/pagos/{pago_id}
-- ============================================================================
-- Descripción: Eliminar pago (hard delete)
-- Tablas utilizadas:
--   ✅ pagos (DELETE)            → Eliminar el pago
--   ✅ pagos_auditoria (INSERT)  → Registrar eliminación

-- Query SQL equivalente:
DELETE FROM pagos
WHERE id = :pago_id;

-- ============================================================================
-- 5. GET /api/v1/pagos/stats
-- ============================================================================
-- Descripción: Obtener estadísticas de pagos
-- Tablas consultadas:
--   ✅ pagos_staging (PRINCIPAL) → Para contar y sumar pagos

-- Query SQL equivalente:
SELECT 
    COUNT(*) as total_pagos,
    COALESCE(SUM(monto_pagado::numeric), 0) as monto_total
FROM pagos_staging
WHERE monto_pagado IS NOT NULL
  AND monto_pagado != ''
  AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$'
  AND fecha_pago IS NOT NULL
  AND fecha_pago != ''
  AND fecha_pago ~ '^\d{4}-\d{2}-\d{2}';

-- ============================================================================
-- 6. GET /api/v1/pagos/kpis
-- ============================================================================
-- Descripción: Obtener KPIs de pagos (monto cobrado, saldo por cobrar, etc.)
-- Tablas consultadas:
--   ✅ pagos_staging (PRINCIPAL) → Para monto cobrado
--   ✅ cuotas (SECUNDARIA)       → Para saldo por cobrar
--   ✅ prestamos (SECUNDARIA)    → Para JOIN con cuotas
--   ✅ clientes (SECUNDARIA)     → Para contar clientes (vía prestamos)

-- Query SQL equivalente (monto cobrado):
SELECT COALESCE(SUM(monto_pagado::numeric), 0) AS monto_total
FROM pagos_staging
WHERE fecha_pago::timestamp >= :fecha_inicio
  AND fecha_pago::timestamp < :fecha_fin
  AND monto_pagado IS NOT NULL
  AND monto_pagado != ''
  AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$'
  AND monto_pagado::numeric >= 0;

-- Query SQL equivalente (saldo por cobrar):
SELECT COALESCE(SUM(
    COALESCE(c.capital_pendiente, 0) +
    COALESCE(c.interes_pendiente, 0) +
    COALESCE(c.monto_mora, 0)
), 0) AS saldo_por_cobrar
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.estado != 'PAGADO'
  AND p.estado = 'APROBADO';

-- Query SQL equivalente (clientes con préstamos):
SELECT COUNT(DISTINCT p.cedula) AS total_clientes
FROM prestamos p
INNER JOIN cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO';

-- Query SQL equivalente (clientes en mora):
SELECT COUNT(DISTINCT p.cedula) AS clientes_en_mora
FROM prestamos p
INNER JOIN cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento < CURRENT_DATE
  AND c.estado != 'PAGADO';

-- ============================================================================
-- 7. POST /api/v1/pagos/{pago_id}/aplicar-cuotas
-- ============================================================================
-- Descripción: Aplicar pago a cuotas manualmente
-- Tablas utilizadas:
--   ✅ pagos (SELECT)            → Obtener el pago
--   ✅ prestamos (VALIDACIÓN)    → Validar préstamo
--   ✅ cuotas (UPDATE)           → Aplicar pago a cuotas
--   ✅ pagos_auditoria (INSERT)  → Registrar auditoría

-- Query SQL equivalente:
SELECT *
FROM pagos
WHERE id = :pago_id;

-- Query SQL equivalente (obtener cuotas pendientes):
SELECT *
FROM cuotas
WHERE prestamo_id = :prestamo_id
  AND estado != 'PAGADO'
ORDER BY fecha_vencimiento ASC, numero_cuota ASC;

-- ============================================================================
-- ⚠️ DIFERENCIAS ENTRE pagos_staging Y pagos
-- ============================================================================
-- 
-- pagos_staging:
--   ✅ Usado para CONSULTAS (listar, estadísticas, KPIs)
--   ✅ Tiene campos TEXT que se convierten a tipos numéricos/fechas
--   ✅ NO tiene prestamo_id en la BD real
--   ✅ NO tiene estado en la BD real
--   ✅ NO tiene fecha_registro en la BD real
--   ✅ Campos: id_stg, cedula_cliente, fecha_pago (TEXT), monto_pagado (TEXT)
--
-- pagos:
--   ✅ Usado para OPERACIONES DE ESCRITURA (crear, actualizar, eliminar)
--   ✅ Tiene tipos de datos correctos (DateTime, Numeric, etc.)
--   ✅ Tiene prestamo_id para relacionar con préstamos
--   ✅ Tiene estado para controlar el estado del pago
--   ✅ Tiene fecha_registro para auditoría
--   ✅ Campos completos con todos los tipos correctos

-- ============================================================================
-- ✅ RESUMEN FINAL
-- ============================================================================
-- El módulo de pagos consulta las siguientes tablas:
--
-- Tablas principales:
--   ⭐ pagos_staging   → Consultas de lectura (listar, estadísticas, KPIs)
--   ⭐ pagos           → Operaciones de escritura (crear, actualizar, eliminar)
--
-- Tablas secundarias:
--   ⭐ prestamos       → Validaciones y JOINs
--   ⭐ cuotas          → Cálculos y aplicación de pagos
--   ⭐ clientes        → Validaciones
--   ⭐ pagos_auditoria → Auditoría de cambios
--
-- Endpoints y sus tablas principales:
--   ✅ GET /api/v1/pagos/              → pagos_staging (lectura)
--   ✅ POST /api/v1/pagos/             → pagos (escritura)
--   ✅ PUT /api/v1/pagos/{id}          → pagos (escritura)
--   ✅ DELETE /api/v1/pagos/{id}       → pagos (escritura)
--   ✅ GET /api/v1/pagos/stats         → pagos_staging (lectura)
--   ✅ GET /api/v1/pagos/kpis          → pagos_staging + cuotas + prestamos
--   ✅ POST /api/v1/pagos/{id}/aplicar-cuotas → pagos + cuotas
--
-- ============================================================================
-- FIN DEL DOCUMENTO
-- ============================================================================

