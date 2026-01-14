# 📍 DÓNDE SE COPIAN LOS PAGOS CONCILIADOS DESDE `pagos` A `cuotas`

> **Última actualización:** 2025-01-XX
> **Respuesta a:** "donde copias los pagos conciliados que vienen desde tabla pagos?"

---

## 🎯 RESPUESTA DIRECTA

Los pagos conciliados desde la tabla `pagos` se copian/aplican al campo **`total_pagado`** en la tabla `cuotas` mediante la función Python **`aplicar_pago_a_cuotas()`**.

**Ubicación del código:** `backend/app/api/v1/endpoints/pagos.py`

---

## 🔄 FLUJO COMPLETO DE APLICACIÓN

### **PASO 1: Conciliación del Pago**

**Archivo:** `backend/app/api/v1/endpoints/pagos_conciliacion.py`

**Función:** `_conciliar_pago()` (línea 48)

```python
# 1. Marcar pago como conciliado
pago.conciliado = True
pago.fecha_conciliacion = datetime.now()
pago.verificado_concordancia = "SI"
db.commit()  # ← Se guarda primero el pago conciliado

# 2. ✅ APLICAR PAGO A CUOTAS AUTOMÁTICAMENTE
if pago.prestamo_id:
    from app.api.v1.endpoints.pagos import aplicar_pago_a_cuotas
    usuario_sistema = db.query(User).first()
    cuotas_completadas = aplicar_pago_a_cuotas(pago, db, usuario_sistema)
```

**Resultado:** Cuando se concilia un pago, se llama automáticamente a `aplicar_pago_a_cuotas()`.

---

### **PASO 2: Validación de Conciliación**

**Archivo:** `backend/app/api/v1/endpoints/pagos.py`

**Función:** `aplicar_pago_a_cuotas()` (línea 1362)

```python
# ✅ VERIFICAR QUE EL PAGO ESTÉ CONCILIADO
if not pago.conciliado:
    verificado_ok = getattr(pago, "verificado_concordancia", None) == "SI"
    if not verificado_ok:
        logger.warning("Pago NO está conciliado. No se aplicará a cuotas.")
        return 0  # ⚠️ NO SE APLICA A CUOTAS
```

**Resultado:** Solo continúa si el pago está conciliado (`conciliado=True` o `verificado_concordancia='SI'`).

---

### **PASO 3: Obtención de Cuotas Pendientes**

**Función:** `_obtener_cuotas_pendientes()` (línea 1320)

```python
cuotas = (
    db.query(Cuota)
    .filter(
        Cuota.prestamo_id == prestamo_id,
        Cuota.estado != "PAGADO",
    )
    .order_by(Cuota.fecha_vencimiento, Cuota.numero_cuota)
    .all()
)
```

**Resultado:** Obtiene las cuotas pendientes ordenadas por fecha de vencimiento (más antiguas primero).

---

### **PASO 4: Aplicación Iterativa a Cuotas**

**Función:** `_aplicar_pago_a_cuotas_iterativas()` (línea 1334)

```python
for cuota in cuotas:
    if saldo_restante <= Decimal("0.00"):
        break
    
    monto_faltante = cuota.monto_cuota - cuota.total_pagado
    monto_aplicar = min(saldo_restante, monto_faltante)
    
    if monto_aplicar <= Decimal("0.00"):
        continue
    
    # ✅ AQUÍ SE APLICA EL MONTO A LA CUOTA
    if _aplicar_monto_a_cuota(cuota, monto_aplicar, fecha_pago, fecha_hoy, db):
        cuotas_completadas += 1
    
    saldo_restante -= monto_aplicar
```

**Resultado:** Itera sobre las cuotas y aplica el monto disponible a cada una.

---

### **PASO 5: ACTUALIZACIÓN DEL CAMPO `total_pagado` EN `cuotas`**

**Función:** `_aplicar_monto_a_cuota()` (línea 1210)

**⚠️ ESTA ES LA LÍNEA DONDE SE COPIA EL PAGO:**

```python
def _aplicar_monto_a_cuota(
    cuota,
    monto_aplicar: Decimal,
    fecha_pago: date,
    fecha_hoy: date,
    db: Session = None,
    es_exceso: bool = False,
) -> bool:
    # ... validaciones ...
    
    # ✅ AQUÍ SE ACTUALIZA total_pagado EN LA TABLA cuotas
    cuota.total_pagado += monto_aplicar  # ← LÍNEA 1233
    
    # También se actualiza fecha_pago si hay monto aplicado
    if monto_aplicar > Decimal("0.00"):
        cuota.fecha_pago = fecha_pago
    
    # Actualizar estado de la cuota
    return _actualizar_estado_cuota(cuota, fecha_hoy, db, es_exceso)
```

**📍 LÍNEA EXACTA:** `backend/app/api/v1/endpoints/pagos.py`, línea **1233**

```python
cuota.total_pagado += monto_aplicar
```

**Resultado:** El campo `total_pagado` en la tabla `cuotas` se incrementa con el monto del pago conciliado.

---

## 📊 RESUMEN DEL FLUJO

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuario concilia pago                                   │
│    └─ pagos.conciliado = True                              │
│    └─ pagos.fecha_conciliacion = datetime.now()            │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Se llama automáticamente aplicar_pago_a_cuotas()        │
│    └─ Verifica: pago.conciliado == True                    │
│    └─ Obtiene cuotas pendientes del préstamo               │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Itera sobre cuotas (más antiguas primero)              │
│    └─ Calcula monto_aplicar = min(saldo_restante, faltante)│
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Llama _aplicar_monto_a_cuota()                          │
│    └─ cuota.total_pagado += monto_aplicar  ← AQUÍ SE COPIA│
│    └─ cuota.fecha_pago = fecha_pago                        │
│    └─ Actualiza estado de cuota                           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Se guarda en base de datos                              │
│    └─ db.commit()                                          │
│    └─ cuotas.total_pagado ahora contiene el pago          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 VERIFICACIÓN EN BASE DE DATOS

Para verificar que los pagos conciliados se están copiando correctamente:

```sql
-- Ver pagos conciliados con su monto
SELECT 
    id,
    cedula,
    monto_pagado,
    conciliado,
    prestamo_id,
    fecha_pago
FROM public.pagos
WHERE conciliado = TRUE
ORDER BY fecha_pago DESC
LIMIT 10;

-- Ver cuotas con total_pagado (donde se copian los pagos)
SELECT 
    id,
    prestamo_id,
    numero_cuota,
    monto_cuota,
    total_pagado,  -- ← Este campo se actualiza con los pagos conciliados
    fecha_pago,
    estado
FROM public.cuotas
WHERE total_pagado > 0
ORDER BY prestamo_id, numero_cuota
LIMIT 20;

-- Verificar que la suma de pagos conciliados coincide con total_pagado
SELECT 
    c.prestamo_id,
    SUM(p.monto_pagado) as suma_pagos_conciliados,
    SUM(c.total_pagado) as suma_total_pagado_cuotas
FROM public.pagos p
JOIN public.cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.conciliado = TRUE
GROUP BY c.prestamo_id
ORDER BY c.prestamo_id
LIMIT 10;
```

---

## ⚠️ IMPORTANTE: CONDICIONES PARA QUE SE COPIE

Los pagos **SOLO se copian** a `cuotas.total_pagado` si se cumplen TODAS estas condiciones:

1. ✅ `pagos.conciliado = True` **O** `pagos.verificado_concordancia = 'SI'`
2. ✅ `pagos.prestamo_id` NO es NULL
3. ✅ El préstamo existe en la tabla `prestamos`
4. ✅ La cédula del pago coincide con la cédula del préstamo
5. ✅ Existen cuotas pendientes (`estado != 'PAGADO'`)

**Si alguna condición NO se cumple, el pago NO se copia a `cuotas`.**

---

## 📝 SCRIPT PARA APLICAR PAGOS CONCILIADOS PENDIENTES

Si hay pagos conciliados que no se aplicaron automáticamente, existe un script:

**Archivo:** `scripts/python/aplicar_pagos_conciliados_pendientes.py`

**Uso:**
```bash
$env:PYTHONPATH="backend"; python scripts/python/aplicar_pagos_conciliados_pendientes.py
```

Este script:
1. Identifica pagos conciliados con `prestamo_id`
2. Llama a `aplicar_pago_a_cuotas()` para cada uno
3. Actualiza `cuotas.total_pagado` con los montos de los pagos

---

## ✅ CONCLUSIÓN

**Los pagos conciliados se copian desde `pagos.monto_pagado` hacia `cuotas.total_pagado` en:**

- **Archivo:** `backend/app/api/v1/endpoints/pagos.py`
- **Función:** `_aplicar_monto_a_cuota()`
- **Línea exacta:** **1233**
- **Código:** `cuota.total_pagado += monto_aplicar`

Este proceso se ejecuta automáticamente cuando se concilia un pago, o manualmente mediante el script `aplicar_pagos_conciliados_pendientes.py`.
