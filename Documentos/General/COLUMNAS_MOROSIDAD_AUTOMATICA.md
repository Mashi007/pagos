# ✅ NUEVAS COLUMNAS: Morosidad Calculada Automáticamente

## Fecha de Implementación
2025-11-06

---

## 🎯 OBJETIVO

Agregar dos columnas en la tabla `cuotas` que se actualizan **automáticamente** para mejorar el rendimiento de gráficos e indicadores:

1. **`dias_morosidad`**: Días de atraso calculados automáticamente
2. **`monto_morosidad`**: Monto pendiente calculado automáticamente (`monto_cuota - total_pagado`)

---

## 📊 COLUMNAS AGREGADAS

### 1. `dias_morosidad` (INTEGER)

**Descripción:** Días de morosidad calculados automáticamente

**Lógica de Cálculo:**
- **Si está pagada y `fecha_pago > fecha_vencimiento`**: `(fecha_pago - fecha_vencimiento).days`
- **Si no está pagada y `fecha_vencimiento < CURRENT_DATE`**: `(CURRENT_DATE - fecha_vencimiento).days`
- **Si está pagada a tiempo o no vencida**: `0`

**Ejemplo:**
```
fecha_vencimiento: 2025-11-30
fecha_pago:        2025-12-15  ← 15 días después
dias_morosidad:    15
```

### 2. `monto_morosidad` (NUMERIC(12, 2))

**Descripción:** Monto pendiente calculado automáticamente

**Fórmula:**
```
monto_morosidad = MAX(0, monto_cuota - total_pagado)
```

**Ejemplo:**
```
monto_cuota:     $500.00
total_pagado:    $300.00
monto_morosidad: $200.00  ← Lo que falta por pagar
```

---

## 🔄 ACTUALIZACIÓN AUTOMÁTICA

### Cuándo se Actualiza

Las columnas se actualizan automáticamente cuando:

1. **Se registra un pago** → Función `_aplicar_monto_a_cuota()`
2. **Se actualiza el estado de una cuota** → Función `_actualizar_estado_cuota()`
3. **Se ejecuta el script de migración** → Para datos existentes

### Función Helper

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py`
**Función:** `_actualizar_morosidad_cuota(cuota, fecha_hoy)`

```python
def _actualizar_morosidad_cuota(cuota, fecha_hoy: date) -> None:
    """
    ✅ ACTUALIZA AUTOMÁTICAMENTE las columnas de morosidad:
    - dias_morosidad: Días de atraso
    - monto_morosidad: Monto pendiente (monto_cuota - total_pagado)
    """
    # 1. Calcular dias_morosidad
    if cuota.fecha_vencimiento:
        if cuota.fecha_pago:
            if cuota.fecha_pago > cuota.fecha_vencimiento:
                cuota.dias_morosidad = (cuota.fecha_pago - cuota.fecha_vencimiento).days
            else:
                cuota.dias_morosidad = 0
        else:
            if cuota.fecha_vencimiento < fecha_hoy:
                cuota.dias_morosidad = (fecha_hoy - cuota.fecha_vencimiento).days
            else:
                cuota.dias_morosidad = 0
    else:
        cuota.dias_morosidad = 0

    # 2. Calcular monto_morosidad
    monto_pendiente = cuota.monto_cuota - (cuota.total_pagado or Decimal("0.00"))
    cuota.monto_morosidad = max(Decimal("0.00"), monto_pendiente)
```

---

## 📋 MIGRACIÓN

### Script SQL

**Ubicación:** `backend/scripts/migrations/AGREGAR_COLUMNAS_MOROSIDAD_CUOTAS.sql`

**Pasos:**
1. Agregar columnas `dias_morosidad` y `monto_morosidad`
2. Crear índices para optimización
3. Calcular valores iniciales para datos existentes
4. Verificar actualización

**Ejecutar en DBeaver:**
```sql
-- Ejecutar el script completo desde:
backend/scripts/migrations/AGREGAR_COLUMNAS_MOROSIDAD_CUOTAS.sql
```

---

## 🚀 BENEFICIOS

### 1. Rendimiento Mejorado

**Antes:**
```python
# Calcular en tiempo real en cada query
dias_atraso = (hoy - cuota.fecha_vencimiento).days
monto_pendiente = cuota.monto_cuota - cuota.total_pagado
```

**Después:**
```python
# Usar valores pre-calculados (más rápido)
dias_atraso = cuota.dias_morosidad
monto_pendiente = cuota.monto_morosidad
```

### 2. Índices Optimizados

```sql
-- Índice para queries de morosidad por días
CREATE INDEX idx_cuotas_dias_morosidad
ON cuotas(dias_morosidad)
WHERE dias_morosidad > 0;

-- Índice para queries de morosidad por monto
CREATE INDEX idx_cuotas_monto_morosidad
ON cuotas(monto_morosidad)
WHERE monto_morosidad > 0;
```

### 3. Queries Más Simples

**Antes:**
```sql
SELECT
    (CURRENT_DATE - c.fecha_vencimiento)::INTEGER as dias_atraso,
    (c.monto_cuota - COALESCE(c.total_pagado, 0)) as monto_pendiente
FROM cuotas c
WHERE c.fecha_vencimiento < CURRENT_DATE
  AND c.estado != 'PAGADO';
```

**Después:**
```sql
SELECT
    c.dias_morosidad,
    c.monto_morosidad
FROM cuotas c
WHERE c.dias_morosidad > 0
  AND c.monto_morosidad > 0;
```

---

## 📈 ENDPOINTS ACTUALIZADOS

### 1. `/composicion-morosidad`

**Antes:**
```python
# Calcular días de atraso en tiempo real
dias_atraso = (hoy - cuota.fecha_vencimiento).days
monto = cuota.monto_cuota
```

**Después:**
```python
# ✅ Usar columnas calculadas automáticamente
dias_atraso = cuota.dias_morosidad or 0
monto = cuota.monto_morosidad
```

**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py` (línea ~2930)

---

## 🔍 VERIFICACIÓN

### Consulta SQL para Verificar

```sql
-- Verificar cuotas con morosidad
SELECT
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN dias_morosidad > 0 THEN 1 END) as cuotas_con_dias_morosidad,
    COUNT(CASE WHEN monto_morosidad > 0 THEN 1 END) as cuotas_con_monto_morosidad,
    SUM(dias_morosidad) as total_dias_morosidad,
    SUM(monto_morosidad) as total_monto_morosidad
FROM cuotas;

-- Verificar consistencia
SELECT
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN ABS(monto_morosidad - (monto_cuota - COALESCE(total_pagado, 0))) > 0.01 THEN 1 END) as inconsistencias
FROM cuotas;
```

---

## ⚠️ CONSIDERACIONES

### 1. Actualización Periódica

Para cuotas que no reciben pagos, `dias_morosidad` debe actualizarse periódicamente (diariamente) porque depende de `CURRENT_DATE`.

**Solución:** Crear un script de actualización periódica (cron job) que ejecute:

```sql
UPDATE cuotas
SET dias_morosidad = (CURRENT_DATE - fecha_vencimiento)::INTEGER
WHERE fecha_pago IS NULL
  AND fecha_vencimiento < CURRENT_DATE
  AND estado != 'PAGADO';
```

### 2. Sincronización

Las columnas se actualizan automáticamente cuando:
- Se registra un pago
- Se actualiza el estado de una cuota

**No se actualizan automáticamente cuando:**
- Pasa el tiempo (para cuotas no pagadas)
- Se modifica directamente en la base de datos

**Recomendación:** Ejecutar script de actualización periódica diariamente.

---

## ✅ RESUMEN

### Cambios Implementados

1. ✅ **Modelo SQLAlchemy** actualizado (`backend/app/models/amortizacion.py`)
2. ✅ **Función helper** creada (`_actualizar_morosidad_cuota()`)
3. ✅ **Lógica de actualización** integrada en `_aplicar_monto_a_cuota()` y `_actualizar_estado_cuota()`
4. ✅ **Script de migración** creado (`AGREGAR_COLUMNAS_MOROSIDAD_CUOTAS.sql`)
5. ✅ **Endpoint del dashboard** actualizado (`/composicion-morosidad`)
6. ✅ **Índices** creados para optimización

### Próximos Pasos

1. **Ejecutar migración SQL** en DBeaver
2. **Verificar** que las columnas se actualicen correctamente
3. **Actualizar otros endpoints** del dashboard que calculen morosidad
4. **Crear script de actualización periódica** (opcional, para cuotas no pagadas)

---

**Estado:** ✅ **IMPLEMENTADO - PENDIENTE MIGRACIÓN SQL**

