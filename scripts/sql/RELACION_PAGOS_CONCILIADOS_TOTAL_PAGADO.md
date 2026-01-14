# 🔍 RELACIÓN ENTRE PAGOS CONCILIADOS Y `cuotas.total_pagado`

> **Respuesta a:** "confirma por cada pago conciliado (que viene desde tabla pagos) hay un cuotas.total_pagado en donde se copia el pago conciliado?"

---

## ❌ RESPUESTA DIRECTA: NO ES UNA RELACIÓN 1:1

**NO**, no hay una relación 1:1 entre un pago conciliado y un `cuotas.total_pagado`.

**La relación real es:**
- **1 pago conciliado** → puede distribuirse entre **MÚLTIPLES cuotas** (distribución)
- **1 cuota** → puede recibir **MÚLTIPLES pagos** (acumulación)

---

## 🔄 CÓMO FUNCIONA LA DISTRIBUCIÓN

### **Proceso de Aplicación:**

1. **Pago conciliado** (`pagos.monto_pagado = $500`)
2. **Se obtienen cuotas pendientes** del préstamo (ordenadas por fecha de vencimiento)
3. **Se distribuye el monto** entre las cuotas más antiguas primero
4. **Cada cuota recibe una porción** en su `total_pagado`

### **Ejemplo 1: Un Pago se Distribuye en Múltiples Cuotas**

```
Pago Conciliado:
- pagos.id = 100
- pagos.monto_pagado = $500
- pagos.conciliado = TRUE
- pagos.prestamo_id = 123

Cuotas del Préstamo 123:
- Cuota 1: monto_cuota = $300, total_pagado = $0 → Recibe $300
- Cuota 2: monto_cuota = $300, total_pagado = $0 → Recibe $200 (exceso)
- Cuota 3: monto_cuota = $300, total_pagado = $0 → No recibe nada

Resultado:
- Cuota 1: total_pagado = $300 (del pago 100)
- Cuota 2: total_pagado = $200 (del pago 100)
- Cuota 3: total_pagado = $0

✅ UN pago afectó DOS cuotas
```

### **Ejemplo 2: Múltiples Pagos se Acumulan en una Cuota**

```
Cuota 1 del Préstamo 123:
- monto_cuota = $300
- total_pagado inicial = $0

Pago 1 Conciliado:
- pagos.id = 100
- pagos.monto_pagado = $150
- Se aplica a Cuota 1 → total_pagado = $150

Pago 2 Conciliado:
- pagos.id = 101
- pagos.monto_pagado = $100
- Se aplica a Cuota 1 → total_pagado = $250

Pago 3 Conciliado:
- pagos.id = 102
- pagos.monto_pagado = $50
- Se aplica a Cuota 1 → total_pagado = $300 (completada)

Resultado:
- Cuota 1: total_pagado = $300 (suma de pagos 100 + 101 + 102)

✅ UNA cuota recibió TRES pagos
```

---

## 📊 RELACIÓN REAL: N:M (Muchos a Muchos)

```
┌─────────────────┐         ┌──────────────────┐
│  pagos          │         │  cuotas          │
├─────────────────┤         ├──────────────────┤
│ id              │         │ id               │
│ monto_pagado    │─────────│ total_pagado     │
│ conciliado      │   N:M   │ monto_cuota      │
│ prestamo_id     │         │ prestamo_id      │
└─────────────────┘         └──────────────────┘
     │                              │
     │                              │
     └──────────┬───────────────────┘
                │
         (distribución/acumulación)
```

**Características:**
- **Un pago** puede afectar **múltiples cuotas** (distribución)
- **Una cuota** puede recibir **múltiples pagos** (acumulación)
- **No hay tabla intermedia** - la relación se maneja mediante la distribución del monto

---

## 🔍 CÓDIGO QUE LO IMPLEMENTA

### **Función: `_aplicar_pago_a_cuotas_iterativas()`**

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` (línea 1334)

```python
def _aplicar_pago_a_cuotas_iterativas(
    cuotas: list, saldo_restante: Decimal, fecha_pago: date, fecha_hoy: date, db: Session
) -> tuple[int, Decimal]:
    """Aplica el pago a las cuotas iterativamente"""
    cuotas_completadas = 0

    for cuota in cuotas:  # ← Itera sobre MÚLTIPLES cuotas
        if saldo_restante <= Decimal("0.00"):
            break

        monto_faltante = cuota.monto_cuota - cuota.total_pagado
        monto_aplicar = min(saldo_restante, monto_faltante)  # ← Porción del pago

        if monto_aplicar <= Decimal("0.00"):
            continue

        # ✅ AQUÍ SE ACTUALIZA total_pagado EN CADA CUOTA
        if _aplicar_monto_a_cuota(cuota, monto_aplicar, fecha_pago, fecha_hoy, db):
            cuotas_completadas += 1

        saldo_restante -= monto_aplicar  # ← Reduce el saldo para la siguiente cuota

    return cuotas_completadas, saldo_restante
```

**Puntos clave:**
- Itera sobre **múltiples cuotas** (`for cuota in cuotas`)
- Aplica una **porción del pago** a cada cuota (`monto_aplicar`)
- El **saldo restante** se reduce y se aplica a la siguiente cuota

---

## ✅ VERIFICACIÓN EN BASE DE DATOS

### **Consulta 1: Ver cómo un pago se distribuye en múltiples cuotas**

```sql
-- Ver un pago específico y cómo se distribuyó
SELECT 
    p.id as pago_id,
    p.monto_pagado,
    p.conciliado,
    c.id as cuota_id,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,
    c.fecha_vencimiento
FROM public.pagos p
JOIN public.cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.id = 100  -- ID del pago a verificar
  AND p.conciliado = TRUE
ORDER BY c.fecha_vencimiento, c.numero_cuota;
```

**Resultado esperado:** Múltiples filas (una por cada cuota afectada)

### **Consulta 2: Ver cómo múltiples pagos se acumulan en una cuota**

```sql
-- Ver una cuota específica y todos los pagos que la afectaron
SELECT 
    c.id as cuota_id,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,
    COUNT(p.id) as cantidad_pagos,
    SUM(p.monto_pagado) as suma_pagos_conciliados
FROM public.cuotas c
JOIN public.pagos p ON p.prestamo_id = c.prestamo_id
WHERE c.id = 500  -- ID de la cuota a verificar
  AND p.conciliado = TRUE
  AND p.fecha_pago <= c.fecha_pago  -- Solo pagos anteriores o iguales
GROUP BY c.id, c.numero_cuota, c.monto_cuota, c.total_pagado;
```

**Resultado esperado:** Una fila mostrando que `total_pagado` es la suma de múltiples pagos

### **Consulta 3: Verificar que la suma de pagos conciliados coincide con total_pagado**

```sql
-- Verificar consistencia: suma de pagos conciliados = total_pagado por préstamo
SELECT 
    c.prestamo_id,
    COUNT(DISTINCT p.id) as cantidad_pagos_conciliados,
    SUM(p.monto_pagado) as suma_pagos_conciliados,
    SUM(c.total_pagado) as suma_total_pagado_cuotas,
    CASE 
        WHEN ABS(SUM(p.monto_pagado) - SUM(c.total_pagado)) < 0.01 
        THEN 'OK - Coinciden'
        ELSE 'ERROR - No coinciden'
    END as verificacion
FROM public.pagos p
JOIN public.cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.conciliado = TRUE
GROUP BY c.prestamo_id
ORDER BY c.prestamo_id
LIMIT 10;
```

**Resultado esperado:** `suma_pagos_conciliados` debe ser igual a `suma_total_pagado_cuotas` por préstamo

---

## 📝 RESUMEN

### **NO es 1:1**
- ❌ Un pago conciliado NO se copia directamente a UNA cuota
- ❌ Una cuota NO recibe solo UN pago

### **SÍ es N:M**
- ✅ Un pago conciliado se **distribuye** entre múltiples cuotas (más antiguas primero)
- ✅ Una cuota **acumula** múltiples pagos en su `total_pagado`
- ✅ `cuotas.total_pagado` es la **suma acumulativa** de todas las porciones de pagos aplicadas

### **Fórmula:**
```
cuotas.total_pagado = SUM(porciones de todos los pagos conciliados aplicados a esta cuota)
```

Donde cada "porción" es:
```
porcion_pago = min(monto_pagado_restante, monto_cuota - total_pagado_actual)
```

---

## ✅ CONCLUSIÓN

**Por cada pago conciliado:**
- Se distribuye entre las cuotas pendientes del préstamo
- Cada cuota recibe una porción en su `total_pagado`
- Puede afectar una o múltiples cuotas según el monto

**Por cada cuota:**
- Su `total_pagado` acumula porciones de múltiples pagos conciliados
- Es la suma de todas las porciones recibidas
- Puede recibir pagos de diferentes fechas y montos

**Relación:** N:M (Muchos a Muchos) mediante distribución/acumulación del monto.
