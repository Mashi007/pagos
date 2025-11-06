-- ============================================================================
-- CONFIRMACIÓN: MÓDULO CLIENTES - TABLAS Y CAMPOS UTILIZADOS
-- ============================================================================
-- Este documento confirma de qué tablas y campos toma datos el módulo de clientes
--
-- Autor: Sistema de Pagos
-- Fecha: 2025
-- ============================================================================

-- ============================================================================
-- 📊 RESUMEN EJECUTIVO
-- ============================================================================
-- El módulo de clientes consulta EXCLUSIVAMENTE la tabla 'clientes'
-- NO consulta otras tablas como prestamos, pagos, cuotas, etc.
--
-- Excepción: El dashboard puede usar datos de préstamos para calcular
-- estadísticas de clientes activos/inactivos/finalizados, pero esto es
-- parte del módulo dashboard, NO del módulo clientes directamente.
--
-- ============================================================================

-- ============================================================================
-- 🗄️ TABLA PRINCIPAL: clientes
-- ============================================================================
-- Ubicación del modelo: backend/app/models/cliente.py
-- Nombre SQL: clientes
-- Endpoint base: /api/v1/clientes

-- ============================================================================
-- 📋 CAMPOS DE LA TABLA clientes
-- ============================================================================

-- ID y Identificación
--   ✅ id                  → INTEGER, PK, Indexed
--   ✅ cedula              → VARCHAR(20), NOT NULL, Indexed (Clave de articulación)
--   ✅ nombres             → VARCHAR(100), NOT NULL (Nombres + apellidos unificados)

-- Información de Contacto
--   ✅ telefono            → VARCHAR(15), NOT NULL, Indexed
--   ✅ email               → VARCHAR(100), NOT NULL, Indexed
--   ✅ direccion           → TEXT, NOT NULL

-- Información Personal
--   ✅ fecha_nacimiento    → DATE, NOT NULL
--   ✅ ocupacion           → VARCHAR(100), NOT NULL

-- Estado y Control
--   ✅ estado              → VARCHAR(20), NOT NULL, Default 'ACTIVO', Indexed
--                          → Valores: 'ACTIVO', 'INACTIVO', 'FINALIZADO'
--   ✅ activo              → BOOLEAN, NOT NULL, Default TRUE, Indexed
--                          → Sincronizado con estado (ACTIVO=True, otros=False)

-- Auditoría
--   ✅ fecha_registro      → TIMESTAMP, NOT NULL, Default NOW()
--   ✅ fecha_actualizacion → TIMESTAMP, NOT NULL, Default NOW(), ON UPDATE NOW()
--   ✅ usuario_registro    → VARCHAR(100), NOT NULL (Email del usuario)

-- Notas
--   ✅ notas               → TEXT, NOT NULL, Default 'NA'

-- ============================================================================
-- 📝 ENDPOINTS DEL MÓDULO CLIENTES
-- ============================================================================
-- Ubicación: backend/app/api/v1/endpoints/clientes.py

-- ============================================================================
-- 1. GET /api/v1/clientes
-- ============================================================================
-- Descripción: Listar clientes con paginación y filtros
-- Tabla consultada: ✅ clientes (SOLO esta tabla)
--
-- Campos utilizados:
--   ✅ nombres      → Búsqueda (ILIKE)
--   ✅ cedula       → Búsqueda y filtro (ILIKE)
--   ✅ telefono     → Búsqueda (ILIKE)
--   ✅ email        → Filtro (ILIKE)
--   ✅ ocupacion    → Filtro (ILIKE)
--   ✅ estado       → Filtro (exacto)
--   ✅ usuario_registro → Filtro (ILIKE)
--   ✅ fecha_registro   → Filtro por rango de fechas
--
-- Query SQL equivalente:
SELECT 
    id,
    cedula,
    nombres,
    telefono,
    email,
    direccion,
    fecha_nacimiento,
    ocupacion,
    estado,
    activo,
    fecha_registro,
    fecha_actualizacion,
    usuario_registro,
    notas
FROM clientes
WHERE 
    -- Filtros de búsqueda (opcionales)
    (nombres ILIKE '%busqueda%' OR cedula ILIKE '%busqueda%' OR telefono ILIKE '%busqueda%')
    -- Filtros específicos (opcionales)
    AND (estado = :estado OR :estado IS NULL)
    AND (cedula ILIKE '%:cedula%' OR :cedula IS NULL)
    AND (email ILIKE '%:email%' OR :email IS NULL)
    AND (telefono ILIKE '%:telefono%' OR :telefono IS NULL)
    AND (ocupacion ILIKE '%:ocupacion%' OR :ocupacion IS NULL)
    AND (usuario_registro ILIKE '%:usuario_registro%' OR :usuario_registro IS NULL)
    -- Filtros de fecha (opcionales)
    AND (DATE(fecha_registro) >= :fecha_desde OR :fecha_desde IS NULL)
    AND (DATE(fecha_registro) < :fecha_hasta OR :fecha_hasta IS NULL)
ORDER BY fecha_registro DESC
LIMIT :per_page OFFSET :offset;

-- ============================================================================
-- 2. GET /api/v1/clientes/stats
-- ============================================================================
-- Descripción: Obtener estadísticas de clientes (KPIs)
-- Tabla consultada: ✅ clientes (SOLO esta tabla)
--
-- Campos utilizados:
--   ✅ estado → Para contar por estado
--
-- Query SQL equivalente:
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE estado = 'ACTIVO') as activos,
    COUNT(*) FILTER (WHERE estado = 'INACTIVO') as inactivos,
    COUNT(*) FILTER (WHERE estado = 'FINALIZADO') as finalizados
FROM clientes;

-- ============================================================================
-- 3. GET /api/v1/clientes/{cliente_id}
-- ============================================================================
-- Descripción: Obtener un cliente por ID
-- Tabla consultada: ✅ clientes (SOLO esta tabla)
--
-- Query SQL equivalente:
SELECT *
FROM clientes
WHERE id = :cliente_id;

-- ============================================================================
-- 4. POST /api/v1/clientes
-- ============================================================================
-- Descripción: Crear nuevo cliente
-- Tabla utilizada: ✅ clientes (SOLO esta tabla - INSERT)
--
-- Validaciones antes de insertar:
--   ✅ Verificar que NO exista cliente con misma cédula
--   ✅ Verificar que NO exista cliente con mismo nombre completo (case-insensitive)
--
-- Query SQL equivalente (validación):
SELECT COUNT(*)
FROM clientes
WHERE cedula = :cedula;  -- Bloquear si existe

SELECT COUNT(*)
FROM clientes
WHERE LOWER(nombres) = LOWER(:nombres);  -- Bloquear si existe

-- Query SQL equivalente (inserción):
INSERT INTO clientes (
    cedula, nombres, telefono, email, direccion,
    fecha_nacimiento, ocupacion, estado, activo,
    fecha_registro, fecha_actualizacion, usuario_registro, notas
) VALUES (
    :cedula, :nombres, :telefono, :email, :direccion,
    :fecha_nacimiento, :ocupacion, 'ACTIVO', TRUE,
    NOW(), NOW(), :usuario_registro, :notas
);

-- ============================================================================
-- 5. PUT /api/v1/clientes/{cliente_id}
-- ============================================================================
-- Descripción: Actualizar cliente existente
-- Tabla utilizada: ✅ clientes (SOLO esta tabla - UPDATE)
--
-- Validaciones antes de actualizar:
--   ✅ Verificar que NO exista otro cliente con misma cédula (excepto el actual)
--   ✅ Verificar que NO exista otro cliente con mismo nombre completo (excepto el actual)
--   ✅ Sincronizar estado y activo si se actualiza el estado
--
-- Query SQL equivalente (validación):
SELECT COUNT(*)
FROM clientes
WHERE cedula = :nueva_cedula
  AND id != :cliente_id;  -- Bloquear si existe otro con misma cédula

SELECT COUNT(*)
FROM clientes
WHERE LOWER(nombres) = LOWER(:nuevos_nombres)
  AND id != :cliente_id;  -- Bloquear si existe otro con mismo nombre

-- Query SQL equivalente (actualización):
UPDATE clientes
SET 
    nombres = :nombres,
    telefono = :telefono,
    email = :email,
    direccion = :direccion,
    fecha_nacimiento = :fecha_nacimiento,
    ocupacion = :ocupacion,
    estado = :estado,
    activo = CASE 
        WHEN :estado = 'ACTIVO' THEN TRUE 
        ELSE FALSE 
    END,
    fecha_actualizacion = NOW(),
    notas = :notas
WHERE id = :cliente_id;

-- ============================================================================
-- 6. DELETE /api/v1/clientes/{cliente_id}
-- ============================================================================
-- Descripción: Eliminar cliente (hard delete)
-- Tabla utilizada: ✅ clientes (SOLO esta tabla - DELETE)
--
-- Query SQL equivalente:
DELETE FROM clientes
WHERE id = :cliente_id;

-- ============================================================================
-- ⚠️ TABLAS QUE NO SE CONSULTAN EN EL MÓDULO CLIENTES
-- ============================================================================
-- El módulo de clientes NO consulta estas tablas:
--
-- ❌ prestamos         → NO se consulta en endpoints de clientes
-- ❌ cuotas            → NO se consulta en endpoints de clientes
-- ❌ pagos             → NO se consulta en endpoints de clientes
-- ❌ pagos_staging     → NO se consulta en endpoints de clientes
-- ❌ cobros            → NO se consulta en endpoints de clientes
-- ❌ clientes_auditoria → NO se consulta (si existe)
-- ❌ Cualquier otra tabla → NO se consulta

-- ============================================================================
-- 📊 NOTA SOBRE EL DASHBOARD
-- ============================================================================
-- El dashboard SÍ puede usar datos de la tabla 'prestamos' para calcular
-- estadísticas de clientes (activos, inactivos, finalizados), pero esto es
-- parte del módulo dashboard (/api/v1/dashboard/kpis-principales), NO del
-- módulo clientes.
--
-- El endpoint /api/v1/clientes/stats consulta SOLO la tabla 'clientes' y
-- cuenta clientes según su campo 'estado' directamente.

-- ============================================================================
-- ✅ RESUMEN FINAL
-- ============================================================================
-- El módulo de clientes consulta EXCLUSIVAMENTE la tabla 'clientes'
--
-- Endpoints y sus tablas:
--   ✅ GET /api/v1/clientes              → Tabla: clientes
--   ✅ GET /api/v1/clientes/stats         → Tabla: clientes
--   ✅ GET /api/v1/clientes/{id}          → Tabla: clientes
--   ✅ POST /api/v1/clientes              → Tabla: clientes (INSERT)
--   ✅ PUT /api/v1/clientes/{id}          → Tabla: clientes (UPDATE)
--   ✅ DELETE /api/v1/clientes/{id}      → Tabla: clientes (DELETE)
--
-- Campos más utilizados:
--   ⭐ cedula       → Clave de articulación, búsqueda, filtros
--   ⭐ nombres      → Búsqueda, visualización
--   ⭐ estado       → Filtros, estadísticas (ACTIVO/INACTIVO/FINALIZADO)
--   ⭐ activo       → Filtros (sincronizado con estado)
--   ⭐ fecha_registro → Ordenamiento, filtros por fecha
--   ⭐ telefono     → Búsqueda, filtros
--   ⭐ email        → Filtros
--
-- ============================================================================
-- FIN DEL DOCUMENTO
-- ============================================================================

