# 🔒 Regla de Negocio: Conciliación de Pagos y Aplicación a Cuotas

> **Regla crítica del sistema**
> Última actualización: 2025-11-06

---

## 🎯 Regla Principal

**Los pagos SOLO se aplican a cuotas cuando están conciliados.**

### **Condiciones Obligatorias:**

1. ✅ `pagos.conciliado = True` **O** `pagos.verificado_concordancia = 'SI'`
2. ✅ `pagos.prestamo_id` NO es NULL
3. ✅ El préstamo existe y la cédula coincide

**Si alguna de estas condiciones NO se cumple, el pago NO se aplica a cuotas.**

---

## 📋 Flujo Completo

### **FASE 1: Registro de Pago**

```
1. Usuario registra pago (manual o masivo)
   └─ Se crea registro en tabla pagos
   └─ pagos.monto_pagado = monto del pago
   └─ pagos.prestamo_id = encontrado automáticamente o del request
   └─ pagos.conciliado = False (default)
   └─ pagos.verificado_concordancia = 'NO' (default)

2. ⚠️ NO se aplica a cuotas todavía
   └─ El pago está registrado pero NO conciliado
   └─ cuotas.total_pagado NO se actualiza
```

---

### **FASE 2: Conciliación de Pago**

```
1. Usuario concilia pago (manual, Excel, o automático)
   └─ pagos.conciliado = True
   └─ pagos.verificado_concordancia = 'SI'
   └─ pagos.fecha_conciliacion = datetime.now()

2. ✅ AHORA SÍ se aplica a cuotas automáticamente
   └─ Se llama a aplicar_pago_a_cuotas()
   └─ Se verifica que el pago esté conciliado
   └─ Se aplica el monto a las cuotas correspondientes
   └─ cuotas.total_pagado += monto_pagado
```

---

## 🔍 Validaciones en el Código

### **Función: `aplicar_pago_a_cuotas()`**

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` (líneas 1251-1306)

**Validación de Conciliación:**
```python
# ✅ VERIFICAR QUE EL PAGO ESTÉ CONCILIADO
if not pago.conciliado:
    verificado_ok = getattr(pago, "verificado_concordancia", None) == "SI"
    if not verificado_ok:
        logger.warning("Pago NO está conciliado. No se aplicará a cuotas.")
        return 0  # ⚠️ NO SE APLICA A CUOTAS
```

**Resultado:**
- Si NO está conciliado → retorna `0` (no aplica a cuotas)
- Si está conciliado → continúa con la aplicación

---

### **Función: `_conciliar_pago()`**

**Ubicación:** `backend/app/api/v1/endpoints/pagos_conciliacion.py` (líneas 48-121)

**Proceso:**
```python
# 1. Marcar pago como conciliado
pago.conciliado = True
pago.verificado_concordancia = "SI"
pago.fecha_conciliacion = datetime.now()
db.commit()

# 2. ✅ APLICAR PAGO A CUOTAS AUTOMÁTICAMENTE
if pago.prestamo_id:
    cuotas_completadas = aplicar_pago_a_cuotas(pago, db, usuario_sistema)
    logger.info(f"✅ {cuotas_completadas} cuota(s) completada(s)")
```

**Resultado:**
- Cuando se concilia → se aplica automáticamente a cuotas

---

## ⚠️ Casos Especiales

### **Caso 1: Pago Registrado pero NO Conciliado**

```
Estado:
- pagos.conciliado = False
- pagos.verificado_concordancia = 'NO'
- pagos.prestamo_id = 123 (existe)

Resultado:
- ❌ NO se aplica a cuotas
- cuotas.total_pagado NO se actualiza
- El pago queda "pendiente de conciliación"
```

---

### **Caso 2: Pago Conciliado pero SIN prestamo_id**

```
Estado:
- pagos.conciliado = True
- pagos.verificado_concordancia = 'SI'
- pagos.prestamo_id = NULL

Resultado:
- ❌ NO se aplica a cuotas (no tiene préstamo asociado)
- cuotas.total_pagado NO se actualiza
- El pago está conciliado pero no tiene préstamo
```

---

### **Caso 3: Pago Conciliado y CON prestamo_id**

```
Estado:
- pagos.conciliado = True
- pagos.verificado_concordancia = 'SI'
- pagos.prestamo_id = 123 (existe)

Resultado:
- ✅ SÍ se aplica a cuotas
- cuotas.total_pagado += monto_pagado
- Se actualiza estado de cuotas (PAGADO, PARCIAL, etc.)
```

---

## 📊 Tabla Resumen: Estados y Aplicación a Cuotas

| Estado del Pago | `conciliado` | `verificado_concordancia` | `prestamo_id` | ¿Se aplica a cuotas? |
|-----------------|--------------|---------------------------|---------------|----------------------|
| Registrado | `False` | `'NO'` | `123` | ❌ NO |
| Registrado sin préstamo | `False` | `'NO'` | `NULL` | ❌ NO |
| Conciliado | `True` | `'SI'` | `123` | ✅ SÍ |
| Conciliado sin préstamo | `True` | `'SI'` | `NULL` | ❌ NO |
| Parcialmente conciliado | `False` | `'SI'` | `123` | ✅ SÍ (verificado_concordancia='SI') |

---

## ✅ Confirmación Final

**Regla de Negocio Implementada:**

1. ✅ Los pagos se registran en `pagos` con `monto_pagado`
2. ✅ Los pagos NO se aplican a cuotas inmediatamente
3. ✅ Solo cuando el pago se concilia (`conciliado = True` o `verificado_concordancia = 'SI'`), se aplica a cuotas
4. ✅ La aplicación a cuotas es automática cuando se concilia
5. ✅ Si el pago NO está conciliado, NO se puede actualizar la tabla `cuotas`

---

**Última actualización:** 2025-11-06

