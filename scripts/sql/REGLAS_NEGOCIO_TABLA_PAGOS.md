# 🔒 REGLAS DE NEGOCIO: TABLA PAGOS

> **Documento de reglas de negocio críticas**
> Última actualización: 2026-01-08

---

## 📋 TABLA: `pagos`

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
| `documento_nombre` | String(255) | ❌ No | Nombre del documento adjunto |
| `documento_tipo` | String(10) | ❌ No | Tipo: PNG, JPG, PDF |
| `documento_tamaño` | Integer | ❌ No | Tamaño en bytes |
| `documento_ruta` | String(500) | ❌ No | Ruta del documento |
| `conciliado` | Boolean | ✅ Sí | Default: `False` |
| `fecha_conciliacion` | DateTime | ❌ No | Fecha de conciliación |
| `estado` | String(20) | ✅ Sí | Default: `"PAGADO"` (indexado) |
| `activo` | Boolean | ✅ Sí | Default: `True` |
| `notas` | Text | ❌ No | Notas adicionales |
| `usuario_registro` | String(100) | ✅ Sí | Email del usuario que registró |
| `fecha_actualizacion` | DateTime | ✅ Sí | Auto-actualizado |
| `verificado_concordancia` | String(2) | ✅ Sí | Default: `"NO"` (SI/NO) |

---

## 🎯 REGLAS DE NEGOCIO PRINCIPALES

### **REGLA 1: Registro de Pago**

**Descripción:** Cuando se registra un pago (manual o masivo), se crea un registro en `pagos`.

**Campos obligatorios:**
- ✅ `cedula` (requerido)
- ✅ `fecha_pago` (requerido, no puede ser futura)
- ✅ `monto_pagado` (requerido, debe ser > 0)
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
# Si prestamo_id NO viene en el request:
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

**Aplicación:**
- ✅ Pago manual (`POST /api/v1/pagos/`)
- ✅ Pago masivo (`POST /api/v1/pagos/cargar-masiva`)

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

**Proceso de conciliación:**
```python
# 1. Marcar pago como conciliado
pago.conciliado = True
pago.verificado_concordancia = "SI"
pago.fecha_conciliacion = datetime.now()
db.commit()

# 2. ✅ APLICAR PAGO A CUOTAS AUTOMÁTICAMENTE
if pago.prestamo_id:
    cuotas_completadas = aplicar_pago_a_cuotas(pago, db, usuario_sistema)
```

---

### **REGLA 4: Aplicación de Pagos a Cuotas**

**Descripción:** Cuando un pago está conciliado, se aplica automáticamente a las cuotas correspondientes.

**Orden de aplicación:**
1. ✅ Se aplica a las cuotas más antiguas primero (por `fecha_vencimiento`)
2. ✅ Solo procesa cuotas con `estado != "PAGADO"`
3. ✅ Una cuota está "ATRASADO" hasta que esté completamente pagada (`total_pagado >= monto_cuota`)
4. ✅ Solo cuando `total_pagado >= monto_cuota`, se marca como "PAGADO"
5. ✅ Si un pago cubre completamente una cuota y sobra, el exceso se aplica a la siguiente

**Validación antes de aplicar:**
```python
# ✅ VERIFICAR QUE EL PAGO ESTÉ CONCILIADO
if not pago.conciliado:
    verificado_ok = getattr(pago, "verificado_concordancia", None) == "SI"
    if not verificado_ok:
        return 0  # ⚠️ NO SE APLICA A CUOTAS
```

**Actualización de cuotas:**
- `cuotas.total_pagado` += `monto_pagado`
- `cuotas.capital_pagado` += `monto_capital`
- `cuotas.interes_pagado` += `monto_interes`
- `cuotas.estado` se actualiza según el monto pagado

---

### **REGLA 5: Estados del Pago**

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
# Si no tiene prestamo_id, mantener estado por defecto
```

**IMPORTANTE:**
- ⚠️ El estado NO se actualiza al crear el pago
- ✅ El estado se actualiza DESPUÉS de conciliar y aplicar a cuotas

---

### **REGLA 6: Validación de Cédula**

**Descripción:** La cédula del pago debe coincidir con la cédula del préstamo.

**Validación:**
```python
def _verificar_prestamo_y_cedula(pago: Pago, db: Session):
    if not pago.prestamo_id:
        return False, "No tiene préstamo asociado"
    
    prestamo = db.query(Prestamo).filter(Prestamo.id == pago.prestamo_id).first()
    if not prestamo:
        return False, "Préstamo no encontrado"
    
    if prestamo.cedula != pago.cedula:
        return False, "Cédula del pago no coincide con cédula del préstamo"
    
    return True, "Validación exitosa"
```

**Resultado:**
- Si la cédula NO coincide → NO se aplica a cuotas
- Si la cédula coincide → Continúa con la aplicación

---

### **REGLA 7: Pagos Parciales**

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

### **REGLA 8: Pagos con Exceso**

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

### **REGLA 9: Auditoría de Pagos**

**Descripción:** Todos los cambios en pagos se registran en la tabla `pago_auditoria`.

**Eventos auditados:**
- ✅ Creación de pago (`CREATE`)
- ✅ Actualización de pago (`UPDATE`)
- ✅ Conciliación de pago (`CONCILIAR`)
- ✅ Eliminación de pago (`DELETE`)

**Campos auditados:**
- `pago_id` - ID del pago modificado
- `usuario` - Email del usuario que realizó la acción
- `accion` - Tipo de acción (CREATE, UPDATE, CONCILIAR, DELETE)
- `campo_modificado` - Campo que se modificó
- `valor_anterior` - Valor anterior del campo
- `valor_nuevo` - Valor nuevo del campo
- `fecha_cambio` - Fecha y hora del cambio
- `observaciones` - Notas adicionales

---

### **REGLA 10: Soft Delete (Eliminación Lógica)**

**Descripción:** Los pagos NO se eliminan físicamente, se marcan como inactivos.

**Campo:**
- `activo` = `False` (eliminación lógica)

**Comportamiento:**
- ✅ Los pagos inactivos (`activo = False`) NO aparecen en consultas normales
- ✅ Los pagos inactivos se mantienen para auditoría
- ✅ Solo se pueden restaurar manualmente cambiando `activo = True`

---

## 📊 FLUJO COMPLETO: Registro → Conciliación → Aplicación

### **FASE 1: Registro de Pago**

```
1. Usuario registra pago (manual o masivo)
   └─ Se crea registro en tabla pagos
   └─ pagos.monto_pagado = monto del pago
   └─ pagos.prestamo_id = encontrado automáticamente o del request
   └─ pagos.conciliado = False (default)
   └─ pagos.verificado_concordancia = 'NO' (default)
   └─ pagos.estado = 'PAGADO' (default)

2. ⚠️ NO se aplica a cuotas todavía
   └─ El pago está registrado pero NO conciliado
   └─ cuotas.total_pagado NO se actualiza
```

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
   └─ cuotas.estado se actualiza (PAGADO, PARCIAL, etc.)
   └─ pagos.estado se actualiza (PAGADO, PARCIAL, etc.)
```

---

## ⚠️ CASOS ESPECIALES

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

## ✅ VALIDACIONES Y RESTRICCIONES

### **Validaciones al Crear Pago:**

1. ✅ Cliente debe existir (`Cliente.cedula` debe existir)
2. ✅ `monto_pagado` debe ser > 0 y < $1,000,000
3. ✅ `fecha_pago` no puede ser futura
4. ✅ `numero_documento` es requerido (se normaliza con trim)
5. ✅ `cedula` es requerida
6. ✅ `usuario_registro` es requerido

### **Validaciones al Aplicar a Cuotas:**

1. ✅ Pago debe estar conciliado (`conciliado = True` o `verificado_concordancia = 'SI'`)
2. ✅ Pago debe tener `prestamo_id` (no NULL)
3. ✅ Préstamo debe existir
4. ✅ Cédula del pago debe coincidir con cédula del préstamo
5. ✅ Debe haber cuotas pendientes (`estado != "PAGADO"`)

---

## 📝 RESUMEN DE REGLAS CRÍTICAS

1. ✅ **Los pagos SOLO se aplican a cuotas cuando están conciliados**
2. ✅ **Si `prestamo_id` no viene en el request, se busca automáticamente**
3. ✅ **El estado del pago se actualiza DESPUÉS de aplicar a cuotas**
4. ✅ **Los pagos se aplican a las cuotas más antiguas primero**
5. ✅ **Si un pago sobra, el exceso se aplica a la siguiente cuota**
6. ✅ **Los pagos pueden ser parciales (menor al monto de la cuota)**
7. ✅ **Todos los cambios se registran en auditoría**
8. ✅ **Los pagos NO se eliminan físicamente (soft delete)**

---

**Última actualización:** 2026-01-08
