# 📋 Comandos SQL Individuales (Sin Errores)

## ⚠️ Si tienes error de sintaxis, ejecuta estos comandos UNO POR UNO

---

## 1. ACTUALIZAR ESTADÍSTICAS (Importante)

Ejecuta estos comandos **uno por uno** en DBeaver:

```sql
ANALYZE prestamos;
```

```sql
ANALYZE cuotas;
```

```sql
ANALYZE pagos;
```

---

## 2. VERIFICAR ESTADÍSTICAS ACTUALIZADAS

```sql
SELECT 
    schemaname,
    tablename,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE tablename IN ('prestamos', 'cuotas', 'pagos')
ORDER BY tablename;
```

---

## 3. VERIFICAR ÍNDICES CREADOS

```sql
SELECT 
    tablename,
    indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('prestamos', 'cuotas', 'pagos')
  AND indexname IN (
    'idx_prestamos_fecha_aprobacion_ym',
    'idx_prestamos_cedula_estado',
    'idx_prestamos_aprobacion_estado_analista',
    'idx_prestamos_concesionario_estado',
    'idx_prestamos_modelo_estado',
    'idx_cuotas_fecha_vencimiento_ym',
    'idx_cuotas_prestamo_fecha_vencimiento',
    'idx_pagos_fecha_pago_activo',
    'idx_pagos_prestamo_fecha'
  )
ORDER BY tablename, indexname;
```

---

## 4. VERIFICAR ESTADO DE ÍNDICES

```sql
SELECT 
    i.indexrelid::regclass AS index_name,
    t.relname AS table_name,
    i.indisvalid AS es_valido,
    i.indisready AS esta_listo,
    i.indislive AS esta_activo
FROM pg_index i
JOIN pg_class t ON i.indrelid = t.oid
WHERE t.relname IN ('prestamos', 'cuotas', 'pagos')
  AND i.indexrelid::regclass::text LIKE 'idx_%'
ORDER BY t.relname, i.indexrelid::regclass;
```

---

## 5. PROBAR QUERY CON EXPLAIN ANALYZE

```sql
EXPLAIN ANALYZE 
SELECT 
    EXTRACT(YEAR FROM fecha_aprobacion),
    EXTRACT(MONTH FROM fecha_aprobacion),
    COUNT(*)
FROM prestamos
WHERE estado = 'APROBADO'
GROUP BY EXTRACT(YEAR FROM fecha_aprobacion), EXTRACT(MONTH FROM fecha_aprobacion);
```

**Después de ejecutar ANALYZE, debería mostrar:**
- `Index Scan using idx_prestamos_fecha_aprobacion_ym` (si hay suficientes datos)
- O `Seq Scan` (si la tabla es pequeña, lo cual es normal)

---

## 6. VER TAMAÑO DE TABLAS

```sql
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS tamaño_total,
    pg_size_pretty(pg_relation_size('public.'||tablename)) AS tamaño_tabla
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('prestamos', 'cuotas', 'pagos')
ORDER BY pg_total_relation_size('public.'||tablename) DESC;
```

---

## 7. VER USO DE ÍNDICES

```sql
SELECT 
    tablename,
    indexrelname AS index_name,
    idx_scan AS veces_usado
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND tablename IN ('prestamos', 'cuotas', 'pagos')
  AND indexrelname LIKE 'idx_%'
ORDER BY tablename, idx_scan DESC;
```

---

## ⚠️ IMPORTANTE

1. **Ejecuta los comandos UNO POR UNO** - No ejecutes todo el script de una vez
2. **Copia y pega cada comando** individualmente en DBeaver
3. **Si hay error**, verifica que no haya caracteres especiales o espacios extra

---

## ✅ ORDEN RECOMENDADO

1. Primero: Ejecutar `ANALYZE` (comandos 1-3)
2. Segundo: Verificar estadísticas (comando 2)
3. Tercero: Probar query (comando 5)
4. Cuarto: Verificar índices (comandos 3, 4, 7)

