# 📊 Revisión de Endpoints - Análisis para Optimización

**Fecha:** 2025-11-09  
**Objetivo:** Revisar endpoints críticos del sistema para identificar oportunidades de optimización

---

## 🔍 ENDPOINTS REVISADOS

### 1. **`/api/v1/dashboard/kpis-principales`** ⚠️ CRÍTICO

**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py:2098`

**Estado Actual:**
- ✅ Cache: 5 minutos (300s)
- ✅ Queries optimizadas: Combina mes actual y anterior en una sola query
- ⚠️ Múltiples queries para diferentes KPIs
- ⚠️ Query de clientes por estado con JOINs

**Problemas Identificados:**

1. **Múltiples queries separadas:**
   ```python
   # Query 1: KPIs de préstamos (mes actual y anterior)
   kpis_prestamos = db.query(...).filter(...)
   
   # Query 2: Clientes por estado (mes actual)
   query_base_clientes = db.query(Cliente).join(Prestamo, ...)
   
   # Query 3: Clientes por estado (mes anterior)
   query_base_anterior = db.query(Cliente).join(Prestamo, ...)
   
   # Query 4: Morosidad actual
   morosidad_actual = _calcular_morosidad(...)
   
   # Query 5: Morosidad anterior
   morosidad_anterior = _calcular_morosidad(...)
   ```

2. **JOINs repetidos:**
   - Múltiples JOINs entre `Cliente` y `Prestamo` para calcular estados
   - Cada query de clientes hace un JOIN completo

3. **Falta de índices potenciales:**
   - `Prestamo.fecha_aprobacion` - usado frecuentemente
   - `Cliente.estado` - usado en agrupaciones
   - `Prestamo.estado` - usado en todos los filtros

**Recomendaciones:**
- ✅ Combinar queries de clientes en una sola con CASE WHEN
- ✅ Usar subqueries para morosidad en lugar de funciones separadas
- ⚠️ Agregar índices compuestos: `(estado, fecha_aprobacion)`
- ⚠️ Considerar materialized views para KPIs frecuentes

---

### 2. **`/api/v1/dashboard/financiamiento-por-rangos`** ⚠️ CRÍTICO

**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py:3120`

**Estado Actual:**
- ✅ Cache: 5 minutos (300s)
- ✅ Optimizado: Usa procesamiento en Python en lugar de CASE WHEN complejo
- ⚠️ Dos queries: una para IDs, otra para montos
- ⚠️ Procesamiento en memoria de todos los préstamos

**Problemas Identificados:**

1. **Doble query:**
   ```python
   # Query 1: Obtener IDs
   prestamo_ids_query = query_base.with_entities(Prestamo.id)
   prestamo_ids = [row[0] for row in prestamo_ids_result]
   
   # Query 2: Obtener montos
   query_sql = text("SELECT id, total_financiamiento FROM prestamos WHERE id = ANY(:ids)")
   ```

2. **Procesamiento en memoria:**
   - Carga todos los préstamos en memoria para clasificarlos
   - Con muchos préstamos (>10,000) puede ser lento

3. **Rangos fijos:**
   - 167 rangos de $300 cada uno (0-50,000)
   - Procesamiento O(n*m) donde n=préstamos, m=rangos

**Recomendaciones:**
- ✅ Usar una sola query con GROUP BY usando división entera
- ✅ Agregar índice en `total_financiamiento`
- ⚠️ Considerar usar `width_bucket` de PostgreSQL para rangos
- ⚠️ Limitar procesamiento a préstamos con filtros aplicados

**Query Optimizada Sugerida:**
```sql
SELECT 
  CASE 
    WHEN total_financiamiento >= 50000 THEN '50000+'
    ELSE CONCAT('$', FLOOR(total_financiamiento / 300) * 300, ' - $', (FLOOR(total_financiamiento / 300) + 1) * 300)
  END as categoria,
  COUNT(*) as cantidad_prestamos,
  SUM(total_financiamiento) as monto_total
FROM prestamos
WHERE estado = 'APROBADO' 
  AND total_financiamiento > 0
  -- filtros adicionales
GROUP BY categoria
ORDER BY MIN(total_financiamiento);
```

---

### 3. **`/api/v1/dashboard/financiamiento-tendencia-mensual`** ⚠️ CRÍTICO

**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py:3956`

**Estado Actual:**
- ✅ Cache: 10 minutos (600s)
- ✅ Query optimizada: GROUP BY año y mes
- ✅ Una sola query con GROUP BY

**Problemas Identificados:**

1. **EXTRACT en GROUP BY:**
   ```python
   func.extract("year", Prestamo.fecha_aprobacion).label("año"),
   func.extract("month", Prestamo.fecha_aprobacion).label("mes"),
   ```
   - EXTRACT puede ser lento sin índices apropiados

2. **Falta de índice en fecha_aprobacion:**
   - Si no hay índice, cada EXTRACT requiere scan completo

**Recomendaciones:**
- ✅ Agregar índice en `fecha_aprobacion`
- ✅ Considerar índice funcional: `(EXTRACT(YEAR FROM fecha_aprobacion), EXTRACT(MONTH FROM fecha_aprobacion))`
- ⚠️ Usar `date_trunc('month', fecha_aprobacion)` en PostgreSQL para mejor rendimiento

---

### 4. **`/api/v1/dashboard/composicion-morosidad`** ⚠️ MEDIO

**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py:3341`

**Estado Actual:**
- ⚠️ Sin cache
- ✅ Usa columnas calculadas (`dias_morosidad`, `monto_morosidad`)
- ⚠️ Carga todas las cuotas en memoria para agrupar

**Problemas Identificados:**

1. **Query con JOIN:**
   ```python
   query_base = (
       db.query(Cuota.id, Cuota.dias_morosidad, Cuota.monto_morosidad)
       .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
       .filter(...)
   )
   cuotas = query_base.all()  # Carga todas en memoria
   ```

2. **Procesamiento en Python:**
   - Agrupa cuotas por categoría en Python
   - Con muchas cuotas puede ser lento

**Recomendaciones:**
- ✅ Agregar cache (5 minutos)
- ✅ Usar GROUP BY en SQL en lugar de procesamiento en Python
- ✅ Agregar índice en `dias_morosidad` y `monto_morosidad`
- ⚠️ Considerar función para categorizar días de atraso en SQL

**Query Optimizada Sugerida:**
```sql
SELECT 
  CASE 
    WHEN dias_morosidad <= 5 THEN '0-5 días'
    WHEN dias_morosidad <= 15 THEN '5-15 días'
    WHEN dias_morosidad <= 60 THEN '1-2 meses'
    -- ... más casos
  END as categoria,
  COUNT(*) as cantidad_cuotas,
  SUM(monto_morosidad) as monto_total
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.dias_morosidad > 0
GROUP BY categoria
ORDER BY MIN(dias_morosidad);
```

---

### 5. **`/api/v1/cobranzas/clientes-atrasados`** ⚠️ MEDIO

**Ubicación:** `backend/app/api/v1/endpoints/cobranzas.py:249`

**Estado Actual:**
- ⚠️ Sin cache
- ✅ Usa subqueries para optimizar
- ✅ JOINs optimizados

**Problemas Identificados:**

1. **Subquery compleja:**
   ```python
   cuotas_vencidas_subq = (
       db.query(...)
       .filter(...)
       .group_by(Cuota.prestamo_id)
       .subquery()
   )
   ```
   - Subquery puede ser lenta con muchos préstamos

2. **Múltiples JOINs:**
   - JOIN con Cliente, Prestamo, subquery, y User
   - Puede ser lento sin índices apropiados

**Recomendaciones:**
- ✅ Agregar cache (2-5 minutos)
- ✅ Agregar índices en:
  - `cuotas.fecha_vencimiento`
  - `cuotas.prestamo_id`
  - `prestamos.cedula`
  - `prestamos.usuario_proponente`

---

## 📈 ANÁLISIS GENERAL

### Problemas Comunes Encontrados:

1. **Falta de Cache:**
   - Varios endpoints sin cache
   - Endpoints con datos históricos deberían tener cache más largo

2. **Queries N+1 Potenciales:**
   - Algunos endpoints hacen múltiples queries cuando podrían combinarse
   - JOINs repetidos en diferentes queries

3. **Falta de Índices:**
   - `fecha_aprobacion` usado frecuentemente sin índice explícito
   - `estado` usado en filtros sin índice compuesto
   - `total_financiamiento` usado en rangos sin índice

4. **Procesamiento en Memoria:**
   - Varios endpoints cargan todos los datos y procesan en Python
   - Deberían usar GROUP BY en SQL cuando sea posible

5. **Queries Separadas:**
   - Algunos endpoints hacen 3-5 queries cuando podrían ser 1-2

---

## 🎯 PRIORIDADES DE OPTIMIZACIÓN

### **ALTA PRIORIDAD** 🔴

1. **Agregar índices críticos:**
   ```sql
   CREATE INDEX idx_prestamos_estado_fecha ON prestamos(estado, fecha_aprobacion);
   CREATE INDEX idx_prestamos_total_financiamiento ON prestamos(total_financiamiento) WHERE estado = 'APROBADO';
   CREATE INDEX idx_cuotas_dias_morosidad ON cuotas(dias_morosidad) WHERE dias_morosidad > 0;
   CREATE INDEX idx_cuotas_fecha_vencimiento ON cuotas(fecha_vencimiento);
   ```

2. **Optimizar `financiamiento-por-rangos`:**
   - Usar GROUP BY en SQL en lugar de procesamiento en Python
   - Reducir de 2 queries a 1

3. **Agregar cache a endpoints sin cache:**
   - `composicion-morosidad`: 5 minutos
   - `clientes-atrasados`: 2-5 minutos

### **MEDIA PRIORIDAD** 🟡

4. **Combinar queries en `kpis-principales`:**
   - Reducir de 5 queries a 2-3
   - Usar subqueries para morosidad

5. **Optimizar `composicion-morosidad`:**
   - Usar GROUP BY en SQL
   - Agregar función SQL para categorizar días

6. **Optimizar `financiamiento-tendencia-mensual`:**
   - Usar `date_trunc` en lugar de EXTRACT
   - Agregar índice funcional

### **BAJA PRIORIDAD** 🟢

7. **Revisar otros endpoints menos críticos**
8. **Considerar materialized views para KPIs**
9. **Implementar paginación en endpoints que retornan muchos datos**

---

## 📝 PRÓXIMOS PASOS

1. ✅ **Revisión completada** - Endpoints críticos identificados
2. ⏳ **Implementar índices** - Crear migración con índices críticos
3. ⏳ **Optimizar queries** - Refactorizar endpoints con más impacto
4. ⏳ **Agregar cache** - Implementar cache en endpoints sin cache
5. ⏳ **Monitorear performance** - Medir mejoras después de optimizaciones

---

## 🔗 REFERENCIAS

- Documentación de optimización: `Documentos/Analisis/2025-11/OPTIMIZACIONES_BACKEND_FRONTEND.md`
- Script de análisis de logs: `backend/scripts/analizar_logs_performance.py`
- Monitor de performance: `backend/app/core/performance_monitor.py`

