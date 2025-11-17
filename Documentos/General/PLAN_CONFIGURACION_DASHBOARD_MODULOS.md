# 🎯 PLAN DE CONFIGURACIÓN: Dashboard y Todos los Módulos

## Fecha
Basado en estructura confirmada en `ESTRUCTURA_TABLAS_CONFIRMADA.md`

---

## ✅ ESTADO ACTUAL

### Backend - Dashboard (`dashboard.py`)

**✅ YA IMPLEMENTADO:**
- ✅ Filtro `Prestamo.estado == "APROBADO"` en la mayoría de queries
- ✅ Filtro `Pago.activo = True` en queries de pagos
- ✅ Normalización de fechas (`normalize_to_date`) para comparaciones TIMESTAMP vs DATE
- ✅ Uso correcto de `prestamos.fecha_aprobacion` para filtros
- ✅ Uso correcto de `cuotas.fecha_vencimiento` para morosidad
- ✅ Uso correcto de `pagos.fecha_pago` para cálculos

**❌ FALTA IMPLEMENTAR:**
- ❌ Filtro `cliente.estado != 'INACTIVO'` en TODAS las queries
- ❌ JOIN con tabla `clientes` en queries que no lo tienen
- ❌ Validación de `cliente.activo = true` (sincronizado con `estado`)

---

## 🔧 CONFIGURACIÓN REQUERIDA

### 1. DASHBOARD PRINCIPAL (`dashboard.py`)

#### 1.1. Función: `dashboard_administrador`

**Ubicación:** Línea ~954

**Cambios Requeridos:**

```python
# ANTES:
base_prestamo_query = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")

# DESPUÉS:
base_prestamo_query = (
    db.query(Prestamo)
    .join(Cliente, Prestamo.cliente_id == Cliente.id)
    .filter(
        Prestamo.estado == "APROBADO",
        Cliente.estado != "INACTIVO",
        Cliente.activo == True
    )
)
```

**Queries a Actualizar:**
- ✅ `cartera_total` (línea ~997)
- ✅ `cartera_vencida_query` (línea ~1001) - Agregar JOIN con Cliente
- ✅ `total_cobrado_mes` (línea ~118)
- ✅ `_calcular_pagos_fecha` (línea ~574)
- ✅ Todas las queries que usan `base_prestamo_query`

---

#### 1.2. Función: `obtener_financiamiento_tendencia_mensual`

**Ubicación:** Línea ~3533

**Cambios Requeridos:**

```python
# En queries SQL con text(), agregar:
INNER JOIN clientes cl ON cl.id = p.cliente_id AND cl.estado != 'INACTIVO' AND cl.activo = true
```

**Queries a Actualizar:**
- ✅ Query de préstamos nuevos (línea ~3600+)
- ✅ Query de cuotas programadas (línea ~3700+)
- ✅ Query de pagos (línea ~3800+)

---

#### 1.3. Función: `obtener_cobranzas_mensuales`

**Ubicación:** Línea ~2141

**Cambios Requeridos:**

```python
# En query SQL (línea ~2212), agregar:
INNER JOIN clientes cl ON cl.id = p.cliente_id AND cl.estado != 'INACTIVO' AND cl.activo = true
```

---

#### 1.4. Función: `obtener_cobranzas_semanales`

**Ubicación:** Línea ~4073

**Cambios Requeridos:**

```python
# En query SQL (línea ~4141), agregar:
INNER JOIN clientes cl ON cl.id = p.cliente_id AND cl.estado != 'INACTIVO' AND cl.activo = true
```

---

#### 1.5. Función: `obtener_evolucion_pagos`

**Ubicación:** Línea ~4490

**Cambios Requeridos:**

```python
# En query SQL (línea ~4530), agregar JOIN con préstamos y clientes:
SELECT
    EXTRACT(YEAR FROM p.fecha_pago)::integer as año,
    EXTRACT(MONTH FROM p.fecha_pago)::integer as mes,
    COUNT(*) as cantidad,
    COALESCE(SUM(p.monto_pagado), 0) as monto_total
FROM pagos p
INNER JOIN prestamos pr ON (
    (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
    OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
)
INNER JOIN clientes cl ON cl.id = pr.cliente_id AND cl.estado != 'INACTIVO' AND cl.activo = true
WHERE p.fecha_pago >= :fecha_inicio
  AND p.fecha_pago <= :fecha_fin
  AND p.monto_pagado IS NOT NULL
  AND p.monto_pagado > 0
  AND p.activo = TRUE
GROUP BY
    EXTRACT(YEAR FROM p.fecha_pago),
    EXTRACT(MONTH FROM p.fecha_pago)
ORDER BY año, mes
```

---

#### 1.6. Función: `obtener_kpis_principales`

**Ubicación:** Línea ~1825

**Cambios Requeridos:**

```python
# Agregar JOIN con Cliente en todas las queries:
# - clientes_activos_actual (línea ~1940+)
# - clientes_finalizados_actual (línea ~1950+)
# - clientes_inactivos_actual (línea ~1955+)
# - Todas las queries de comparación con mes anterior
```

---

#### 1.7. Función: `dashboard_analista`

**Ubicación:** Línea ~1652

**Cambios Requeridos:**

```python
# Ya tiene filtro Cliente.activo (línea ~1673), pero agregar:
.filter(
    Cliente.activo == True,
    Cliente.estado != "INACTIVO",  # ← AGREGAR
    Prestamo.estado == "APROBADO",
    Prestamo.usuario_proponente == current_user.email,
)
```

---

### 2. MÓDULO DE PAGOS (`pagos.py`)

**Archivo:** `backend/app/api/v1/endpoints/pagos.py`

**Cambios Requeridos:**

```python
# En todas las queries de pagos, agregar:
INNER JOIN prestamos pr ON (
    (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
    OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
)
INNER JOIN clientes cl ON cl.id = pr.cliente_id AND cl.estado != 'INACTIVO' AND cl.activo = true
WHERE p.activo = TRUE
```

**Endpoints a Actualizar:**
- ✅ `obtener_pagos` (listar pagos)
- ✅ `obtener_kpis_pagos` (KPIs de pagos)
- ✅ `obtener_pagos_por_fecha` (pagos por fecha)
- ✅ Cualquier query que use tabla `pagos`

---

### 3. MÓDULO DE COBRANZAS (`cobranzas.py`)

**Archivo:** `backend/app/api/v1/endpoints/cobranzas.py` (si existe)

**Cambios Requeridos:**

```python
# En queries de cuotas vencidas, agregar:
INNER JOIN prestamos p ON c.prestamo_id = p.id
INNER JOIN clientes cl ON cl.id = p.cliente_id AND cl.estado != 'INACTIVO' AND cl.activo = true
WHERE p.estado = 'APROBADO'
```

---

### 4. MÓDULO DE PRÉSTAMOS (`prestamos.py`)

**Archivo:** `backend/app/api/v1/endpoints/prestamos.py`

**Estado:** ✅ **YA CONFIGURADO CORRECTAMENTE**

**Confirmado:**
- ✅ `obtener_datos_cliente` filtra `Cliente.estado == "ACTIVO"`
- ✅ `crear_prestamo` valida que cliente esté ACTIVO
- ✅ Asignación correcta de `cliente_id`

**No requiere cambios adicionales.**

---

### 5. MÓDULO DE REPORTES

**Archivos:** Cualquier archivo que genere reportes

**Cambios Requeridos:**

```python
# En todas las queries, agregar:
INNER JOIN clientes cl ON cl.id = p.cliente_id AND cl.estado != 'INACTIVO' AND cl.activo = true
```

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### Backend - Dashboard

- [ ] **1.1** Actualizar `dashboard_administrador` - Agregar JOIN con Cliente
- [ ] **1.2** Actualizar `obtener_financiamiento_tendencia_mensual` - Agregar filtro cliente
- [ ] **1.3** Actualizar `obtener_cobranzas_mensuales` - Agregar filtro cliente
- [ ] **1.4** Actualizar `obtener_cobranzas_semanales` - Agregar filtro cliente
- [ ] **1.5** Actualizar `obtener_evolucion_pagos` - Agregar JOIN con préstamos y clientes
- [ ] **1.6** Actualizar `obtener_kpis_principales` - Agregar filtro cliente
- [ ] **1.7** Actualizar `dashboard_analista` - Agregar filtro `estado != 'INACTIVO'`
- [ ] **1.8** Actualizar `_calcular_total_cobrado_mes` - Agregar filtro cliente
- [ ] **1.9** Actualizar `_calcular_pagos_fecha` - Agregar filtro cliente
- [ ] **1.10** Revisar todas las queries SQL con `text()` - Agregar JOIN con clientes

### Backend - Módulos

- [ ] **2.1** Actualizar `pagos.py` - Agregar filtro cliente en todas las queries
- [ ] **2.2** Actualizar `cobranzas.py` (si existe) - Agregar filtro cliente
- [ ] **2.3** Revisar otros módulos que usen préstamos/cuotas/pagos

### Frontend

- [ ] **3.1** Validar que solo se muestran clientes ACTIVOS en búsqueda (✅ YA IMPLEMENTADO)
- [ ] **3.2** Validar que solo se pueden crear préstamos para clientes ACTIVOS (✅ YA IMPLEMENTADO)
- [ ] **3.3** Revisar componentes de dashboard - Validar que muestran datos correctos

---

## 🔍 PATRÓN DE BÚSQUEDA

### Para encontrar queries que necesitan actualización:

```bash
# Buscar queries SQL con text() que no incluyen JOIN con clientes
grep -r "text(" backend/app/api/v1/endpoints/ | grep -v "clientes"

# Buscar queries que usan Prestamo sin JOIN con Cliente
grep -r "Prestamo.estado == \"APROBADO\"" backend/app/api/v1/endpoints/ | grep -v "join(Cliente"

# Buscar queries que usan Cuota sin JOIN con Cliente
grep -r "Cuota" backend/app/api/v1/endpoints/ | grep -v "join(Cliente"
```

---

## 📝 PLANTILLA DE CÓDIGO

### Para Queries SQLAlchemy ORM:

```python
# ANTES:
query = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")

# DESPUÉS:
query = (
    db.query(Prestamo)
    .join(Cliente, Prestamo.cliente_id == Cliente.id)
    .filter(
        Prestamo.estado == "APROBADO",
        Cliente.estado != "INACTIVO",
        Cliente.activo == True
    )
)
```

### Para Queries SQL con text():

```python
# ANTES:
query_sql = text("""
    SELECT ...
    FROM prestamos p
    WHERE p.estado = 'APROBADO'
""")

# DESPUÉS:
query_sql = text("""
    SELECT ...
    FROM prestamos p
    INNER JOIN clientes cl ON cl.id = p.cliente_id
        AND cl.estado != 'INACTIVO'
        AND cl.activo = true
    WHERE p.estado = 'APROBADO'
""")
```

### Para Queries de Cuotas:

```python
# ANTES:
query = (
    db.query(Cuota)
    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    .filter(Prestamo.estado == "APROBADO")
)

# DESPUÉS:
query = (
    db.query(Cuota)
    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    .join(Cliente, Prestamo.cliente_id == Cliente.id)
    .filter(
        Prestamo.estado == "APROBADO",
        Cliente.estado != "INACTIVO",
        Cliente.activo == True
    )
)
```

### Para Queries de Pagos:

```python
# ANTES:
query_sql = text("""
    SELECT ...
    FROM pagos p
    WHERE p.activo = TRUE
""")

# DESPUÉS:
query_sql = text("""
    SELECT ...
    FROM pagos p
    INNER JOIN prestamos pr ON (
        (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
        OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
    )
    INNER JOIN clientes cl ON cl.id = pr.cliente_id
        AND cl.estado != 'INACTIVO'
        AND cl.activo = true
    WHERE p.activo = TRUE
""")
```

---

## ⚠️ VALIDACIONES CRÍTICAS

### 1. No Duplicar JOINs

Si una query ya tiene JOIN con `Cliente`, solo agregar el filtro:

```python
.filter(
    Cliente.estado != "INACTIVO",
    Cliente.activo == True
)
```

### 2. Validar Relaciones

- ✅ `Prestamo.cliente_id` → `Cliente.id` (Foreign Key confirmada)
- ✅ `Cuota.prestamo_id` → `Prestamo.id` (Foreign Key confirmada)
- ✅ `Pago.prestamo_id` → `Prestamo.id` (Foreign Key confirmada, nullable)

### 3. Pagos sin Prestamo

Si un pago no tiene `prestamo_id`, usar JOIN por `cedula`:

```python
INNER JOIN prestamos pr ON (
    (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
    OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
)
```

---

## 🧪 PRUEBAS RECOMENDADAS

### 1. Verificar KPIs

Después de implementar, verificar que:
- ✅ Total de préstamos excluye clientes INACTIVOS
- ✅ Total de cartera excluye clientes INACTIVOS
- ✅ Total de pagos excluye clientes INACTIVOS

### 2. Verificar Filtros

- ✅ Filtro por analista funciona correctamente
- ✅ Filtro por concesionario funciona correctamente
- ✅ Filtro por modelo funciona correctamente
- ✅ Filtro por fecha funciona correctamente

### 3. Verificar Rendimiento

- ✅ Queries no son más lentas (índices en `cliente_id` y `estado`)
- ✅ Cache funciona correctamente

---

## 📊 IMPACTO ESPERADO

### Datos que se Excluirán

- ❌ Préstamos de clientes con `estado = 'INACTIVO'`
- ❌ Cuotas de préstamos de clientes INACTIVOS
- ❌ Pagos de préstamos de clientes INACTIVOS

### Datos que se Mantendrán

- ✅ Préstamos de clientes con `estado = 'ACTIVO'`
- ✅ Préstamos de clientes con `estado = 'FINALIZADO'` (si aplica)
- ✅ Todos los préstamos APROBADOS de clientes ACTIVOS

---

## ✅ CRITERIOS DE ÉXITO

1. ✅ Todas las queries del dashboard incluyen filtro `cliente.estado != 'INACTIVO'`
2. ✅ Todas las queries del dashboard incluyen JOIN con tabla `clientes`
3. ✅ KPIs muestran solo datos de clientes ACTIVOS
4. ✅ Gráficos muestran solo datos de clientes ACTIVOS
5. ✅ No hay errores de SQL (JOINs correctos)
6. ✅ Rendimiento no se degrada significativamente

---

**Estado:** 📋 **PLAN LISTO PARA IMPLEMENTACIÓN**

**Próximo Paso:** Implementar cambios según checklist

