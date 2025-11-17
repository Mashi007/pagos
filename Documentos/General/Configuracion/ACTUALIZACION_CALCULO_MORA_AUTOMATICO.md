# ✅ ACTUALIZACIÓN: Cálculo Automático de Mora

## Fecha de Implementación
Actualizado según requerimiento: "UNIFICAR EN FECHA DE PAGO, SI DESPUÉS DE FECHA CAE EN MORA"

---

## 🎯 OBJETIVO

**Unificar la lógica de mora:** Cuando `fecha_pago > fecha_vencimiento`, calcular automáticamente `dias_mora` y `monto_mora`.

---

## 🔧 CAMBIOS IMPLEMENTADOS

### Archivo Modificado

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py`
**Función:** `_aplicar_monto_a_cuota()` (líneas 1013-1077)

### Lógica Agregada

```python
# ✅ UNIFICAR EN FECHA DE PAGO: Si fecha_pago > fecha_vencimiento, calcular mora automáticamente
if cuota.fecha_vencimiento and fecha_pago > cuota.fecha_vencimiento:
    # Calcular días de mora
    dias_mora = (fecha_pago - cuota.fecha_vencimiento).days

    # Obtener tasa de mora diaria (por defecto desde settings)
    tasa_mora_diaria = Decimal(str(settings.TASA_MORA_DIARIA))  # 0.067% diario

    # Calcular monto de mora
    saldo_base_mora = cuota.monto_cuota
    monto_mora = (saldo_base_mora * tasa_mora_diaria * Decimal(dias_mora) / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Actualizar campos de mora
    cuota.dias_mora = dias_mora
    cuota.monto_mora = monto_mora
    cuota.tasa_mora = tasa_mora_diaria
else:
    # Si pago a tiempo o adelantado, no hay mora
    if fecha_pago <= cuota.fecha_vencimiento:
        cuota.dias_mora = 0
        cuota.monto_mora = Decimal("0.00")
        cuota.tasa_mora = Decimal("0.00")
```

---

## 📊 COMPORTAMIENTO

### Escenario 1: Pago a Tiempo

```
fecha_vencimiento: 2025-11-30
fecha_pago:        2025-11-28  ← ANTES del vencimiento

Resultado:
- dias_mora: 0
- monto_mora: $0.00
- tasa_mora: 0.00%
- estado: PAGADO (o PENDIENTE si parcial)
```

### Escenario 2: Pago Tardío (Mora)

```
fecha_vencimiento: 2025-11-30
fecha_pago:        2025-12-15  ← DESPUÉS del vencimiento (15 días tarde)

Cálculo:
- dias_mora = (2025-12-15 - 2025-11-30).days = 15 días
- tasa_mora_diaria = 0.067% (desde settings)
- monto_cuota = $500.00
- monto_mora = $500.00 * 0.067 * 15 / 100 = $5.03

Resultado:
- dias_mora: 15
- monto_mora: $5.03
- tasa_mora: 0.067%
- estado: PAGADO (pero con mora)
```

### Escenario 3: Pago Adelantado

```
fecha_vencimiento: 2025-11-30
fecha_pago:        2025-10-15  ← MUCHO ANTES del vencimiento

Resultado:
- dias_mora: 0
- monto_mora: $0.00
- tasa_mora: 0.00%
- estado: ADELANTADO (si parcial) o PAGADO (si completo)
```

---

## ⚙️ CONFIGURACIÓN

### Tasa de Mora

**Ubicación:** `backend/app/core/config.py`

```python
TASA_MORA: float = 2.0  # 2% mensual
TASA_MORA_DIARIA: float = 0.067  # 2% / 30 días
```

**Fórmula de Cálculo:**
```
monto_mora = monto_cuota * tasa_mora_diaria * dias_mora / 100
```

**Ejemplo:**
- Cuota: $500.00
- Días de mora: 15
- Tasa diaria: 0.067%
- Mora = $500.00 * 0.067 * 15 / 100 = **$5.03**

---

## 🔄 FLUJO COMPLETO

### 1. Usuario Registra un Pago

```python
POST /api/v1/pagos
{
    "prestamo_id": 3708,
    "numero_cuota": 1,
    "fecha_pago": "2025-12-15",  # 15 días después del vencimiento
    "monto_pagado": 500.00
}
```

### 2. Sistema Aplica Pago a Cuota

```python
_aplicar_monto_a_cuota(
    cuota=cuota_1,
    monto_aplicar=500.00,
    fecha_pago=date(2025, 12, 15),  # fecha_pago > fecha_vencimiento
    fecha_hoy=date(2025, 12, 15)
)
```

### 3. Sistema Detecta Mora

```python
# fecha_pago (2025-12-15) > fecha_vencimiento (2025-11-30)
# → Calcular mora automáticamente
```

### 4. Sistema Calcula y Actualiza Mora

```python
dias_mora = 15
monto_mora = $5.03
tasa_mora = 0.067%

# Actualiza cuota
cuota.dias_mora = 15
cuota.monto_mora = 5.03
cuota.tasa_mora = 0.067
cuota.fecha_pago = 2025-12-15
```

### 5. Sistema Actualiza Estado

```python
# Si total_pagado >= monto_cuota
cuota.estado = "PAGADO"  # (aunque tenga mora)
```

---

## 📋 CAMPOS ACTUALIZADOS

Cuando `fecha_pago > fecha_vencimiento`, se actualizan automáticamente:

| Campo | Valor | Descripción |
|-------|-------|-------------|
| `fecha_pago` | Fecha del pago | ✅ Se establece con la fecha del pago |
| `dias_mora` | Días de diferencia | ✅ `(fecha_pago - fecha_vencimiento).days` |
| `monto_mora` | Monto calculado | ✅ `monto_cuota * tasa_diaria * dias_mora / 100` |
| `tasa_mora` | Tasa aplicada | ✅ `TASA_MORA_DIARIA` desde settings |

---

## ✅ VENTAJAS

1. **Automático:** No requiere cálculo manual de mora
2. **Consistente:** Usa la misma lógica en todos los pagos
3. **Unificado:** Toda la lógica de mora basada en `fecha_pago`
4. **Preciso:** Calcula mora exacta según días de atraso
5. **Configurable:** Tasa de mora desde settings (fácil de cambiar)

---

## ⚠️ CONSIDERACIONES

### 1. Base de Cálculo de Mora

**Actual:** Usa `monto_cuota` como base

```python
saldo_base_mora = cuota.monto_cuota
```

**Alternativa (si se prefiere):** Usar saldo pendiente

```python
saldo_base_mora = cuota.capital_pendiente + cuota.interes_pendiente
```

**Recomendación:** Mantener `monto_cuota` para consistencia con el sistema actual.

### 2. Pagos Parciales con Mora

Si un pago parcial se registra después del vencimiento:
- ✅ Se calcula mora automáticamente
- ✅ El pago se aplica a capital, interés y mora
- ✅ Estado puede ser `PARCIAL` si no cubre toda la cuota + mora

### 3. Múltiples Pagos en una Cuota

Si una cuota recibe múltiples pagos:
- `fecha_pago` se establece con la fecha del **primer pago**
- Si el primer pago fue tardío, se calcula mora
- Si el primer pago fue a tiempo, no hay mora (aunque pagos posteriores sean tardíos)

**Nota:** Esto es consistente con la lógica actual del sistema.

---

## 🧪 PRUEBAS RECOMENDADAS

### Test 1: Pago Tardío

```python
# Cuota vence: 2025-11-30
# Pago registrado: 2025-12-15 (15 días tarde)
# Resultado esperado:
# - dias_mora = 15
# - monto_mora > 0
# - estado = PAGADO (si cubre cuota + mora)
```

### Test 2: Pago a Tiempo

```python
# Cuota vence: 2025-11-30
# Pago registrado: 2025-11-28 (2 días antes)
# Resultado esperado:
# - dias_mora = 0
# - monto_mora = 0.00
# - estado = PAGADO
```

### Test 3: Pago Adelantado

```python
# Cuota vence: 2025-11-30
# Pago registrado: 2025-10-15 (45 días antes)
# Resultado esperado:
# - dias_mora = 0
# - monto_mora = 0.00
# - estado = ADELANTADO (si parcial) o PAGADO (si completo)
```

---

## 📝 LOGS

El sistema registra automáticamente cuando se calcula mora:

```
💰 [aplicar_monto_a_cuota] Cuota #1 (Préstamo 3708):
   Mora calculada: 15 días, $5.03
   (fecha_pago: 2025-12-15, fecha_vencimiento: 2025-11-30)
```

---

## 🔍 VERIFICACIÓN EN BASE DE DATOS

### Consulta para Verificar Mora Calculada

```sql
SELECT
    c.numero_cuota,
    c.fecha_vencimiento,
    c.fecha_pago,
    c.dias_mora,
    c.monto_mora,
    c.tasa_mora,
    c.estado,
    CASE
        WHEN c.fecha_pago > c.fecha_vencimiento THEN '✅ Mora calculada'
        WHEN c.fecha_pago <= c.fecha_vencimiento THEN '✅ Sin mora'
        ELSE '⏳ Pendiente'
    END as verificacion_mora
FROM cuotas c
WHERE c.prestamo_id = 3708
ORDER BY c.numero_cuota;
```

---

## ✅ RESUMEN

### Antes

- ❌ Mora se calculaba manualmente o no se calculaba automáticamente
- ❌ `dias_mora` y `monto_mora` podían quedar en 0 aunque hubiera atraso

### Después

- ✅ Mora se calcula **automáticamente** cuando `fecha_pago > fecha_vencimiento`
- ✅ `dias_mora` y `monto_mora` se actualizan automáticamente
- ✅ Lógica unificada: todo basado en comparación de `fecha_pago` vs `fecha_vencimiento`

---

**Estado:** ✅ **IMPLEMENTADO Y LISTO PARA USO**

