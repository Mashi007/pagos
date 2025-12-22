# 🔗 Regla de Vinculación de Pagos a Cuotas Después de Conciliación

> **Regla crítica del sistema**
> Última actualización: 2025-01-27

---

## 🎯 Regla Principal

**Los pagos se vinculan y aplican a cuotas AUTOMÁTICAMENTE cuando se concilian.**

### **Condiciones Obligatorias para Aplicación:**

1. ✅ `pagos.conciliado = True` **O** `pagos.verificado_concordancia = 'SI'`
2. ✅ `pagos.prestamo_id` NO es NULL
3. ✅ El préstamo existe y la cédula del pago coincide con la cédula del préstamo
4. ✅ El préstamo tiene cuotas pendientes (estado != 'PAGADO')

**Si alguna de estas condiciones NO se cumple, el pago NO se aplica a cuotas.**

---

## 📋 Flujo Completo de Vinculación

### **FASE 1: Conciliación del Pago**

```
1. Usuario concilia pago (manual, Excel, o automático)
   └─ pagos.conciliado = True
   └─ pagos.verificado_concordancia = 'SI'
   └─ pagos.fecha_conciliacion = datetime.now()
   └─ db.commit()  ← Se guarda primero el pago conciliado
```

### **FASE 2: Aplicación Automática a Cuotas**

```
2. ✅ Se llama automáticamente a aplicar_pago_a_cuotas()
   
   PASO 2.1: Verificación de Conciliación
   └─ Verifica: pago.conciliado == True O verificado_concordancia == 'SI'
   └─ Si NO está conciliado → retorna 0 (NO se aplica)
   
   PASO 2.2: Verificación de Préstamo
   └─ Verifica: pago.prestamo_id existe
   └─ Verifica: préstamo existe en BD
   └─ Verifica: cédula del pago == cédula del préstamo
   └─ Si alguna falla → retorna 0 (NO se aplica)
   
   PASO 2.3: Obtener Cuotas Pendientes
   └─ Busca cuotas del préstamo con estado != 'PAGADO'
   └─ Ordena por: fecha_vencimiento ASC, numero_cuota ASC
   └─ (Las cuotas más antiguas primero)
   
   PASO 2.4: Aplicar Pago a Cuotas (Iterativo)
   └─ Recorre cuotas en orden (más antigua primero)
   └─ Para cada cuota:
      ├─ Calcula: monto_faltante = monto_cuota - total_pagado
      ├─ Calcula: monto_aplicar = min(saldo_restante, monto_faltante)
      ├─ Actualiza: cuota.total_pagado += monto_aplicar
      ├─ Actualiza: cuota.capital_pagado += proporción_capital
      ├─ Actualiza: cuota.interes_pagado += proporción_interes
      ├─ Actualiza: cuota.capital_pendiente -= proporción_capital
      ├─ Actualiza: cuota.interes_pendiente -= proporción_interes
      ├─ Si total_pagado >= monto_cuota → marca como completada
      └─ saldo_restante -= monto_aplicar
   
   PASO 2.5: Aplicar Exceso (si sobra)
   └─ Si saldo_restante > 0 después de aplicar a todas las cuotas
   └─ Busca siguiente cuota pendiente (más antigua)
   └─ Aplica el exceso a esa cuota
   
   PASO 2.6: Actualizar Estados
   └─ Actualiza estado de cada cuota según reglas:
      ├─ PAGADO: total_pagado >= monto_cuota Y todos los pagos conciliados
      ├─ PENDIENTE: total_pagado >= monto_cuota PERO NO todos conciliados
      ├─ PARCIAL: total_pagado > 0 pero < monto_cuota y vencida
      ├─ ATRASADO: total_pagado = 0 y vencida
      └─ ADELANTADO: total_pagado > 0 pero < monto_cuota y no vencida
   
   PASO 2.7: Actualizar Estado del Pago
   └─ Si completó al menos 1 cuota → pago.estado = 'PAGADO'
   └─ Si no completó ninguna pero tiene préstamo → pago.estado = 'PARCIAL'
   └─ db.commit()  ← Se guardan todos los cambios
```

---

## 🔍 Detalles de Implementación

### **Función: `_conciliar_pago()`**

**Ubicación:** `backend/app/api/v1/endpoints/pagos_conciliacion.py` (líneas 48-149)

**Proceso:**
```python
# 1. Marcar pago como conciliado
pago.conciliado = True
pago.fecha_conciliacion = datetime.now()
pago.verificado_concordancia = "SI"
db.commit()  # ✅ Se guarda primero

# 2. ✅ APLICAR PAGO A CUOTAS AUTOMÁTICAMENTE
if pago.prestamo_id:
    cuotas_completadas = aplicar_pago_a_cuotas(pago, db, usuario_sistema)
    # Esto actualiza cuotas.total_pagado automáticamente
```

### **Función: `aplicar_pago_a_cuotas()`**

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` (líneas 1256-1346)

**Validaciones:**
```python
# ✅ VERIFICAR QUE EL PAGO ESTÉ CONCILIADO
if not pago.conciliado:
    verificado_ok = getattr(pago, "verificado_concordancia", None) == "SI"
    if not verificado_ok:
        return 0  # ⚠️ NO SE APLICA A CUOTAS

# ✅ VERIFICAR PRÉSTAMO Y CÉDULA
validacion_ok, _ = _verificar_prestamo_y_cedula(pago, db)
if not validacion_ok:
    return 0  # ⚠️ NO SE APLICA A CUOTAS
```

**Orden de Aplicación:**
```python
# Obtener cuotas pendientes ordenadas por fecha_vencimiento
cuotas = _obtener_cuotas_pendientes(db, pago.prestamo_id)
# Orden: fecha_vencimiento ASC, numero_cuota ASC
# (Las cuotas más antiguas primero)
```

### **Función: `_aplicar_pago_a_cuotas_iterativas()`**

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` (líneas 1228-1253)

**Lógica:**
```python
for cuota in cuotas:  # Ordenadas por fecha_vencimiento ASC
    monto_faltante = cuota.monto_cuota - cuota.total_pagado
    monto_aplicar = min(saldo_restante, monto_faltante)
    
    # Actualizar cuota
    cuota.total_pagado += monto_aplicar
    cuota.capital_pagado += capital_aplicar
    cuota.interes_pagado += interes_aplicar
    # ... más actualizaciones
    
    saldo_restante -= monto_aplicar
    
    if saldo_restante <= 0:
        break  # Ya no hay más saldo para aplicar
```

---

## 📊 Reglas de Orden de Aplicación

### **1. Orden por Fecha de Vencimiento**

**Regla:** Los pagos se aplican a las cuotas más antiguas primero.

**Criterio de Ordenamiento:**
```sql
ORDER BY fecha_vencimiento ASC, numero_cuota ASC
```

**Ejemplo:**
```
Préstamo con 12 cuotas:
- Cuota 1: vence 2025-01-10 → Se aplica PRIMERO
- Cuota 2: vence 2025-02-10 → Se aplica SEGUNDO
- Cuota 3: vence 2025-03-10 → Se aplica TERCERO
...
```

### **2. Aplicación Proporcional**

**Regla:** El monto se distribuye proporcionalmente entre capital e interés.

**Cálculo:**
```python
proporcion_capital = (monto_cuota.capital / monto_cuota.total) * monto_aplicar
proporcion_interes = (monto_cuota.interes / monto_cuota.total) * monto_aplicar
```

### **3. Manejo de Exceso**

**Regla:** Si un pago cubre completamente una cuota y sobra, el exceso se aplica a la siguiente cuota pendiente.

**Ejemplo:**
```
Pago: $500
Cuota 1: $300 (faltante) → Se aplica $300, sobra $200
Cuota 2: $300 (faltante) → Se aplica $200 del exceso
Resultado: Cuota 1 completada, Cuota 2 con $200 aplicados
```

---

## ⚠️ Casos Especiales

### **Caso 1: Pago Conciliado pero Préstamo sin Cuotas**

```
Estado:
- pagos.conciliado = True
- pagos.prestamo_id = 123
- Préstamo no tiene cuotas pendientes

Resultado:
- ⚠️ NO se aplica a cuotas (no hay cuotas pendientes)
- El pago queda conciliado pero sin aplicar
```

### **Caso 2: Pago Mayor que Todas las Cuotas Pendientes**

```
Estado:
- Pago: $10,000
- Cuotas pendientes: $3,000 total

Resultado:
- ✅ Se aplica a todas las cuotas pendientes
- ⚠️ Sobra $7,000 (se queda como exceso)
- Las cuotas quedan completamente pagadas
```

### **Caso 3: Múltiples Pagos para Misma Cuota**

```
Estado:
- Cuota 1: $500 (monto_cuota)
- Pago 1: $200 (conciliado) → total_pagado = $200
- Pago 2: $300 (conciliado) → total_pagado = $500

Resultado:
- ✅ Cuota 1 completada (total_pagado = $500)
- ✅ Estado cambia a "PAGADO" (si todos los pagos conciliados)
```

---

## 📋 Tabla Resumen: Flujo de Vinculación

| Paso | Acción | Condición | Resultado |
|------|--------|-----------|-----------|
| 1 | Conciliar pago | Usuario concilia | `pagos.conciliado = True` |
| 2 | Verificar conciliación | `conciliado = True` | Continúa |
| 3 | Verificar préstamo | `prestamo_id != NULL` | Continúa |
| 4 | Verificar cédula | `cedula_pago == cedula_prestamo` | Continúa |
| 5 | Obtener cuotas | `estado != 'PAGADO'` | Lista de cuotas pendientes |
| 6 | Aplicar a cuotas | Orden: `fecha_vencimiento ASC` | `cuotas.total_pagado += monto` |
| 7 | Actualizar estados | Según reglas | `cuotas.estado` actualizado |
| 8 | Guardar cambios | `db.commit()` | Cambios persistidos |

---

## ✅ Confirmación Final

**Regla de Negocio Implementada:**

1. ✅ Los pagos se concilian primero (`pagos.conciliado = True`)
2. ✅ Después de conciliar, se aplican AUTOMÁTICAMENTE a cuotas
3. ✅ Se aplican a cuotas más antiguas primero (por `fecha_vencimiento`)
4. ✅ Se actualiza `cuotas.total_pagado` automáticamente
5. ✅ Se actualiza `cuotas.estado` según reglas de negocio
6. ✅ Si sobra monto, se aplica a la siguiente cuota pendiente

**Última actualización:** 2025-01-27
