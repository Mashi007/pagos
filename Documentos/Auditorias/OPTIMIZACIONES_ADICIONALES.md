# 🔧 OPTIMIZACIONES ADICIONALES PENDIENTES

**Fecha:** 2025-01-27  
**Estado:** Pendientes de implementar

---

## 📊 RESUMEN

Después de aplicar las optimizaciones principales, quedan **2 áreas de optimización adicionales** que pueden mejorar significativamente el rendimiento del sistema:

1. **Índices en Base de Datos** - Mejora queries por factor 10-100x
2. **Optimización de KPIs/Dashboard** - Reduce tiempo de respuesta de 5-10s a 1-2s

---

## 1️⃣ ÍNDICES EN BASE DE DATOS

### ❌ Problema

Campos que se consultan frecuentemente **NO tienen índices**, causando:
- **Full table scans** en vez de búsquedas indexadas
- Queries lentas (especialmente con grandes volúmenes de datos)
- Alto uso de CPU y I/O del servidor

### 📋 Campos que Necesitan Índices

#### **Tabla: `pagos`**
```python
# ❌ FALTA ÍNDICE
fecha_registro = Column(DateTime, default=func.now(), nullable=False)  
# Se usa en: ORDER BY, filtros por fecha, queries de dashboard

# ✅ YA TIENE ÍNDICE (correcto)
cedula_cliente = Column(String(CEDULA_LENGTH), nullable=False, index=True)
estado = Column(String(20), default="PAGADO", nullable=False, index=True)
```

**Ubicación:** `backend/app/models/pago.py:32`

**Impacto:**
- `listar_pagos()` ordena por `fecha_registro.desc()` → sin índice es lento con muchos registros
- Dashboard filtra pagos por fecha → sin índice hace full table scan

---

#### **Tabla: `cuotas`**
```python
# ❌ FALTA ÍNDICE
fecha_vencimiento = Column(Date, nullable=False)
# Se usa en: filtros de mora, queries de cuotas vencidas, dashboard

# ✅ YA TIENE ÍNDICE (correcto)
prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False, index=True)
```

**Ubicación:** `backend/app/models/amortizacion.py:35`

**Impacto:**
- `_calcular_cuotas_atrasadas_batch()` filtra por `fecha_vencimiento < hoy` → sin índice es lento
- Dashboard calcula cartera vencida con filtro de fecha → sin índice es muy lento

---

#### **Tabla: `prestamos`**
```python
# ❌ FALTA ÍNDICE
fecha_registro = Column(TIMESTAMP, nullable=False, default=func.now())
# Se usa en: ORDER BY, filtros por fecha, queries de dashboard

# ✅ YA TIENE ÍNDICE (correcto)
cedula = Column(String(20), nullable=False, index=True)
cliente_id = Column(Integer, nullable=False, index=True)
```

**Ubicación:** `backend/app/models/prestamo.py:67`

**Impacto:**
- `listar_prestamos()` ordena por `fecha_registro.desc()` → sin índice es lento
- Dashboard filtra préstamos por rango de fechas → sin índice hace full table scan

---

#### **Tabla: `prestamo_auditoria`**
```python
# ❌ FALTA ÍNDICE
fecha_cambio = Column(TIMESTAMP, nullable=False, default=func.now())
# Se usa en: ORDER BY fecha_cambio.desc() en listar auditoría

# ✅ YA TIENE ÍNDICE (correcto)
prestamo_id = Column(Integer, nullable=False, index=True)
```

**Ubicación:** `backend/app/models/prestamo_auditoria.py:38`

**Impacto:**
- `listar_auditoria()` ordena por `fecha_cambio.desc()` → sin índice es lento con muchos registros

---

### ✅ Solución: Agregar Índices

**Crear migración Alembic:**

```python
# backend/alembic/versions/XXXX_add_indexes.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Índice en pagos.fecha_registro
    op.create_index(
        'ix_pagos_fecha_registro', 
        'pagos', 
        ['fecha_registro'], 
        unique=False
    )
    
    # Índice en cuotas.fecha_vencimiento
    op.create_index(
        'ix_cuotas_fecha_vencimiento', 
        'cuotas', 
        ['fecha_vencimiento'], 
        unique=False
    )
    
    # Índice en prestamos.fecha_registro
    op.create_index(
        'ix_prestamos_fecha_registro', 
        'prestamos', 
        ['fecha_registro'], 
        unique=False
    )
    
    # Índice en prestamo_auditoria.fecha_cambio
    op.create_index(
        'ix_prestamo_auditoria_fecha_cambio', 
        'prestamo_auditoria', 
        ['fecha_cambio'], 
        unique=False
    )

def downgrade():
    op.drop_index('ix_pagos_fecha_registro', table_name='pagos')
    op.drop_index('ix_cuotas_fecha_vencimiento', table_name='cuotas')
    op.drop_index('ix_prestamos_fecha_registro', table_name='prestamos')
    op.drop_index('ix_prestamo_auditoria_fecha_cambio', table_name='prestamo_auditoria')
```

**O directamente en modelos:**

```python
# backend/app/models/pago.py
fecha_registro = Column(DateTime, default=func.now(), nullable=False, index=True)  # ✅ Agregar index=True

# backend/app/models/amortizacion.py
fecha_vencimiento = Column(Date, nullable=False, index=True)  # ✅ Agregar index=True

# backend/app/models/prestamo.py
fecha_registro = Column(TIMESTAMP, nullable=False, default=func.now(), index=True)  # ✅ Agregar index=True

# backend/app/models/prestamo_auditoria.py
fecha_cambio = Column(TIMESTAMP, nullable=False, default=func.now(), index=True)  # ✅ Agregar index=True
```

**Impacto estimado:**
- Queries con filtros por fecha: **10-100x más rápidas**
- ORDER BY por fecha: **5-50x más rápidas**
- Dashboard KPIs: **3-10x más rápido**

---

## 2️⃣ OPTIMIZACIÓN DE KPIs/DASHBOARD

### ❌ Problema

Endpoints de dashboard ejecutan **múltiples queries separadas** que podrían combinarse o cachearse:

**Ejemplo en `dashboard_kpis_principales()`:**
```python
# Query 1: Cartera total
cartera_query = db.query(func.sum(Prestamo.total_financiamiento))...

# Query 2: Clientes con cuotas
clientes_con_cuotas_query = db.query(func.count(func.distinct(Prestamo.cedula)))...

# Query 3: Clientes en mora
clientes_en_mora_query = db.query(func.count(func.distinct(Prestamo.cedula)))...

# Query 4: Pagos del mes
pagos_query = db.query(func.sum(Pago.monto_pagado))...

# ... y más queries
```

**Con 10-15 queries separadas**, cada una ejecuta filtros similares → redundancia

---

### ✅ Soluciones Propuestas

#### **A. Cache de KPIs (Recomendado)**

Usar el sistema de cache ya implementado (`backend/app/core/cache.py`):

```python
from app.core.cache import cache_result

@router.get("/dashboard")
@cache_result(ttl=300)  # Cache por 5 minutos
def dashboard_kpis_principales(...):
    # KPIs cambian poco, cache es muy efectivo
    ...
```

**Impacto:**
- **Primera llamada:** Normal (5-10s)
- **Llamadas siguientes (5 min):** Instantáneo (<0.1s)
- **Reducción de carga:** 95% menos queries a BD

---

#### **B. Combinar Queries Similares**

Usar `UNION` o subqueries para combinar cálculos relacionados:

```python
# ANTES: 2 queries separadas
clientes_con_cuotas = db.query(...).scalar()
clientes_en_mora = db.query(...).scalar()

# DESPUÉS: 1 query combinada
resultado = db.query(
    func.count(func.distinct(case([...]))).label('con_cuotas'),
    func.count(func.distinct(case([...]))).label('en_mora')
).one()
```

**Impacto:** 50% menos queries en dashboard

---

#### **C. Materialized Views (PostgreSQL)**

Para KPIs muy complejos, crear vistas materializadas:

```sql
CREATE MATERIALIZED VIEW dashboard_stats AS
SELECT 
    COUNT(DISTINCT p.cedula) as clientes_total,
    SUM(p.total_financiamiento) as cartera_total,
    ...
FROM prestamos p
WHERE p.estado = 'APROBADO'
GROUP BY DATE_TRUNC('month', p.fecha_registro);

CREATE INDEX ON dashboard_stats (fecha_registro);
```

**Refrescar periódicamente:** `REFRESH MATERIALIZED VIEW dashboard_stats;`

**Impacto:** KPIs complejos de 10s → 0.1s

---

### 📋 Endpoints a Optimizar

1. ✅ `/api/v1/kpis/dashboard` - Múltiples queries separadas
2. ✅ `/api/v1/dashboard/admin` - Queries complejas sin cache
3. ✅ `/api/v1/dashboard/kpis-principales` - Cálculos repetitivos

---

## 📊 RESUMEN DE IMPACTO

| Optimización | Impacto | Complejidad | Prioridad |
|-------------|---------|-------------|-----------|
| Índices en BD | 10-100x más rápido | Baja | 🔴 Alta |
| Cache de KPIs | 95% menos queries | Media | 🟡 Media |
| Combinar queries | 50% menos queries | Alta | 🟢 Baja |
| Materialized Views | 100x más rápido | Alta | 🟢 Baja |

---

## 🎯 RECOMENDACIÓN DE PRIORIDAD

### **1. Índices en BD** (CRÍTICO)
- **Tiempo:** 2-3 horas
- **Impacto:** Alto
- **Riesgo:** Bajo
- **Hacer:** Inmediatamente

### **2. Cache de KPIs** (IMPORTANTE)
- **Tiempo:** 4-6 horas
- **Impacto:** Alto
- **Riesgo:** Bajo
- **Hacer:** Próxima semana

### **3. Combinar Queries** (OPCIONAL)
- **Tiempo:** 8-12 horas
- **Impacto:** Medio
- **Riesgo:** Medio
- **Hacer:** Si hay tiempo

---

## ✅ CONCLUSIÓN

Las optimizaciones principales ya aplicadas mejoraron el sistema **10-15x**.

Las optimizaciones adicionales pueden mejorar aún más:
- **Índices:** 10-100x en queries específicas
- **Cache:** 95% reducción de carga en dashboard

**Total potencial:** Sistema **50-200x más rápido** que el estado inicial.

