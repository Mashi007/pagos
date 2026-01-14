# 📊 COLUMNAS DE `cuotas` ACTUALIZADAS POR PAGOS CONCILIADOS

**Última actualización:** 2025-01-XX  
**Función:** `aplicar_pago_a_cuotas()` → `_aplicar_monto_a_cuota()`

---

## ✅ COLUMNA PRINCIPAL: `total_pagado`

### **📍 Ubicación en código:**
- **Archivo:** `backend/app/api/v1/endpoints/pagos.py`
- **Función:** `_aplicar_monto_a_cuota()` (línea 1232)
- **Línea exacta:** `cuota.total_pagado += monto_aplicar`

### **Descripción:**
**`cuotas.total_pagado`** es la **COLUMNA PRINCIPAL** donde se almacenan los pagos conciliados.

- **Tipo:** `NUMERIC(12,2)`
- **Comportamiento:** **SUMA ACUMULATIVA** (se incrementa con cada pago)
- **Valor inicial:** `0.00`
- **Operación:** `total_pagado += monto_pagado` (se suma, no se reemplaza)

### **Ejemplo:**
```python
# Cuota inicial
cuotas.total_pagado = 0.00

# Pago 1: $200.00 conciliado
cuotas.total_pagado += 200.00  # Resultado: 200.00

# Pago 2: $150.00 conciliado
cuotas.total_pagado += 150.00  # Resultado: 350.00
```

---

## 📋 TODAS LAS COLUMNAS ACTUALIZADAS

Cuando se aplica un pago conciliado, se actualizan las siguientes columnas en `cuotas`:

| # | Columna | Tipo | Operación | Descripción |
|---|---------|------|-----------|-------------|
| **1** | **`total_pagado`** ⭐ | `NUMERIC(12,2)` | `+= monto_aplicar` | **COLUMNA PRINCIPAL** - Suma acumulativa de todos los pagos |
| **2** | `capital_pagado` | `NUMERIC(12,2)` | `+= capital_aplicar` | Capital pagado (proporcional al monto) |
| **3** | `interes_pagado` | `NUMERIC(12,2)` | `+= interes_aplicar` | Interés pagado (proporcional al monto) |
| **4** | `capital_pendiente` | `NUMERIC(12,2)` | `-= capital_aplicar` | Capital pendiente (se reduce) |
| **5** | `interes_pendiente` | `NUMERIC(12,2)` | `-= interes_aplicar` | Interés pendiente (se reduce) |
| **6** | `fecha_pago` | `DATE` | `= fecha_pago` | Fecha del pago aplicado |
| **7** | `estado` | `VARCHAR(20)` | `= 'PAGADO'/'PARCIAL'/'ATRASADO'` | Estado de la cuota (calculado) |
| **8** | `dias_mora` | `INTEGER` | `= 0` | Días de mora (siempre 0, mora desactivada) |
| **9** | `monto_mora` | `NUMERIC(12,2)` | `= 0.00` | Monto de mora (siempre 0, mora desactivada) |
| **10** | `tasa_mora` | `NUMERIC(5,2)` | `= 0.00` | Tasa de mora (siempre 0, mora desactivada) |
| **11** | `dias_morosidad` | `INTEGER` | Calculado automático | Días de morosidad (calculado) |
| **12** | `monto_morosidad` | `NUMERIC(12,2)` | Calculado automático | Monto pendiente (calculado) |

---

## 🔍 CÓDIGO EXACTO DE ACTUALIZACIÓN

### Función: `_aplicar_monto_a_cuota()` (línea 1209-1253)

```python
def _aplicar_monto_a_cuota(
    cuota,
    monto_aplicar: Decimal,
    fecha_pago: date,
    fecha_hoy: date,
    db: Session = None,
    es_exceso: bool = False,
) -> bool:
    # Calcular proporción capital/interés
    capital_aplicar, interes_aplicar = _calcular_proporcion_capital_interes(cuota, monto_aplicar)
    
    # ✅ COLUMNAS ACTUALIZADAS:
    
    # 1. COLUMNA PRINCIPAL: total_pagado (SUMA ACUMULATIVA)
    cuota.total_pagado += monto_aplicar  # ⭐ LÍNEA 1232
    
    # 2. Capital e interés pagados (SUMA ACUMULATIVA)
    cuota.capital_pagado += capital_aplicar      # LÍNEA 1230
    cuota.interes_pagado += interes_aplicar      # LÍNEA 1231
    
    # 3. Capital e interés pendientes (REDUCCIÓN)
    cuota.capital_pendiente = max(Decimal("0.00"), cuota.capital_pendiente - capital_aplicar)  # LÍNEA 1233
    cuota.interes_pendiente = max(Decimal("0.00"), cuota.interes_pendiente - interes_aplicar)  # LÍNEA 1234
    
    # 4. Fecha de pago
    if monto_aplicar > Decimal("0.00"):
        cuota.fecha_pago = fecha_pago  # LÍNEA 1237
        
        # 5. Mora (siempre 0, desactivada)
        cuota.dias_mora = 0                    # LÍNEA 1241
        cuota.monto_mora = Decimal("0.00")    # LÍNEA 1242
        cuota.tasa_mora = Decimal("0.00")     # LÍNEA 1243
        
        # 6. Actualizar morosidad (calculado automático)
        _actualizar_morosidad_cuota(cuota, fecha_hoy)  # LÍNEA 1251
    
    # 7. Actualizar estado (PAGADO, PARCIAL, ATRASADO, etc.)
    return _actualizar_estado_cuota(cuota, fecha_hoy, db, es_exceso)  # LÍNEA 1253
```

---

## 📊 RESUMEN EJECUTIVO

### **Columna Principal:**
**`cuotas.total_pagado`** ⭐

Esta es la **ÚNICA columna que necesitas verificar** para saber si un pago conciliado fue aplicado a una cuota.

### **Verificación:**
```sql
-- Verificar si hay pagos aplicados
SELECT 
    id,
    prestamo_id,
    numero_cuota,
    monto_cuota,
    total_pagado,  -- ⭐ COLUMNA PRINCIPAL
    estado
FROM cuotas
WHERE total_pagado > 0;
```

### **Limpieza (si es necesario):**
```sql
-- Limpiar total_pagado antes de aplicar pagos
UPDATE cuotas
SET total_pagado = 0.00
WHERE total_pagado > 0;
```

---

## ⚠️ IMPORTANTE

1. **`total_pagado` es ACUMULATIVO:**
   - Se **SUMA** con cada pago (`+=`)
   - **NO se reemplaza** (`=`)

2. **Solo pagos CONCILIADOS se aplican:**
   - Condición: `pagos.conciliado = True` **O** `pagos.verificado_concordancia = 'SI'`
   - Si el pago NO está conciliado, `total_pagado` NO se actualiza

3. **Orden de aplicación:**
   - Los pagos se aplican a las cuotas **más antiguas primero** (por `fecha_vencimiento`)
   - Si una cuota se completa, el exceso se aplica a la siguiente

4. **Estado de la cuota:**
   - Se actualiza automáticamente según `total_pagado` vs `monto_cuota`
   - `PAGADO`: `total_pagado >= monto_cuota`
   - `PARCIAL`: `0 < total_pagado < monto_cuota`
   - `PENDIENTE`: `total_pagado = 0`

---

## 📝 CONCLUSIÓN

**Los pagos conciliados van a la columna `cuotas.total_pagado`**

- **Columna específica:** `total_pagado`
- **Tipo:** `NUMERIC(12,2)`
- **Comportamiento:** Suma acumulativa (`+=`)
- **Ubicación código:** `backend/app/api/v1/endpoints/pagos.py`, línea 1232
- **Función:** `_aplicar_monto_a_cuota()`

**Esta es la columna que debes verificar para asegurarte de que está vacía antes de aplicar pagos conciliados.**
