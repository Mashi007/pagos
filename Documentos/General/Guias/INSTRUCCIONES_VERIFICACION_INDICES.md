# 📋 Instrucciones para Verificar Índices

## Problema Resuelto

El error `syntax error at or near "backend"` se debía a que el script original usaba comandos `\echo` que solo funcionan en `psql` (línea de comandos), no en herramientas GUI.

## Solución: Dos Versiones del Script

### Versión 1: `verificar_uso_indices_puro.sql` (Recomendada)
**Para:** Herramientas GUI (DBeaver, pgAdmin, DataGrip, etc.)
- ✅ Solo contiene queries SQL puras
- ✅ Sin comandos `\echo`
- ✅ Compatible con todas las herramientas

### Versión 2: `verificar_uso_indices.sql` (Original)
**Para:** Línea de comandos `psql`
- ✅ Incluye mensajes informativos con `\echo`
- ✅ Solo funciona en `psql`

---

## Cómo Ejecutar

### Opción 1: Herramienta GUI (Recomendado)

1. Abre tu herramienta de base de datos (DBeaver, pgAdmin, etc.)
2. Abre el archivo: `backend/scripts/verificar_uso_indices_puro.sql`
3. Ejecuta cada query individualmente o todas juntas
4. Revisa los resultados de cada `EXPLAIN ANALYZE`

### Opción 2: Línea de Comandos psql

```bash
psql -U usuario -d pagos_db -f backend/scripts/verificar_uso_indices.sql
```

### Opción 3: Ejecutar Queries Individuales

Copia y pega cada query del script en tu herramienta de base de datos y ejecuta una por una.

---

## Qué Buscar en los Resultados

### ✅ Indicadores de Éxito

#### 1. Index Only Scan (EXCELENTE)
```
Index Only Scan using idx_pagos_fecha_pago_activo_monto
Heap Fetches: 0
Execution Time: 0.203 ms
```
**Significado:** El índice contiene toda la información, no necesita leer la tabla.

#### 2. Index Scan (IDEAL)
```
Index Scan using idx_cuotas_fecha_vencimiento_estado
Execution Time: 2.5 ms
```
**Significado:** Usa el índice para buscar y luego lee solo las filas necesarias.

#### 3. Bitmap Index Scan (BUENO)
```
Bitmap Index Scan using idx_prestamos_fecha_registro_estado
Execution Time: 5.1 ms
```
**Significado:** Usa el índice para crear un bitmap, útil para múltiples condiciones.

### ❌ Indicador de Problema

#### Seq Scan (MALO)
```
Seq Scan on pagos
Execution Time: 2500.0 ms
```
**Significado:** No está usando ningún índice, está leyendo toda la tabla.

---

## Verificaciones por Índice

### 1. `idx_pagos_fecha_pago_activo_monto`
**Query #1 del script**
**Resultado Esperado:** `Index Only Scan` o `Index Scan`
**Tiempo Esperado:** < 1ms

### 2. `idx_cuotas_fecha_vencimiento_estado`
**Query #2 del script**
**Resultado Esperado:** `Index Scan` o `Bitmap Index Scan`
**Tiempo Esperado:** < 5ms

### 3. `idx_prestamos_fecha_registro_estado`
**Query #3 del script**
**Resultado Esperado:** `Index Scan` o `Bitmap Index Scan`
**Tiempo Esperado:** < 5ms

### 4. `idx_pagos_prestamo_id_activo_fecha`
**Query #4 del script**
**Resultado Esperado:** `Index Scan`
**Tiempo Esperado:** < 10ms

### 5. `idx_cuotas_prestamo_estado_fecha_vencimiento`
**Query #5 del script**
**Resultado Esperado:** `Index Scan`
**Tiempo Esperado:** < 50ms

### 6. `idx_prestamos_estado_analista_concesionario`
**Query #6 del script**
**Resultado Esperado:** `Index Scan` o `Bitmap Index Scan`
**Tiempo Esperado:** < 10ms

### 7. `idx_prestamos_estado_cedula`
**Query #7 del script**
**Resultado Esperado:** `Index Scan`
**Tiempo Esperado:** < 10ms

### 8. `idx_prestamos_usuario_proponente`
**Query #8 del script**
**Resultado Esperado:** `Index Scan`
**Tiempo Esperado:** < 20ms

---

## Si un Índice NO se Está Usando

### Pasos de Diagnóstico

1. **Verificar que el índice existe:**
   ```sql
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE indexname = 'idx_nombre_indice';
   ```

2. **Actualizar estadísticas:**
   ```sql
   ANALYZE tabla_nombre;
   ```

3. **Verificar que los filtros coinciden:**
   - Los filtros en WHERE deben coincidir con las columnas del índice
   - Los filtros del índice (WHERE en CREATE INDEX) deben aplicarse

4. **Verificar tamaño de la tabla:**
   - En tablas muy pequeñas (< 1000 filas), PostgreSQL puede preferir Seq Scan
   - Esto es normal y aceptable

---

## Ejemplo de Resultado Correcto

Ya viste un resultado excelente anteriormente:

```
Index Only Scan using idx_pagos_fecha_pago_activo_monto
  Index Cond: ((fecha_pago >= '2024-01-01'::date) AND (fecha_pago <= '2024-12-31'::date))
  Heap Fetches: 0
Planning Time: 0.611 ms
Execution Time: 0.203 ms  ← ✅ Excelente!
```

Todos los demás índices deberían mostrar resultados similares.

---

## Archivos Disponibles

1. ✅ **`verificar_uso_indices_puro.sql`** - Versión sin `\echo` (Recomendada para GUI)
2. ⚠️ **`verificar_uso_indices.sql`** - Versión con `\echo` (Solo para psql)

---

## Resumen

✅ **Script corregido:** `verificar_uso_indices_puro.sql`
✅ **Compatible:** Todas las herramientas GUI
✅ **8 verificaciones:** Todos los índices críticos
✅ **Fácil de usar:** Ejecutar cada query individualmente

Usa la versión `_puro.sql` para evitar errores de sintaxis.

