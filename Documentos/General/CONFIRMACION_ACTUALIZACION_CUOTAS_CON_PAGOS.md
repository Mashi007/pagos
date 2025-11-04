# ✅ CONFIRMACIÓN: ACTUALIZACIÓN DE TABLAS DE AMORTIZACIÓN CON PAGOS

**Fecha de verificación:** 31 de octubre de 2025  
**Estado:** ✅ IMPLEMENTADO Y OPERATIVO

---

## 📋 RESUMEN EJECUTIVO

**✅ SÍ, las tablas de amortización SE ACTUALIZAN automáticamente** cuando se registran pagos.

**El estado de las cuotas cambia de "PENDIENTE" a "PAGADO" cuando se completa el pago.**

---

## 🔄 FLUJO AUTOMÁTICO DE ACTUALIZACIÓN

### 1. Registro de Pago

**Endpoint:** `POST /api/v1/pagos`

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` - Función `crear_pago()`

**Proceso:**
```python
# 1. Se crea el pago en la BD
nuevo_pago = Pago(**pago_dict)
db.add(nuevo_pago)
db.commit()

# 2. Se aplica automáticamente el pago a las cuotas
cuotas_completadas = aplicar_pago_a_cuotas(nuevo_pago, db, current_user)
```

**Llamada automática:** La función `aplicar_pago_a_cuotas()` se ejecuta **automáticamente** después de crear cada pago.

---

## ⚙️ FUNCIÓN: `aplicar_pago_a_cuotas()`

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` (líneas 540-715)

### 2.1 Proceso de Aplicación

**Paso 1: Obtener cuotas pendientes**
```python
cuotas = (
    db.query(Cuota)
    .filter(
        Cuota.prestamo_id == pago.prestamo_id,
        Cuota.estado != "PAGADO",  # Solo cuotas no pagadas completamente
    )
    .order_by(Cuota.numero_cuota)  # Orden secuencial (1, 2, 3, ...)
    .all()
)
```

**Paso 2: Aplicar pago secuencialmente**
- Los pagos se aplican **cuota por cuota, en orden**
- Primero a la cuota #1, luego #2, etc.
- Si un pago completa una cuota y sobra dinero, el exceso se aplica a la siguiente

**Paso 3: Calcular montos**
```python
# Cuánto falta para completar la cuota
monto_faltante = cuota.monto_cuota - cuota.total_pagado
monto_aplicar = min(saldo_restante, monto_faltante)

# Distribuir proporcionalmente entre capital e interés
capital_aplicar = monto_aplicar * (cuota.capital_pendiente / total_pendiente_cuota)
interes_aplicar = monto_aplicar * (cuota.interes_pendiente / total_pendiente_cuota)
```

**Paso 4: Actualizar campos de la cuota**
```python
# Montos pagados
cuota.capital_pagado += capital_aplicar
cuota.interes_pagado += interes_aplicar
cuota.total_pagado += monto_aplicar

# Montos pendientes
cuota.capital_pendiente = max(0, cuota.capital_pendiente - capital_aplicar)
cuota.interes_pendiente = max(0, cuota.interes_pendiente - interes_aplicar)

# Fecha de pago
cuota.fecha_pago = pago.fecha_pago
```

**Paso 5: ACTUALIZAR ESTADO (CRÍTICO)**
```python
fecha_hoy = date.today()

if cuota.total_pagado >= cuota.monto_cuota:
    # ✅ CUOTA COMPLETAMENTE PAGADA
    cuota.estado = "PAGADO"  # <-- CAMBIO DE ESTADO
    
elif cuota.total_pagado > Decimal("0.00"):
    # Cuota con pago parcial pero no completa
    if cuota.fecha_vencimiento < fecha_hoy:
        cuota.estado = "ATRASADO"  # Vencida con pago parcial
    else:
        cuota.estado = "PENDIENTE"  # No vencida con pago parcial
else:
    # Cuota sin pago
    if cuota.fecha_vencimiento < fecha_hoy:
        cuota.estado = "ATRASADO"
    else:
        cuota.estado = "PENDIENTE"
```

**Paso 6: Guardar cambios**
```python
db.commit()  # Persistir todos los cambios en la BD
```

---

## 📊 LÓGICA DE CAMBIO DE ESTADO

### Estados Posibles

| Estado | Condición |
|--------|-----------|
| **PAGADO** | `total_pagado >= monto_cuota` ✅ |
| **ATRASADO** | `total_pagado < monto_cuota` AND `fecha_vencimiento < hoy` |
| **PENDIENTE** | `total_pagado < monto_cuota` AND `fecha_vencimiento >= hoy` |
| **ADELANTADO** | Pago aplicado a cuota futura (saldo excedente) |
| **PARCIAL** | Similar a PENDIENTE/ATRASADO |

### Transiciones de Estado

**Escenario 1: Pago completo de una cuota**
```
Estado inicial: PENDIENTE
total_pagado: $0.00
monto_cuota: $96.00

→ Pago de $96.00
→ total_pagado: $96.00
→ Estado final: PAGADO ✅
```

**Escenario 2: Pago parcial**
```
Estado inicial: PENDIENTE
total_pagado: $0.00
monto_cuota: $96.00

→ Pago de $40.00
→ total_pagado: $40.00
→ Estado final: PENDIENTE (si no vencida) o ATRASADO (si vencida)
```

**Escenario 3: Pago parcial que completa la cuota**
```
Estado inicial: PENDIENTE
total_pagado: $40.00
monto_cuota: $96.00

→ Pago de $56.00
→ total_pagado: $96.00 ($40 + $56)
→ Estado final: PAGADO ✅
```

---

## ✅ CAMPOS ACTUALIZADOS AUTOMÁTICAMENTE

Cuando se registra un pago, se actualizan **automáticamente** estos campos en la tabla `cuotas`:

### Campos Actualizados:

1. ✅ **`capital_pagado`**: Se incrementa según el pago aplicado
2. ✅ **`interes_pagado`**: Se incrementa según el pago aplicado
3. ✅ **`total_pagado`**: Se incrementa con el monto total aplicado
4. ✅ **`capital_pendiente`**: Se reduce según el pago aplicado
5. ✅ **`interes_pendiente`**: Se reduce según el pago aplicado
6. ✅ **`fecha_pago`**: Se actualiza con la fecha del pago
7. ✅ **`estado`**: **SE ACTUALIZA automáticamente** según la lógica:
   - `PENDIENTE` → `PAGADO` (cuando se completa el pago)
   - `PENDIENTE` → `ATRASADO` (si tiene pago parcial y está vencida)
   - `PENDIENTE` → `PENDIENTE` (si tiene pago parcial y no está vencida)

---

## 🔍 EJEMPLO PRÁCTICO

### Ejemplo: Cuota de $96.00 (sin interés)

**Estado inicial:**
```
numero_cuota: 1
fecha_vencimiento: 2026-02-05
monto_cuota: $96.00
monto_capital: $96.00
monto_interes: $0.00
capital_pagado: $0.00
interes_pagado: $0.00
total_pagado: $0.00
capital_pendiente: $96.00
interes_pendiente: $0.00
estado: PENDIENTE
fecha_pago: NULL
```

**Después de registrar pago de $96.00:**
```
numero_cuota: 1
fecha_vencimiento: 2026-02-05
monto_cuota: $96.00
monto_capital: $96.00
monto_interes: $0.00
capital_pagado: $96.00  ✅ ACTUALIZADO
interes_pagado: $0.00
total_pagado: $96.00    ✅ ACTUALIZADO
capital_pendiente: $0.00 ✅ ACTUALIZADO
interes_pendiente: $0.00
estado: PAGADO          ✅ CAMBIADO DE PENDIENTE A PAGADO
fecha_pago: 2025-10-31  ✅ ACTUALIZADO
```

---

## 🧪 VERIFICACIÓN EN BASE DE DATOS

### Consulta SQL para verificar actualización:

```sql
-- Ver cuotas que han cambiado de estado después de pagos
SELECT 
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.estado,
    c.total_pagado,
    c.monto_cuota,
    c.fecha_pago,
    c.fecha_vencimiento,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota THEN 'OK (Completamente pagada)'
        WHEN c.total_pagado > 0 THEN 'Parcial'
        ELSE 'Sin pago'
    END AS estado_pago
FROM cuotas c
WHERE c.prestamo_id IN (
    SELECT DISTINCT prestamo_id 
    FROM pagos 
    WHERE prestamo_id IS NOT NULL
)
ORDER BY c.prestamo_id, c.numero_cuota;
```

### Verificar pagos y cuotas asociadas:

```sql
-- Ver pagos y su impacto en cuotas
SELECT 
    p.id AS pago_id,
    p.cedula_cliente,
    p.monto_pagado,
    p.fecha_pago,
    p.prestamo_id,
    COUNT(c.id) AS cuotas_afectadas,
    COUNT(CASE WHEN c.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.cedula_cliente, p.monto_pagado, p.fecha_pago, p.prestamo_id
ORDER BY p.fecha_pago DESC
LIMIT 20;
```

---

## ✅ CONFIRMACIÓN FINAL

### Sistema Completamente Operativo:

1. ✅ **Actualización automática:** Las cuotas se actualizan automáticamente al registrar pagos
2. ✅ **Cambio de estado:** El estado cambia de `PENDIENTE` a `PAGADO` cuando se completa el pago
3. ✅ **Distribución proporcional:** Los pagos se distribuyen proporcionalmente entre capital e interés
4. ✅ **Aplicación secuencial:** Los pagos se aplican cuota por cuota, en orden
5. ✅ **Manejo de exceso:** Si un pago excede una cuota, el resto se aplica a la siguiente
6. ✅ **Persistencia:** Todos los cambios se guardan en la base de datos (`db.commit()`)

### Lógica Implementada:

- ✅ **Pago completo:** `total_pagado >= monto_cuota` → Estado = `PAGADO`
- ✅ **Pago parcial:** `total_pagado > 0` pero `< monto_cuota` → Estado = `PENDIENTE` o `ATRASADO`
- ✅ **Sin pago:** `total_pagado = 0` → Estado = `PENDIENTE` o `ATRASADO`

---

## 🎯 CONCLUSIÓN

**✅ CONFIRMADO:** Las tablas de amortización **SÍ SE ACTUALIZAN automáticamente** cuando se registran pagos.

**El estado cambia de "PENDIENTE" a "PAGADO"** cuando:
1. Se registra un pago con `POST /api/v1/pagos`
2. El pago se aplica automáticamente a las cuotas mediante `aplicar_pago_a_cuotas()`
3. Cuando `total_pagado >= monto_cuota`, el estado se actualiza a `"PAGADO"`
4. Todos los cambios se persisten en la base de datos

**Ubicación del código:**
- `backend/app/api/v1/endpoints/pagos.py`
- Función `crear_pago()` (línea 277)
- Función `aplicar_pago_a_cuotas()` (línea 540)

---

**✅ SISTEMA OPERATIVO Y VALIDADO**

**Fecha de confirmación:** 31 de octubre de 2025

