# 🚀 Optimizaciones Aplicadas a Endpoints Lentos

## Fecha: 2025-11-05

---

## 📊 Análisis de Performance

### Endpoints Optimizados

#### 1. `/api/v1/dashboard/financiamiento-por-rangos`
**Tiempo Anterior:** 5.8-6 segundos  
**Tiempo Esperado:** 1-2 segundos  
**Mejora Esperada:** **70-80%**

**Problema Identificado:**
- Hacía 5 queries en loop (una por cada rango)
- Cada query ejecutaba `count()` y `sum()` por separado
- No tenía cache

**Optimizaciones Aplicadas:**
1. ✅ **Query única con CASE WHEN**: Reemplazado loop de 5 queries por una sola query con `CASE WHEN` y `GROUP BY`
2. ✅ **Cálculo de totales optimizado**: Una sola query para contar y sumar totales
3. ✅ **Cache agregado**: `@cache_result(ttl=300)` para cachear resultados por 5 minutos

**Código Optimizado:**
```python
# ❌ ANTES: 5 queries en loop
for min_val, max_val, categoria in rangos:
    query_rango = query_base.filter(...)
    cantidad = query_rango.count()  # Query 1
    monto_total = query_rango.with_entities(func.sum(...)).scalar()  # Query 2

# ✅ DESPUÉS: 1 query con CASE WHEN
distribucion_query = (
    query_base
    .with_entities(
        case(*case_conditions, else_="Otro").label("rango"),
        func.count(Prestamo.id).label("cantidad"),
        func.sum(Prestamo.total_financiamiento).label("monto_total")
    )
    .group_by("rango")
    .all()
)
```

---

#### 2. `/api/v1/dashboard/evolucion-general-mensual`
**Tiempo Anterior:** 1.3-1.9 segundos  
**Tiempo Esperado:** 0.5-1 segundo  
**Mejora Esperada:** **40-50%**

**Problema Identificado:**
- Loop por mes haciendo queries individuales para morosidad y activos
- Para 6 meses = 12 queries (2 por mes)
- No aprovechaba índices de manera óptima

**Optimizaciones Aplicadas:**
1. ✅ **Query única para morosidad**: Reemplazado loop por una query con `GROUP BY`
2. ✅ **Query única para activos**: Reemplazado loop por una query con `GROUP BY` y cálculo de acumulado
3. ✅ **Fallback inteligente**: Si la query optimizada falla, usa el método original

**Código Optimizado:**
```python
# ❌ ANTES: Loop con queries por mes
for mes_info in meses_lista:
    query_morosidad = db.query(...).filter(...).scalar()  # Query 1
    query_activos = db.query(...).filter(...).scalar()    # Query 2

# ✅ DESPUÉS: Query única con GROUP BY
query_morosidad_optimizada = db.execute(
    text("""
        SELECT 
            EXTRACT(YEAR FROM c.fecha_vencimiento)::integer as año,
            EXTRACT(MONTH FROM c.fecha_vencimiento)::integer as mes,
            COALESCE(SUM(c.monto_cuota), 0) as morosidad
        FROM cuotas c
        INNER JOIN prestamos p ON c.prestamo_id = p.id
        WHERE p.estado = 'APROBADO'
          AND c.fecha_vencimiento <= :fecha_limite
          AND c.estado != 'PAGADO'
        GROUP BY 
            EXTRACT(YEAR FROM c.fecha_vencimiento),
            EXTRACT(MONTH FROM c.fecha_vencimiento)
    """).bindparams(fecha_limite=fecha_ultima_morosidad)
)
```

---

## 📈 Impacto Esperado

### Reducción de Queries

| Endpoint | Queries Anteriores | Queries Optimizadas | Reducción |
|----------|-------------------|---------------------|-----------|
| `/financiamiento-por-rangos` | **10 queries** (5 rangos × 2) | **2 queries** | **80%** |
| `/evolucion-general-mensual` | **12+ queries** (6 meses × 2+) | **4 queries** | **67%** |

### Mejora de Performance

| Endpoint | Tiempo Anterior | Tiempo Esperado | Mejora |
|----------|----------------|------------------|---------|
| `/financiamiento-por-rangos` | 5.8-6 seg | **1-2 seg** | **70-80%** |
| `/evolucion-general-mensual` | 1.3-1.9 seg | **0.5-1 seg** | **40-50%** |

---

## ✅ Optimizaciones Implementadas

### 1. Función `_procesar_distribucion_rango_monto`
- ✅ Reemplazado loop de 5 queries por 1 query con `CASE WHEN`
- ✅ Usa `GROUP BY` para clasificar por rango
- ✅ Reduce de 10 queries a 1 query

### 2. Endpoint `obtener_financiamiento_por_rangos`
- ✅ Cache agregado: `@cache_result(ttl=300)`
- ✅ Cálculo de totales optimizado (1 query en lugar de 2)
- ✅ Logging de tiempo de ejecución

### 3. Endpoint `obtener_evolucion_general_mensual`
- ✅ Query optimizada para morosidad con `GROUP BY`
- ✅ Query optimizada para activos acumulados
- ✅ Fallback inteligente si las queries optimizadas fallan

---

## 🔍 Verificación

### Próximos Pasos

1. **Monitorear logs** después del despliegue para verificar mejoras
2. **Comparar tiempos** antes/después de las optimizaciones
3. **Verificar uso de índices** con `EXPLAIN ANALYZE` si es necesario

### Indicadores de Éxito

- ✅ `/financiamiento-por-rangos`: Tiempo < 2 segundos
- ✅ `/evolucion-general-mensual`: Tiempo < 1 segundo
- ✅ Logs muestran tiempos de ejecución reducidos
- ✅ Cache funcionando (segunda llamada mucho más rápida)

---

## 📝 Notas Técnicas

### Cache
- TTL: 300 segundos (5 minutos)
- Key prefix: `dashboard`
- Se invalida automáticamente después de 5 minutos

### Índices Usados
- `idx_prestamos_fecha_registro_estado` - Para queries de financiamiento
- `idx_cuotas_fecha_vencimiento_estado` - Para queries de morosidad
- `idx_pagos_fecha_pago_activo_monto` - Para queries de pagos

---

## ✅ Resumen

**Optimizaciones aplicadas:**
- ✅ 2 endpoints optimizados
- ✅ Reducción de 22+ queries a 6 queries
- ✅ Cache agregado a 1 endpoint
- ✅ Mejora esperada: 40-80% más rápido

**Estado:** Listo para despliegue y monitoreo

