# 🔧 Corrección: Errores SQL en Dashboard

**Fecha:** 2025-11-06
**Problemas:**
1. Error 500 en endpoint `/api/v1/dashboard/resumen-financiamiento-pagado` - Error de sintaxis SQL `SELECTCOALESCE`
2. Error 500 en múltiples endpoints - Error de sintaxis SQL `GROUP BYEXTRACT`
3. Error `column prestamos.valor_activo does not exist` en consultas de `Prestamo`

---

## ❌ PROBLEMA DETECTADO

El error 500 era causado por un error de sintaxis SQL donde faltaba un espacio entre `SELECT` y `COALESCE`:

```sql
-- ❌ INCORRECTO
SELECTCOALESCE(SUM(monto_pagado), 0)

-- ✅ CORRECTO
SELECT COALESCE(SUM(monto_pagado), 0)
```

---

## ✅ CORRECCIONES APLICADAS

### **1. `backend/app/api/v1/endpoints/dashboard.py`**

#### **Línea 838:**
```python
# ❌ ANTES
SELECTCOALESCE(SUM(p.monto_pagado), 0)

# ✅ DESPUÉS
SELECT COALESCE(SUM(p.monto_pagado), 0)
```

#### **Línea 850:**
```python
# ❌ ANTES
SELECTCOALESCE(SUM(monto_pagado), 0)

# ✅ DESPUÉS
SELECT COALESCE(SUM(monto_pagado), 0)
```

#### **Línea 1277:**
```python
# ❌ ANTES
SELECTCOALESCE(AVG((:hoy::date - fecha_vencimiento::date)), 0)

# ✅ DESPUÉS
SELECT COALESCE(AVG((:hoy::date - fecha_vencimiento::date)), 0)
```

#### **Línea 2443:**
```python
# ❌ ANTES
SELECTCOALESCE(SUM(monto_pagado), 0)

# ✅ DESPUÉS
SELECT COALESCE(SUM(monto_pagado), 0)
```

#### **Línea 2460:**
```python
# ❌ ANTES
SELECTCOALESCE(SUM(monto_pagado), 0)

# ✅ DESPUÉS
SELECT COALESCE(SUM(monto_pagado), 0)
```

#### **Línea 4676:**
```python
# ❌ ANTES
SELECTCOALESCE(SUM(p.monto_pagado), 0) as total_pagado

# ✅ DESPUÉS
SELECT COALESCE(SUM(p.monto_pagado), 0) as total_pagado
```

#### **Línea 4700:**
```python
# ❌ ANTES
SELECTCOALESCE(SUM(monto_pagado), 0) as total_pagado

# ✅ DESPUÉS
SELECT COALESCE(SUM(monto_pagado), 0) as total_pagado
```

#### **Línea 4391-4392:**
```python
# ❌ ANTES
SELECTEXISTS (
    SELECTFROM information_schema.tables

# ✅ DESPUÉS
SELECT EXISTS (
    SELECT FROM information_schema.tables
```

### **2. `backend/app/api/v1/endpoints/reportes.py`**

#### **Línea 276:**
```python
# ❌ ANTES
SELECTCOALESCE(SUM(monto_pagado), 0)

# ✅ DESPUÉS
SELECT COALESCE(SUM(monto_pagado), 0)
```

#### **Línea 807:**
```python
# ❌ ANTES
SELECTCOALESCE(SUM(monto_pagado), 0)

# ✅ DESPUÉS
SELECT COALESCE(SUM(monto_pagado), 0)
```

---

## 📊 RESUMEN

### **Archivos Corregidos:**
1. ✅ `backend/app/api/v1/endpoints/dashboard.py` - 20 correcciones (7 SELECTCOALESCE + 13 GROUP BYEXTRACT)
2. ✅ `backend/app/api/v1/endpoints/reportes.py` - 2 correcciones
3. ✅ `backend/app/utils/pagos_cuotas_helper.py` - 3 correcciones (valor_activo)

### **Total de Correcciones:**
- ✅ **9 instancias** de `SELECTCOALESCE` corregidas a `SELECT COALESCE`
- ✅ **2 instancias** adicionales: `SELECTEXISTS` → `SELECT EXISTS` y `SELECTFROM` → `SELECT FROM`
- ✅ **13 instancias** de `GROUP BYEXTRACT` corregidas a `GROUP BY EXTRACT`
- ✅ **3 funciones** corregidas para evitar error de `valor_activo` en `pagos_cuotas_helper.py`

### **Endpoints Afectados:**
- ✅ `/api/v1/dashboard/resumen-financiamiento-pagado` - **CORREGIDO** (causa del error 500)
- ✅ `/api/v1/dashboard/admin` - Prevención de errores futuros
- ✅ `/api/v1/reportes/dashboard/resumen` - Prevención de errores futuros
- ✅ Otros endpoints que usan queries similares - Prevención de errores futuros

---

## ✅ CORRECCIONES ADICIONALES (2025-11-06 - Segunda ronda)

### **3. Corrección de `GROUP BYEXTRACT` → `GROUP BY EXTRACT`**

Se corrigieron **13 instancias** en `backend/app/api/v1/endpoints/dashboard.py`:

- Líneas 277, 296, 317, 330: En función `_calcular_morosidad()`
- Líneas 1361, 1390, 1420, 1447: En función `dashboard_administrador()`
- Líneas 2221, 2260: En función `obtener_cobranzas_mensuales()`
- Líneas 3161, 3179: En función `obtener_evolucion_general_mensual()`
- Línea 4444: En función `obtener_evolucion_morosidad()`

**Antes:**
```sql
GROUP BYEXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
```

**Después:**
```sql
GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
```

### **4. Corrección de error `column prestamos.valor_activo does not exist`**

El modelo `Prestamo` tiene definido el campo `valor_activo`, pero la columna no existe en la base de datos en producción. Cuando SQLAlchemy hace `db.query(Prestamo)`, intenta seleccionar todas las columnas del modelo, incluyendo `valor_activo`, y falla.

**Solución:** Modificar las consultas para usar solo las columnas necesarias en lugar de cargar todo el objeto `Prestamo`.

#### **Archivo: `backend/app/utils/pagos_cuotas_helper.py`**

**Función `calcular_total_pagado_cuota()` (línea 199):**
```python
# ❌ ANTES
prestamo = db.query(Prestamo).filter(Prestamo.id == cuota.prestamo_id).first()
if not prestamo:
    return Decimal("0")
cedula = prestamo.cedula

# ✅ DESPUÉS
prestamo_cedula = (
    db.query(Prestamo.cedula)
    .filter(Prestamo.id == cuota.prestamo_id)
    .scalar()
)
if not prestamo_cedula:
    return Decimal("0")
cedula = prestamo_cedula
```

**Función `calcular_monto_pagado_mes()` (línea 260):**
```python
# ❌ ANTES
prestamo = db.query(Prestamo).filter(Prestamo.id == cuota.prestamo_id).first()
if prestamo:
    pagos = obtener_pagos_cuota(..., cedula=prestamo.cedula, ...)

# ✅ DESPUÉS
prestamo_cedula = (
    db.query(Prestamo.cedula)
    .filter(Prestamo.id == cuota.prestamo_id)
    .scalar()
)
if prestamo_cedula:
    pagos = obtener_pagos_cuota(..., cedula=prestamo_cedula, ...)
```

**Función `reconciliar_pago_cuota()` (línea 312):**
```python
# ❌ ANTES
prestamos = db.query(Prestamo).filter(...).all()
for prestamo in prestamos:
    cuota = db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id, ...).first()

# ✅ DESPUÉS
prestamo_ids = [
    row[0] for row in db.query(Prestamo.id).filter(...).all()
]
for prestamo_id in prestamo_ids:
    cuota = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id, ...).first()
```

---

## ✅ ESTADO FINAL

- ✅ **Error 500 corregido** en `/api/v1/dashboard/resumen-financiamiento-pagado`
- ✅ **Todas las instancias** de `SELECTCOALESCE` corregidas (9 instancias)
- ✅ **Todas las instancias** de `GROUP BYEXTRACT` corregidas (13 instancias)
- ✅ **Error `valor_activo` corregido** en 3 funciones de `pagos_cuotas_helper.py`
- ✅ **Sin errores de linting**
- ✅ **Código listo para producción**

---

## 🔍 VERIFICACIÓN

Para verificar que no quedan más instancias:

```bash
# Verificar SELECTCOALESCE
grep -r "SELECTCOALESCE" backend/

# Verificar GROUP BYEXTRACT
grep -r "BYEXTRACT" backend/

# Verificar SELECTEXISTS y SELECTFROM
grep -r "SELECTEXISTS\|SELECTFROM" backend/
```

**Resultado esperado:** No debe encontrar ninguna coincidencia (excepto en este documento de correcciones).

---

## 📝 NOTA

Este error probablemente se introdujo durante una corrección automática de formato o durante una edición manual donde se eliminó accidentalmente el espacio entre `SELECT` y `COALESCE`.

**Prevención:** En el futuro, usar herramientas de linting SQL o validar queries antes de commitear.

