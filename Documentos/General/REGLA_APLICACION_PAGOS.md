# 🎯 REGLA DE NEGOCIO: ¿A DÓNDE SE APLICA UN PAGO CUANDO SE REGISTRA?

> **Regla crítica del sistema**
> Última actualización: 2026-01-08

---

## ⚠️ RESPUESTA DIRECTA

**Cuando registras un pago, NO se aplica automáticamente a ninguna cuota.**

**El pago se aplica a las cuotas SOLO cuando está conciliado.**

---

## 📋 FLUJO COMPLETO: Registro → Aplicación

### **FASE 1: REGISTRO DEL PAGO**

Cuando registras un pago (manual o masivo):

```
1. Se crea registro en tabla `pagos`
   └─ pagos.monto_pagado = monto del pago
   └─ pagos.prestamo_id = encontrado automáticamente o del request
   └─ pagos.conciliado = False (default)
   └─ pagos.verificado_concordancia = 'NO' (default)
   └─ pagos.estado = 'PAGADO' (default)

2. ⚠️ NO SE APLICA A CUOTAS
   └─ El pago está registrado pero NO conciliado
   └─ cuotas.total_pagado NO se actualiza
   └─ Las cuotas NO cambian de estado
```

**Código del endpoint:**
```python
# backend/app/api/v1/endpoints/pagos.py - línea 657
# ⚠️ NO APLICAR PAGO A CUOTAS AQUÍ
# Los pagos solo se aplican a cuotas cuando están conciliados
# La aplicación a cuotas se hará automáticamente cuando el pago se concilie
```

---

### **FASE 2: CONCILIACIÓN DEL PAGO**

Cuando concilias el pago (manual, Excel, o automático):

```
1. Se marca el pago como conciliado
   └─ pagos.conciliado = True
   └─ pagos.verificado_concordancia = 'SI'
   └─ pagos.fecha_conciliacion = datetime.now()

2. ✅ AHORA SÍ SE APLICA A CUOTAS AUTOMÁTICAMENTE
   └─ Se llama a aplicar_pago_a_cuotas()
   └─ Se verifica que el pago esté conciliado
   └─ Se aplica el monto a las cuotas correspondientes
```

---

## 🎯 ¿A DÓNDE SE APLICA EL PAGO?

### **Regla de Aplicación:**

**El pago se aplica a las CUOTAS del préstamo asociado, en este orden:**

1. ✅ **Cuotas más antiguas primero** (ordenadas por `fecha_vencimiento`)
2. ✅ **Solo cuotas pendientes** (`estado != "PAGADO"`)
3. ✅ **Una cuota a la vez** hasta agotar el monto del pago
4. ✅ **Si sobra monto**, se aplica a la siguiente cuota pendiente

### **Ejemplo Práctico:**

```
Préstamo ID: 123
Cuotas pendientes:
- Cuota 1: fecha_vencimiento = 2025-01-15, monto_cuota = $100.00, total_pagado = $0.00
- Cuota 2: fecha_vencimiento = 2025-02-15, monto_cuota = $100.00, total_pagado = $0.00
- Cuota 3: fecha_vencimiento = 2025-03-15, monto_cuota = $100.00, total_pagado = $0.00

Pago registrado: monto_pagado = $150.00

DESPUÉS DE CONCILIAR:
- Cuota 1: total_pagado = $100.00, estado = "PAGADO" ✅
- Cuota 2: total_pagado = $50.00, estado = "PARCIAL" ✅
- Cuota 3: total_pagado = $0.00, estado = "PENDIENTE" (sin cambios)
```

---

## 🔒 CONDICIONES OBLIGATORIAS PARA APLICAR A CUOTAS

**El pago SOLO se aplica a cuotas si se cumplen TODAS estas condiciones:**

1. ✅ `pagos.conciliado = True` **O** `pagos.verificado_concordancia = 'SI'`
2. ✅ `pagos.prestamo_id` NO es NULL
3. ✅ El préstamo existe en la base de datos
4. ✅ La cédula del pago coincide con la cédula del préstamo
5. ✅ Hay cuotas pendientes (`estado != "PAGADO"`)

**Si alguna condición NO se cumple, el pago NO se aplica a cuotas.**

---

## 📊 TABLA DE ESTADOS

| Estado del Pago | `conciliado` | `prestamo_id` | ¿Se aplica a cuotas? | ¿Dónde se aplica? |
|-----------------|--------------|---------------|----------------------|-------------------|
| Registrado | `False` | `123` | ❌ NO | N/A |
| Registrado sin préstamo | `False` | `NULL` | ❌ NO | N/A |
| Conciliado | `True` | `123` | ✅ SÍ | Cuotas del préstamo 123 |
| Conciliado sin préstamo | `True` | `NULL` | ❌ NO | N/A |

---

## 🔄 PROCESO DE APLICACIÓN A CUOTAS

### **Paso 1: Verificar Conciliación**
```python
if not pago.conciliado:
    verificado_ok = pago.verificado_concordancia == "SI"
    if not verificado_ok:
        return 0  # ⚠️ NO SE APLICA A CUOTAS
```

### **Paso 2: Obtener Cuotas Pendientes**
```python
cuotas = db.query(Cuota).filter(
    Cuota.prestamo_id == pago.prestamo_id,
    Cuota.estado != "PAGADO"
).order_by(Cuota.fecha_vencimiento).all()
```

### **Paso 3: Aplicar Monto a Cuotas**
```python
saldo_restante = pago.monto_pagado

for cuota in cuotas:  # Ordenadas por fecha_vencimiento (más antigua primero)
    monto_faltante = cuota.monto_cuota - cuota.total_pagado
    monto_aplicar = min(saldo_restante, monto_faltante)
    
    # Aplicar monto a la cuota
    cuota.total_pagado += monto_aplicar
    saldo_restante -= monto_aplicar
    
    # Actualizar estado de la cuota
    if cuota.total_pagado >= cuota.monto_cuota:
        cuota.estado = "PAGADO"
    else:
        cuota.estado = "PARCIAL"
    
    if saldo_restante <= 0:
        break  # Se agotó el monto del pago
```

---

## ✅ RESUMEN DE LA REGLA DE NEGOCIO

### **Cuando registras un pago:**

1. ✅ Se guarda en la tabla `pagos`
2. ✅ Se busca automáticamente el `prestamo_id` (si no viene en el request)
3. ❌ **NO se aplica a cuotas** (aún no está conciliado)

### **Cuando concilias el pago:**

1. ✅ Se marca como conciliado (`conciliado = True`)
2. ✅ **Se aplica automáticamente a las cuotas** del préstamo asociado
3. ✅ Se aplica a las cuotas más antiguas primero
4. ✅ Si sobra monto, se aplica a la siguiente cuota pendiente

### **Dónde se aplica:**

- ✅ **Tabla `cuotas`** del préstamo asociado (`pagos.prestamo_id`)
- ✅ **Orden:** Cuotas más antiguas primero (por `fecha_vencimiento`)
- ✅ **Solo cuotas pendientes** (`estado != "PAGADO"`)

---

## ⚠️ IMPORTANTE

**Regla crítica:**
- Los pagos **NO se aplican a cuotas** cuando se registran
- Los pagos **SOLO se aplican a cuotas** cuando están conciliados
- La aplicación es **automática** cuando se concilia el pago
- Se aplica a las **cuotas del préstamo asociado**, empezando por las más antiguas

---

**Última actualización:** 2026-01-08
