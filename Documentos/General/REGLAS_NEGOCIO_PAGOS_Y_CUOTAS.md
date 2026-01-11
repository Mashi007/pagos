# 🔒 REGLAS DE NEGOCIO: TABLAS PAGOS Y CUOTAS

> **Documento completo de reglas de negocio críticas**
> Última actualización: 2026-01-08

---

## 📋 TABLA 1: `pagos`

### **Estructura Principal**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `id` | Integer | ✅ Sí | Primary Key |
| `cedula` | String(20) | ✅ Sí | Cédula del cliente (indexado) |
| `cliente_id` | Integer | ❌ No | FK a `clientes.id` |
| `prestamo_id` | Integer | ❌ No | FK a `prestamos.id` (indexado) |
| `numero_cuota` | Integer | ❌ No | Número de cuota asociada (opcional) |
| `fecha_pago` | DateTime | ✅ Sí | Fecha de pago (manual) |
| `fecha_registro` | DateTime | ✅ Sí | Fecha de registro (automático, indexado) |
| `monto_pagado` | Numeric(12,2) | ✅ Sí | Monto del pago |
| `numero_documento` | String(100) | ✅ Sí | Número de documento (indexado) |
| `institucion_bancaria` | String(100) | ❌ No | Institución bancaria |
| `conciliado` | Boolean | ✅ Sí | Default: `False` |
| `fecha_conciliacion` | DateTime | ❌ No | Fecha de conciliación |
| `estado` | String(20) | ✅ Sí | Default: `"PAGADO"` (indexado) |
| `activo` | Boolean | ✅ Sí | Default: `True` |
| `usuario_registro` | String(100) | ✅ Sí | Email del usuario que registró |
| `verificado_concordancia` | String(2) | ✅ Sí | Default: `"NO"` (SI/NO) |

---

## 🎯 REGLAS DE NEGOCIO: TABLA `pagos`

### **REGLA 1: Registro de Pago**

**Descripción:** Cuando se registra un pago (manual o masivo), se crea un registro en `pagos`.

**Campos obligatorios:**
- ✅ `cedula` (requerido)
- ✅ `fecha_pago` (requerido, no puede ser futura)
- ✅ `monto_pagado` (requerido, debe ser > 0 y < $1,000,000)
- ✅ `numero_documento` (requerido)
- ✅ `usuario_registro` (requerido)

**Valores por defecto:**
- `conciliado` = `False`
- `verificado_concordancia` = `"NO"`
- `estado` = `"PAGADO"`
- `activo` = `True`
- `fecha_registro` = `datetime.now()`

**Validaciones:**
1. ✅ El cliente debe existir (`Cliente.cedula` debe existir)
2. ✅ `monto_pagado` debe ser > 0 y < $1,000,000
3. ✅ `fecha_pago` no puede ser futura
4. ✅ `numero_documento` se normaliza (trim espacios)

---

### **REGLA 2: Búsqueda Automática de Préstamo**

**Descripción:** Si no se proporciona `prestamo_id` en el request, el sistema lo busca automáticamente.

**Lógica:**
```python
if not prestamo_id:
    prestamo = db.query(Prestamo).filter(
        Prestamo.cedula == cedula,
        Prestamo.estado == "APROBADO"
    ).first()
    
    if prestamo:
        prestamo_id = prestamo.id  # ✅ ASIGNADO AUTOMÁTICAMENTE
    else:
        prestamo_id = None  # ⚠️ NO se encontró préstamo
```

**Resultado:**
- Si encuentra préstamo → `pagos.prestamo_id` = ID del préstamo
- Si NO encuentra → `pagos.prestamo_id` = `NULL` (no se aplica a cuotas)

---

### **REGLA 3: Conciliación de Pagos (CRÍTICA)**

**Descripción:** Los pagos SOLO se aplican a cuotas cuando están conciliados.

**Condiciones obligatorias para aplicar a cuotas:**
1. ✅ `pagos.conciliado = True` **O** `pagos.verificado_concordancia = 'SI'`
2. ✅ `pagos.prestamo_id` NO es NULL
3. ✅ El préstamo existe y la cédula coincide

**Si alguna condición NO se cumple, el pago NO se aplica a cuotas.**

**Estados de conciliación:**

| Estado | `conciliado` | `verificado_concordancia` | `prestamo_id` | ¿Se aplica a cuotas? |
|--------|--------------|--------------------------|---------------|----------------------|
| Registrado | `False` | `'NO'` | `123` | ❌ NO |
| Registrado sin préstamo | `False` | `'NO'` | `NULL` | ❌ NO |
| Conciliado | `True` | `'SI'` | `123` | ✅ SÍ |
| Conciliado sin préstamo | `True` | `'SI'` | `NULL` | ❌ NO |
| Parcialmente conciliado | `False` | `'SI'` | `123` | ✅ SÍ |

---

### **REGLA 4: Estados del Pago**

**Descripción:** El estado del pago se actualiza DESPUÉS de conciliar y aplicar a cuotas.

**Valores permitidos:**
- `"PAGADO"` - Default al crear
- `"PENDIENTE"` - Pago registrado pero no conciliado
- `"PARCIAL"` - Pago aplicado pero no completó ninguna cuota completamente
- `"ADELANTADO"` - Pago que cubre cuotas futuras

**Lógica de actualización:**
```python
# DESPUÉS de aplicar a cuotas:
if cuotas_completadas > 0:
    pago.estado = "PAGADO"  # Completó al menos una cuota
elif pago.prestamo_id:
    pago.estado = "PARCIAL"  # No completó ninguna cuota completamente
```

**IMPORTANTE:**
- ⚠️ El estado NO se actualiza al crear el pago
- ✅ El estado se actualiza DESPUÉS de conciliar y aplicar a cuotas

---

### **REGLA 5: Soft Delete (Eliminación Lógica)**

**Descripción:** Los pagos NO se eliminan físicamente, se marcan como inactivos.

**Campo:**
- `activo` = `False` (eliminación lógica)

**Comportamiento:**
- ✅ Los pagos inactivos (`activo = False`) NO aparecen en consultas normales
- ✅ Los pagos inactivos se mantienen para auditoría

---

## 📋 TABLA 2: `cuotas`

### **Estructura Principal**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `id` | Integer | ✅ Sí | Primary Key |
| `prestamo_id` | Integer | ✅ Sí | FK a `prestamos.id` (indexado) |
| `numero_cuota` | Integer | ✅ Sí | Número de cuota (1, 2, 3, ...) |
| `fecha_vencimiento` | Date | ✅ Sí | Fecha límite de pago (indexado) |
| `fecha_pago` | Date | ❌ No | Fecha real cuando se pagó |
| `monto_cuota` | Numeric(12,2) | ✅ Sí | Monto total programado de la cuota |
| `monto_capital` | Numeric(12,2) | ✅ Sí | Monto de capital de esta cuota |
| `monto_interes` | Numeric(12,2) | ✅ Sí | Monto de interés de esta cuota |
| `saldo_capital_inicial` | Numeric(12,2) | ✅ Sí | Saldo de capital al inicio del período |
| `saldo_capital_final` | Numeric(12,2) | ✅ Sí | Saldo de capital al fin del período |
| `capital_pagado` | Numeric(12,2) | ✅ Sí | Default: `0.00` |
| `interes_pagado` | Numeric(12,2) | ✅ Sí | Default: `0.00` |
| `mora_pagada` | Numeric(12,2) | ✅ Sí | Default: `0.00` |
| `total_pagado` | Numeric(12,2) | ✅ Sí | Default: `0.00` |
| `capital_pendiente` | Numeric(12,2) | ✅ Sí | Capital que falta pagar |
| `interes_pendiente` | Numeric(12,2) | ✅ Sí | Interés que falta pagar |
| `dias_mora` | Integer | ✅ Sí | Default: `0` |
| `monto_mora` | Numeric(12,2) | ✅ Sí | Default: `0.00` |
| `dias_morosidad` | Integer | ✅ Sí | Default: `0` (indexado) |
| `monto_morosidad` | Numeric(12,2) | ✅ Sí | Default: `0.00` (indexado) |
| `estado` | String(20) | ✅ Sí | Default: `"PENDIENTE"` (indexado) |

---

## 🎯 REGLAS DE NEGOCIO: TABLA `cuotas`

### **REGLA 1: Generación de Cuotas**

**Descripción:** Las cuotas se generan automáticamente cuando un préstamo se aprueba.

**Condiciones:**
1. ✅ El préstamo debe tener estado `"APROBADO"`
2. ✅ El préstamo debe tener `fecha_base_calculo`
3. ✅ El préstamo debe tener `numero_cuotas` > 0
4. ✅ El préstamo debe tener `total_financiamiento` > 0

**Proceso:**
- Se eliminan cuotas existentes (si las hay)
- Se generan `numero_cuotas` registros en `cuotas`
- Cada cuota tiene `numero_cuota` único (1, 2, 3, ..., numero_cuotas)
- Las fechas se calculan según `modalidad_pago` (MENSUAL, QUINCENAL, SEMANAL)

---

### **REGLA 2: Cálculo de Cuotas (Método Francés)**

**Descripción:** Las cuotas se calculan usando el método francés (cuota fija).

**Fórmulas:**
```python
# Cuota fija (igual para todas las cuotas)
monto_cuota = total_financiamiento / numero_cuotas

# Para cada cuota:
monto_interes = saldo_capital * tasa_mensual
monto_capital = monto_cuota - monto_interes
saldo_capital = saldo_capital - monto_capital
```

**Características:**
- ✅ Cuota constante: Todas las cuotas tienen el mismo monto (`monto_cuota`)
- ✅ Interés decreciente: El interés se calcula sobre el saldo pendiente
- ✅ Capital creciente: Como la cuota es fija y el interés disminuye, el capital aumenta
- ✅ Saldo decreciente: El saldo de capital se reduce progresivamente

---

### **REGLA 3: Aplicación de Pagos a Cuotas**

**Descripción:** Los pagos se aplican a las cuotas cuando están conciliados.

**Orden de aplicación:**
1. ✅ **Cuotas más antiguas primero** (ordenadas por `fecha_vencimiento`)
2. ✅ **Solo cuotas pendientes** (`estado != "PAGADO"`)
3. ✅ **Una cuota a la vez** hasta agotar el monto del pago
4. ✅ **Si sobra monto**, se aplica a la siguiente cuota pendiente

**Actualización de campos:**
```python
# Cuando se aplica un pago a una cuota:
cuota.capital_pagado += capital_aplicar
cuota.interes_pagado += interes_aplicar
cuota.total_pagado += monto_aplicar
cuota.capital_pendiente -= capital_aplicar
cuota.interes_pendiente -= interes_aplicar
cuota.fecha_pago = fecha_pago  # Si es el primer pago
```

---

### **REGLA 4: Estados de Cuotas**

**Descripción:** El estado de la cuota se actualiza automáticamente según el monto pagado Y la conciliación de pagos.

**Valores permitidos:**
- `"PENDIENTE"` - Default al crear, no se ha pagado nada O pagada pero no conciliada
- `"PARCIAL"` - Se ha pagado algo pero no está completa (`total_pagado < monto_cuota`) y está vencida
- `"PAGADO"` - Cuota completamente pagada (`total_pagado >= monto_cuota`) Y todos los pagos conciliados
- `"ATRASADO"` - Cuota vencida y no pagada completamente (`total_pagado = 0`)
- `"ADELANTADO"` - Pago aplicado a cuota futura (exceso de pago)

**Lógica de actualización:**
```python
def _actualizar_estado_cuota(cuota, fecha_hoy):
    # Verificar si todos los pagos están conciliados
    todos_conciliados = verificar_pagos_conciliados_cuota(cuota.id)
    
    # Regla 1: Cuota completamente pagada
    if cuota.total_pagado >= cuota.monto_cuota:
        if todos_conciliados:
            cuota.estado = "PAGADO"  # ✅ Solo si todos los pagos están conciliados
        else:
            cuota.estado = "PENDIENTE"  # ⚠️ Pagada pero no conciliada
        return True
    
    # Regla 2: Cuota parcialmente pagada
    if cuota.total_pagado > 0:
        if cuota.fecha_vencimiento < fecha_hoy:
            cuota.estado = "PARCIAL"  # Vencida con pago parcial
        else:
            if es_exceso:
                cuota.estado = "ADELANTADO"  # Pago adelantado
            else:
                cuota.estado = "PENDIENTE"  # No vencida con pago parcial
        return False
    
    # Regla 3: Cuota sin pagos
    if cuota.fecha_vencimiento < fecha_hoy:
        cuota.estado = "ATRASADO"  # Vencida sin pagos
    else:
        cuota.estado = "PENDIENTE"  # No vencida sin pagos
    return False
```

**IMPORTANTE:**
- ⚠️ Una cuota solo se marca como `"PAGADO"` si `total_pagado >= monto_cuota` Y todos los pagos están conciliados
- ⚠️ Si `total_pagado >= monto_cuota` pero hay pagos sin conciliar → `estado = "PENDIENTE"`

---

### **REGLA 5: Cálculo de Mora**

**Descripción:** La mora se calcula automáticamente cuando una cuota está vencida.

**Condiciones para calcular mora:**
1. ✅ `fecha_vencimiento < fecha_hoy` (cuota vencida)
2. ✅ `total_pagado < monto_cuota` (no está completamente pagada)

**Cálculo:**
```python
dias_mora = (fecha_hoy - fecha_vencimiento).days
saldo_mora = capital_pendiente + interes_pendiente
monto_mora = saldo_mora * tasa_mora_diaria * dias_mora
```

**Campos actualizados:**
- `dias_mora` = días de atraso
- `monto_mora` = monto de mora calculado
- `dias_morosidad` = días de atraso (indexado)
- `monto_morosidad` = `monto_cuota - total_pagado` (indexado)

---

### **REGLA 6: Proporción Capital/Interés en Pagos**

**Descripción:** Cuando se aplica un pago, se distribuye proporcionalmente entre capital e interés.

**Cálculo:**
```python
# Calcular proporción según lo que falta pagar
total_faltante = cuota.capital_pendiente + cuota.interes_pendiente

if total_faltante > 0:
    proporcion_capital = cuota.capital_pendiente / total_faltante
    proporcion_interes = cuota.interes_pendiente / total_faltante
    
    capital_aplicar = monto_aplicar * proporcion_capital
    interes_aplicar = monto_aplicar * proporcion_interes
else:
    # Si ya está pagada, aplicar todo a capital
    capital_aplicar = monto_aplicar
    interes_aplicar = Decimal("0.00")
```

---

### **REGLA 7: Cuota Vencida**

**Descripción:** Una cuota está vencida si cumple ambas condiciones.

**Criterio:**
```python
cuota_vencida = (
    cuota.fecha_vencimiento < fecha_hoy AND
    cuota.total_pagado < cuota.monto_cuota
)
```

**Comportamiento:**
- ✅ Si está vencida → `estado = "ATRASADO"`
- ✅ Se calcula mora automáticamente
- ✅ Se actualiza `dias_mora` y `monto_mora`

---

### **REGLA 8: Cuota Completamente Pagada**

**Descripción:** Una cuota está completamente pagada cuando el total pagado es igual o mayor al monto de la cuota.

**Criterio:**
```python
cuota_pagada = cuota.total_pagado >= cuota.monto_cuota
```

**Comportamiento:**
- ✅ `estado = "PAGADO"`
- ✅ `fecha_pago` se establece con la fecha del último pago que completó la cuota
- ✅ No se procesa en futuras aplicaciones de pagos (`estado != "PAGADO"`)

---

### **REGLA 9: Pagos Parciales**

**Descripción:** Los pagos pueden ser parciales (menor al monto de la cuota).

**Comportamiento:**
- ✅ Un pago puede ser menor al monto de una cuota
- ✅ Se aplica el monto disponible a la cuota
- ✅ La cuota queda en estado `"PARCIAL"` si `total_pagado < monto_cuota`
- ✅ La cuota queda en estado `"PAGADO"` si `total_pagado >= monto_cuota`

**Ejemplo:**
```
Cuota 1: monto_cuota = $100.00, total_pagado = $0.00
Pago 1: monto_pagado = $30.00
Resultado: total_pagado = $30.00, estado = "PARCIAL"

Pago 2: monto_pagado = $70.00
Resultado: total_pagado = $100.00, estado = "PAGADO"
```

---

### **REGLA 10: Pagos con Exceso**

**Descripción:** Si un pago cubre completamente una cuota y sobra, el exceso se aplica a la siguiente.

**Comportamiento:**
```python
# Ejemplo:
Cuota 1: monto_cuota = $100.00, total_pagado = $0.00
Cuota 2: monto_cuota = $100.00, total_pagado = $0.00

Pago: monto_pagado = $150.00

Resultado:
- Cuota 1: total_pagado = $100.00, estado = "PAGADO"
- Cuota 2: total_pagado = $50.00, estado = "PARCIAL"
- Saldo restante: $0.00
```

**Lógica:**
1. Se aplica el monto a la primera cuota pendiente
2. Si sobra, se aplica a la siguiente cuota pendiente
3. Se repite hasta agotar el monto del pago

---

## 🔄 RELACIÓN ENTRE PAGOS Y CUOTAS

### **Flujo Completo:**

```
1. REGISTRO DE PAGO
   └─ Se crea registro en tabla `pagos`
   └─ pagos.conciliado = False
   └─ ⚠️ NO se aplica a cuotas todavía

2. CONCILIACIÓN DE PAGO
   └─ pagos.conciliado = True
   └─ ✅ AHORA SÍ se aplica a cuotas automáticamente

3. APLICACIÓN A CUOTAS
   └─ Se obtienen cuotas pendientes (ordenadas por fecha_vencimiento)
   └─ Se aplica monto a cada cuota hasta agotar el pago
   └─ Se actualizan campos: total_pagado, capital_pagado, interes_pagado
   └─ Se actualiza estado de cuotas: PAGADO, PARCIAL, ATRASADO

4. ACTUALIZACIÓN DE ESTADOS
   └─ Cuotas: estado se actualiza según total_pagado vs monto_cuota
   └─ Pagos: estado se actualiza según cuántas cuotas completó
```

---

## ✅ RESUMEN DE REGLAS CRÍTICAS

### **Tabla PAGOS:**

1. ✅ Los pagos SOLO se aplican a cuotas cuando están conciliados
2. ✅ Si `prestamo_id` no viene en el request, se busca automáticamente
3. ✅ El estado del pago se actualiza DESPUÉS de aplicar a cuotas
4. ✅ Los pagos NO se eliminan físicamente (soft delete)

### **Tabla CUOTAS:**

1. ✅ Las cuotas se generan automáticamente cuando un préstamo se aprueba
2. ✅ Las cuotas se calculan usando el método francés (cuota fija)
3. ✅ Los pagos se aplican a las cuotas más antiguas primero
4. ✅ El estado se actualiza automáticamente según el monto pagado
5. ✅ La mora se calcula automáticamente cuando una cuota está vencida
6. ✅ Una cuota está pagada cuando `total_pagado >= monto_cuota`
7. ✅ Si un pago sobra, el exceso se aplica a la siguiente cuota

---

**Última actualización:** 2026-01-08
