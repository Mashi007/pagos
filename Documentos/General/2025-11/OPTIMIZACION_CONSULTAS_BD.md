# 🚀 Optimización de Consultas de Base de Datos

## 📋 Resumen Ejecutivo

Este documento identifica problemas de rendimiento en las consultas del dashboard y propone soluciones concretas para mejorar los tiempos de respuesta.

## 🔴 Problemas Identificados

### 1. **N+1 Queries** (CRÍTICO)

#### Problema: `obtener_resumen_prestamos_cliente`
**Ubicación:** `backend/app/api/v1/endpoints/prestamos.py:639-695`

**Código actual:**
```python
prestamos = db.query(Prestamo).filter(Prestamo.cedula == cedula).all()

for row in prestamos:
    # ❌ Query individual por cada préstamo
    cuotas = db.query(Cuota).filter(Cuota.prestamo_id == row.id).all()
```

**Impacto:** Si un cliente tiene 5 préstamos, se ejecutan 6 queries (1 + 5)

**Solución:**
```python
# ✅ Una sola query con JOIN
prestamos_ids = [p.id for p in prestamos]

# Query optimizada con agregación
cuotas_agregadas = (
    db.query(
        Cuota.prestamo_id,
        func.sum(Cuota.capital_pendiente + Cuota.interes_pendiente + Cuota.monto_mora).label('saldo_pendiente'),
        func.sum(
            case(
                (and_(
                    Cuota.fecha_vencimiento < date.today(),
                    Cuota.estado != "PAGADO"
                ), 1),
                else_=0
            )
        ).label('cuotas_en_mora')
    )
    .filter(Cuota.prestamo_id.in_(prestamos_ids))
    .group_by(Cuota.prestamo_id)
    .all()
)

# Crear diccionario para lookup rápido
cuotas_por_prestamo = {row.prestamo_id: row for row in cuotas_agregadas}

for prestamo in prestamos:
    datos = cuotas_por_prestamo.get(prestamo.id)
    saldo_pendiente = float(datos.saldo_pendiente) if datos else 0.0
    cuotas_en_mora = int(datos.cuotas_en_mora) if datos else 0
```

**Mejora esperada:** De 6 queries a 2 queries (reducción de 66%)

---

### 2. **Múltiples Queries Separadas en KPIs** (ALTO)

#### Problema: `obtener_kpis_principales`
**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py:1780-1963`

**Código actual:**
```python
# ❌ 8 queries separadas para calcular KPIs
query_prestamos_actual = db.query(func.sum(Prestamo.total_financiamiento))...
query_prestamos_anterior = db.query(func.sum(Prestamo.total_financiamiento))...
query_creditos_nuevos_actual = db.query(func.count(Prestamo.id))...
query_creditos_nuevos_anterior = db.query(func.count(Prestamo.id))...
query_clientes_activos = db.query(func.count(func.distinct(Prestamo.cedula)))...
query_clientes_finalizados = db.query(func.count(func.distinct(Prestamo.cedula)))...
query_clientes_inactivos = db.query(func.count(func.distinct(Prestamo.cedula)))...
# ... más queries
```

**Solución: Combinar queries con CASE WHEN**
```python
# ✅ Una sola query para préstamos actual y anterior
kpis_prestamos = (
    db.query(
        func.sum(
            case(
                (and_(
                    Prestamo.fecha_aprobacion >= fecha_inicio_mes_actual,
                    Prestamo.fecha_aprobacion < fecha_fin_mes_actual
                ), Prestamo.total_financiamiento),
                else_=0
            )
        ).label('total_actual'),
        func.sum(
            case(
                (and_(
                    Prestamo.fecha_aprobacion >= fecha_inicio_mes_anterior,
                    Prestamo.fecha_aprobacion < fecha_fin_mes_anterior
                ), Prestamo.total_financiamiento),
                else_=0
            )
        ).label('total_anterior'),
        func.count(
            case(
                (and_(
                    Prestamo.fecha_aprobacion >= fecha_inicio_mes_actual,
                    Prestamo.fecha_aprobacion < fecha_fin_mes_actual
                ), 1),
                else_=None
            )
        ).label('creditos_actual'),
        func.count(
            case(
                (and_(
                    Prestamo.fecha_aprobacion >= fecha_inicio_mes_anterior,
                    Prestamo.fecha_aprobacion < fecha_fin_mes_anterior
                ), 1),
                else_=None
            )
        ).label('creditos_anterior')
    )
    .filter(Prestamo.estado == "APROBADO")
)

# Aplicar filtros
kpis_prestamos = FiltrosDashboard.aplicar_filtros_prestamo(
    kpis_prestamos, analista, concesionario, modelo, None, None
)

resultado = kpis_prestamos.first()
```

**Mejora esperada:** De 8 queries a 2-3 queries (reducción de 60-75%)

---

### 3. **Queries con EXTRACT sin Índices** (ALTO)

#### Problema: `obtener_financiamiento_tendencia_mensual`
**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py:3417-3823`

**Código actual:**
```python
# ❌ EXTRACT sin índice funcional
query_nuevos = (
    db.query(
        func.extract("year", Prestamo.fecha_aprobacion).label("año"),
        func.extract("month", Prestamo.fecha_aprobacion).label("mes"),
        func.count(Prestamo.id).label("cantidad"),
        func.sum(Prestamo.total_financiamiento).label("monto_total"),
    )
    .group_by(func.extract("year", Prestamo.fecha_aprobacion), func.extract("month", Prestamo.fecha_aprobacion))
)
```

**Solución: Crear índices funcionales**
```sql
-- ✅ Índice funcional para GROUP BY por año/mes
CREATE INDEX IF NOT EXISTS idx_prestamos_fecha_aprobacion_ym
ON prestamos (
    EXTRACT(YEAR FROM fecha_aprobacion),
    EXTRACT(MONTH FROM fecha_aprobacion)
)
WHERE estado = 'APROBADO'
  AND fecha_aprobacion IS NOT NULL;

-- ✅ Índice compuesto para filtros adicionales
CREATE INDEX IF NOT EXISTS idx_prestamos_aprobacion_estado_analista
ON prestamos (fecha_aprobacion, estado, analista, concesionario)
WHERE estado = 'APROBADO';
```

**Mejora esperada:** Reducción de 2000-5000ms a 200-500ms (reducción de 80-90%)

---

### 4. **Queries SQL Directas sin Optimización** (MEDIO)

#### Problema: Queries SQL con texto plano
**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py:3557-3678`

**Código actual:**
```python
# ❌ SQL directo sin usar índices eficientemente
query_cuotas_sql = text("""
    SELECT
        EXTRACT(YEAR FROM c.fecha_vencimiento)::integer as año,
        EXTRACT(MONTH FROM c.fecha_vencimiento)::integer as mes,
        COALESCE(SUM(c.monto_cuota), 0) as total_cuotas_programadas
    FROM cuotas c
    INNER JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p.estado = 'APROBADO'
      AND EXTRACT(YEAR FROM c.fecha_vencimiento) >= 2024
""")
```

**Solución: Usar ORM con eager loading**
```python
# ✅ Query optimizada con ORM y eager loading
query_cuotas = (
    db.query(
        func.extract("year", Cuota.fecha_vencimiento).label("año"),
        func.extract("month", Cuota.fecha_vencimiento).label("mes"),
        func.sum(Cuota.monto_cuota).label("total_cuotas_programadas")
    )
    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    .filter(
        Prestamo.estado == "APROBADO",
        func.extract("year", Cuota.fecha_vencimiento) >= 2024
    )
    .group_by(
        func.extract("year", Cuota.fecha_vencimiento),
        func.extract("month", Cuota.fecha_vencimiento)
    )
    .order_by("año", "mes")
)

# Aplicar filtros
query_cuotas = FiltrosDashboard.aplicar_filtros_cuota(
    query_cuotas, analista, concesionario, modelo, fecha_inicio, fecha_fin
)
```

**Mejora esperada:** Mejor uso de índices y cache de query plan (reducción de 20-30%)

---

## ✅ Soluciones Propuestas

### Prioridad 1: Índices de Base de Datos (IMPACTO INMEDIATO)

#### Script de Migración de Índices
```sql
-- ============================================================================
-- ÍNDICES CRÍTICOS PARA DASHBOARD
-- ============================================================================

-- 1. Índice para GROUP BY por año/mes en préstamos
CREATE INDEX IF NOT EXISTS idx_prestamos_fecha_aprobacion_ym
ON prestamos (
    EXTRACT(YEAR FROM fecha_aprobacion),
    EXTRACT(MONTH FROM fecha_aprobacion),
    estado
)
WHERE estado = 'APROBADO'
  AND fecha_aprobacion IS NOT NULL;

-- 2. Índice para GROUP BY por año/mes en cuotas
CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_vencimiento_ym
ON cuotas (
    EXTRACT(YEAR FROM fecha_vencimiento),
    EXTRACT(MONTH FROM fecha_vencimiento)
)
WHERE fecha_vencimiento IS NOT NULL;

-- 3. Índice compuesto para JOINs eficientes
CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_fecha_vencimiento
ON cuotas (prestamo_id, fecha_vencimiento, estado, total_pagado, monto_cuota);

-- 4. Índice para filtros de fecha en pagos
CREATE INDEX IF NOT EXISTS idx_pagos_fecha_pago_activo
ON pagos (fecha_pago, activo, monto_pagado)
WHERE activo = TRUE
  AND monto_pagado > 0;

-- 5. Índice para búsquedas por cédula
CREATE INDEX IF NOT EXISTS idx_prestamos_cedula_estado
ON prestamos (cedula, estado)
WHERE estado IN ('APROBADO', 'FINALIZADO');
```

**Ejecutar:** Durante horario de bajo tráfico (puede tardar varios minutos)

---

### Prioridad 2: Optimizar N+1 Queries

#### Archivo: `backend/app/api/v1/endpoints/prestamos.py`

**Cambio requerido:** Reemplazar loop de queries por query agregada

**Impacto:** Reducción de 66% en número de queries

---

### Prioridad 3: Combinar Queries Múltiples

#### Archivo: `backend/app/api/v1/endpoints/dashboard.py`

**Cambio requerido:** Usar CASE WHEN para combinar queries de mes actual/anterior

**Impacto:** Reducción de 60-75% en número de queries

---

### Prioridad 4: Cache de Resultados

#### Mejorar estrategia de cache
```python
# ✅ Cache más agresivo para datos históricos
@cache_result(ttl=1800, key_prefix="dashboard")  # 30 minutos para datos históricos
def obtener_financiamiento_tendencia_mensual(...):
    ...

# ✅ Cache por filtros
def _get_cache_key(filtros, periodo):
    """Generar clave de cache única por combinación de filtros"""
    filtros_str = json.dumps(sorted(filtros.items()), sort_keys=True)
    return f"dashboard:{periodo}:{hashlib.md5(filtros_str.encode()).hexdigest()}"
```

---

## 📊 Métricas de Mejora Esperadas

| Endpoint | Tiempo Actual | Tiempo Esperado | Mejora |
|----------|--------------|-----------------|--------|
| `/kpis-principales` | 2000-3000ms | 500-800ms | 70-75% |
| `/financiamiento-tendencia-mensual` | 2000-5000ms | 300-600ms | 80-90% |
| `/cedula/{cedula}/resumen` | 500-1000ms | 100-200ms | 80% |
| `/admin` | 3000-5000ms | 800-1200ms | 70-75% |

---

## 🔧 Plan de Implementación

### Fase 1: Índices (1-2 horas)
1. ✅ Crear script de migración de índices
2. ✅ Ejecutar en horario de bajo tráfico
3. ✅ Verificar que los índices se usen con `EXPLAIN ANALYZE`

### Fase 2: Optimizar N+1 (2-3 horas)
1. ✅ Refactorizar `obtener_resumen_prestamos_cliente`
2. ✅ Probar con datos reales
3. ✅ Medir mejora de rendimiento

### Fase 3: Combinar Queries (3-4 horas)
1. ✅ Refactorizar `obtener_kpis_principales`
2. ✅ Refactorizar queries de mes actual/anterior
3. ✅ Validar resultados

### Fase 4: Testing y Monitoreo (1-2 horas)
1. ✅ Comparar tiempos antes/después
2. ✅ Verificar que los resultados sean idénticos
3. ✅ Monitorear en producción

---

## 📝 Notas Importantes

1. **Índices funcionales:** PostgreSQL requiere funciones IMMUTABLE. Si `EXTRACT` no funciona, usar `DATE_TRUNC`.

2. **Cache:** Los datos históricos pueden cachearse más tiempo que los datos actuales.

3. **Testing:** Siempre validar que los resultados optimizados sean idénticos a los originales.

4. **Monitoreo:** Usar `EXPLAIN ANALYZE` para verificar que los índices se usen correctamente.

---

## 🚀 Próximos Pasos

1. **Revisar y aprobar** este documento
2. **Crear migración** de índices
3. **Implementar optimizaciones** en orden de prioridad
4. **Medir mejoras** y ajustar según sea necesario

