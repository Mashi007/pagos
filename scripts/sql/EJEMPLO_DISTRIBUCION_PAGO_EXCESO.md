# 📋 EJEMPLO: Distribución de Pago con Exceso

> **Respuesta a:** "Si hay un pago de 100USD en tabla pagos y esta conciliado de cédula V123. Se verifica y en la tabla cuotas de la cédula correspondiente V123 la cuota siguiente por cubrir es de 90USD entonces se copia a cuotas.total_pagado por 90 USD y se crea otra cuotas.total_pagado por 10 USD"

---

## ❌ CORRECCIÓN: NO se crea una nueva cuota

**Lo que NO pasa:**
- ❌ NO se crea una nueva cuota con `total_pagado = $10`
- ❌ NO se crea un nuevo registro en la tabla `cuotas`

**Lo que SÍ pasa:**
- ✅ Se aplica $90 a la primera cuota pendiente (completándola)
- ✅ El exceso de $10 se aplica a la **SIGUIENTE cuota pendiente existente**
- ✅ Se actualizan los `total_pagado` de las cuotas existentes

---

## ✅ EJEMPLO CORRECTO

### **Situación Inicial:**

```
Pago Conciliado:
- pagos.id = 100
- pagos.monto_pagado = $100
- pagos.conciliado = TRUE
- pagos.cedula = 'V123'
- pagos.prestamo_id = 123

Préstamo 123 (cédula V123) - Cuotas Existentes:
- Cuota 1: monto_cuota = $90, total_pagado = $0, estado = 'PENDIENTE'
- Cuota 2: monto_cuota = $90, total_pagado = $0, estado = 'PENDIENTE'
- Cuota 3: monto_cuota = $90, total_pagado = $0, estado = 'PENDIENTE'
- Cuota 4: monto_cuota = $90, total_pagado = $0, estado = 'PENDIENTE'
```

### **Proceso de Aplicación:**

```
PASO 1: Obtener cuotas pendientes
└─ Cuota 1, Cuota 2, Cuota 3, Cuota 4 (ordenadas por fecha_vencimiento)

PASO 2: Aplicar pago de $100
├─ Cuota 1: monto_faltante = $90 - $0 = $90
│  └─ monto_aplicar = min($100, $90) = $90
│  └─ total_pagado = $0 + $90 = $90 ✅ (COMPLETADA)
│  └─ saldo_restante = $100 - $90 = $10
│
├─ Cuota 2: monto_faltante = $90 - $0 = $90
│  └─ monto_aplicar = min($10, $90) = $10
│  └─ total_pagado = $0 + $10 = $10 ✅ (PARCIAL)
│  └─ saldo_restante = $10 - $10 = $0
│
└─ Saldo restante = $0 → FIN del proceso
```

### **Resultado Final:**

```
Cuotas Actualizadas (NO se crearon nuevas):
- Cuota 1: monto_cuota = $90, total_pagado = $90, estado = 'PAGADO' ✅
- Cuota 2: monto_cuota = $90, total_pagado = $10, estado = 'PARCIAL' ✅
- Cuota 3: monto_cuota = $90, total_pagado = $0, estado = 'PENDIENTE'
- Cuota 4: monto_cuota = $90, total_pagado = $0, estado = 'PENDIENTE'

✅ Se ACTUALIZARON 2 cuotas existentes
❌ NO se creó ninguna cuota nueva
```

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

    for cuota in cuotas:  # ← Itera sobre cuotas EXISTENTES
        if saldo_restante <= Decimal("0.00"):
            break

        monto_faltante = cuota.monto_cuota - cuota.total_pagado
        monto_aplicar = min(saldo_restante, monto_faltante)

        if monto_aplicar <= Decimal("0.00"):
            continue

        # ✅ ACTUALIZA cuota EXISTENTE (NO crea nueva)
        if _aplicar_monto_a_cuota(cuota, monto_aplicar, fecha_pago, fecha_hoy, db):
            cuotas_completadas += 1

        saldo_restante -= monto_aplicar

    return cuotas_completadas, saldo_restante
```

### **Función: `_aplicar_exceso_a_siguiente_cuota()`**

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` (línea 1257)

```python
def _aplicar_exceso_a_siguiente_cuota(
    db: Session, prestamo_id: int, saldo_restante: Decimal, fecha_pago: date, fecha_hoy: date
) -> int:
    """
    Aplica el exceso de pago a la siguiente cuota pendiente (más antigua primero).

    Returns:
        número de cuotas completadas
    """
    # ✅ Busca SIGUIENTE cuota PENDIENTE EXISTENTE (NO crea nueva)
    siguiente_cuota = (
        db.query(Cuota)
        .filter(
            Cuota.prestamo_id == prestamo_id,
            Cuota.estado != "PAGADO",
        )
        .order_by(Cuota.fecha_vencimiento, Cuota.numero_cuota)
        .first()
    )

    if not siguiente_cuota:
        return 0

    monto_faltante = siguiente_cuota.monto_cuota - siguiente_cuota.total_pagado
    monto_aplicar_exceso = min(saldo_restante, monto_faltante)

    if monto_aplicar_exceso <= Decimal("0.00"):
        return 0

    # ✅ ACTUALIZA cuota EXISTENTE (NO crea nueva)
    estado_completado = _aplicar_monto_a_cuota(
        siguiente_cuota, monto_aplicar_exceso, fecha_pago, fecha_hoy, db, es_exceso=True
    )

    return 1 if estado_completado else 0
```

**Puntos clave:**
- Busca la **siguiente cuota pendiente EXISTENTE** (`db.query(Cuota).filter(...).first()`)
- **Actualiza** esa cuota (`_aplicar_monto_a_cuota()`)
- **NO crea** ninguna cuota nueva

---

## ✅ VERIFICACIÓN EN BASE DE DATOS

### **Consulta: Verificar que NO se crean cuotas nuevas**

```sql
-- Antes del pago: Contar cuotas del préstamo
SELECT COUNT(*) as total_cuotas_antes
FROM public.cuotas
WHERE prestamo_id = 123;

-- Aplicar pago (esto lo hace el código Python automáticamente)

-- Después del pago: Contar cuotas del préstamo
SELECT COUNT(*) as total_cuotas_despues
FROM public.cuotas
WHERE prestamo_id = 123;

-- Verificar que el número de cuotas NO cambió
SELECT 
    (SELECT COUNT(*) FROM public.cuotas WHERE prestamo_id = 123) as total_cuotas,
    (SELECT COUNT(*) FROM public.prestamos WHERE id = 123) as numero_cuotas_esperadas
FROM public.prestamos
WHERE id = 123;
```

**Resultado esperado:** El número de cuotas debe ser igual antes y después del pago.

### **Consulta: Ver cómo se distribuyó el pago**

```sql
-- Ver cómo se distribuyó el pago de $100
SELECT 
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,
    c.estado,
    CASE 
        WHEN c.total_pagado > 0 THEN 'AFECTADA POR EL PAGO'
        ELSE 'NO AFECTADA'
    END as afectada_por_pago
FROM public.cuotas c
WHERE c.prestamo_id = 123
ORDER BY c.numero_cuota;
```

**Resultado esperado:**
```
numero_cuota | monto_cuota | total_pagado | estado   | afectada_por_pago
-------------|-------------|--------------|----------|-------------------
1            | 90          | 90           | PAGADO   | AFECTADA POR EL PAGO
2            | 90          | 10           | PARCIAL  | AFECTADA POR EL PAGO
3            | 90          | 0            | PENDIENTE| NO AFECTADA
4            | 90          | 0            | PENDIENTE| NO AFECTADA
```

---

## 📝 RESUMEN DEL EJEMPLO

### **Tu ejemplo:**
- Pago: $100 USD conciliado (cédula V123)
- Cuota siguiente: $90 USD

### **Lo que pasa:**
1. ✅ Se aplica $90 a la primera cuota pendiente → `total_pagado = $90` (completada)
2. ✅ Se aplica $10 a la siguiente cuota pendiente → `total_pagado = $10` (parcial)
3. ❌ **NO se crea** una nueva cuota con $10

### **Reglas importantes:**
- ✅ Las cuotas se **crean** cuando se genera la tabla de amortización del préstamo
- ✅ Los pagos solo **actualizan** las cuotas existentes
- ✅ El exceso se aplica a la **siguiente cuota pendiente existente**
- ❌ **NUNCA** se crean cuotas nuevas al aplicar pagos

---

## ✅ CONCLUSIÓN

**Tu ejemplo corregido:**

```
Pago: $100 USD conciliado (cédula V123)
Cuota siguiente: $90 USD

Resultado:
- Cuota 1: total_pagado = $90 ✅ (actualizada, no creada)
- Cuota 2: total_pagado = $10 ✅ (actualizada, no creada)
- NO se crea ninguna cuota nueva
```

**Relación:**
- Las cuotas se crean una vez al generar la tabla de amortización
- Los pagos solo actualizan los `total_pagado` de las cuotas existentes
- El exceso se distribuye automáticamente a la siguiente cuota pendiente
