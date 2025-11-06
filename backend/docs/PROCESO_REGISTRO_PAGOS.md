# 📋 Proceso de Registro de Pagos (Manual y Masivo)

> **Documento actualizado con nombres reales de tablas y campos**  
> Última actualización: 2025-11-06

---

## 🎯 Resumen Ejecutivo

**Cuando se registra un pago (manual o masivo), se crea un registro en la tabla `pagos` con el campo `pagos.monto_pagado`.**

**IMPORTANTE:** 
1. El pago **DEBE estar relacionado con un préstamo** (`pagos.prestamo_id`). Si no se proporciona `prestamo_id` en el request, el sistema lo busca automáticamente por `cedula` y `estado = 'APROBADO'` (tanto en pago manual como en carga masiva).
2. **Los pagos SOLO se aplican a cuotas cuando están conciliados** (`pagos.conciliado = True` o `pagos.verificado_concordancia = 'SI'`). Si el pago NO está conciliado, NO se puede actualizar la tabla `cuotas`.
3. Cuando un pago se concilia, se aplica automáticamente a las cuotas correspondientes, actualizando `cuotas.total_pagado`.

---

## 📊 Flujo Completo: Registro de Pago

### **FASE 1: CREAR REGISTRO EN TABLA `pagos`**

#### **1.1. Pago Manual**

**Endpoint:** `POST /api/v1/pagos/`  
**Archivo:** `backend/app/api/v1/endpoints/pagos.py`  
**Función:** `crear_pago()` (líneas 596-669)

**Proceso:**
```python
# 1. Validar que el cliente existe
cliente = db.query(Cliente).filter(Cliente.cedula == pago_data.cedula).first()

# 2. ✅ BUSCAR PRÉSTAMO AUTOMÁTICAMENTE si no viene en el request
prestamo_id = pago_data.prestamo_id
if not prestamo_id:
    prestamo = db.query(Prestamo).filter(
        Prestamo.cedula == pago_data.cedula,
        Prestamo.estado == "APROBADO"
    ).first()
    if prestamo:
        prestamo_id = prestamo.id  # ✅ ASIGNADO AUTOMÁTICAMENTE

# 3. Crear registro en tabla pagos
pago_dict = pago_data.model_dump()
pago_dict["prestamo_id"] = prestamo_id  # Del request o encontrado automáticamente
nuevo_pago = Pago(**pago_dict)  # Incluye monto_pagado y prestamo_id
db.add(nuevo_pago)
db.commit()  # ⭐ SE GUARDA EN pagos.monto_pagado

# 4. ⚠️ NO APLICAR PAGO A CUOTAS AQUÍ
# Los pagos solo se aplican a cuotas cuando están conciliados (conciliado=True o verificado_concordancia='SI')
# La aplicación a cuotas se hará automáticamente cuando el pago se concilie
```

**Campos que se guardan en `pagos`:**
- `pagos.monto_pagado` = `pago_data.monto_pagado` (del request)
- `pagos.cedula` = `pago_data.cedula`
- `pagos.fecha_pago` = `pago_data.fecha_pago`
- `pagos.prestamo_id` = `pago_data.prestamo_id` (opcional)
- `pagos.numero_documento` = `pago_data.numero_documento`
- `pagos.conciliado` = `false` (default)
- `pagos.fecha_conciliacion` = `NULL` (default)
- `pagos.verificado_concordancia` = `'NO'` (default)
- `pagos.activo` = `true` (default)
- `pagos.usuario_registro` = `current_user.email`
- `pagos.fecha_registro` = `datetime.now()`

---

#### **1.2. Pago Masivo (Carga desde Excel)**

**Endpoint:** `POST /api/v1/pagos/cargar-masiva`  
**Archivo:** `backend/app/api/v1/endpoints/pagos_upload.py`  
**Función:** `_procesar_fila_pago()` (líneas 85-160)

**Proceso:**
```python
# 1. Leer datos del Excel
monto_pagado = Decimal(str(row["monto_pagado"]))
cedula = str(row["cedula"]).strip()
fecha_pago = datetime.strptime(str(row["fecha_pago"]), "%Y-%m-%d")
numero_documento = str(row["numero_documento"]).strip()

# 2. Verificar conciliación automática (si numero_documento ya existe)
pago_existente = db.query(Pago).filter(
    func.trim(Pago.numero_documento) == numero_documento_normalizado,
    Pago.activo.is_(True)
).first()

if pago_existente:
    conciliado = True
    fecha_conciliacion = datetime.now()

# 3. ✅ BUSCAR PRÉSTAMO AUTOMÁTICAMENTE por cédula
prestamo = db.query(Prestamo).filter(
    Prestamo.cedula == cedula, 
    Prestamo.estado == "APROBADO"
).first()

# 4. Crear registro en tabla pagos
nuevo_pago = Pago(
    monto_pagado=monto_pagado,  # ⭐ SE GUARDA EN pagos.monto_pagado
    cedula=cedula,
    prestamo_id=prestamo.id if prestamo else None,  # ✅ ASIGNADO AUTOMÁTICAMENTE
    fecha_pago=fecha_pago,
    numero_documento=numero_documento_normalizado,
    conciliado=conciliado,  # ✅ Puede ser True si ya existe
    fecha_conciliacion=fecha_conciliacion,  # ✅ Puede tener valor si ya existe
    activo=True,
    ...
)
db.add(nuevo_pago)
db.commit()  # ⭐ SE GUARDA EN pagos.monto_pagado

# 5. Aplicar pago a cuotas (automático si tiene prestamo_id)
#    Se ejecuta después del commit en la función principal
```

**Campos que se guardan en `pagos`:**
- `pagos.monto_pagado` = `monto_pagado` (del Excel)
- `pagos.cedula` = `cedula` (del Excel)
- `pagos.fecha_pago` = `fecha_pago` (del Excel)
- `pagos.numero_documento` = `numero_documento` (del Excel)
- `pagos.conciliado` = `True` o `False` (según si ya existe)
- `pagos.fecha_conciliacion` = `datetime.now()` o `NULL` (según si ya existe)
- `pagos.activo` = `true`
- `pagos.usuario_registro` = `current_user.email`
- `pagos.fecha_registro` = `datetime.now()`

---

### **FASE 2: APLICAR PAGO A CUOTAS (Automático - Solo si está conciliado)**

**Función:** `aplicar_pago_a_cuotas()` (líneas 1251-1306)  
**Se ejecuta automáticamente cuando el pago se concilia**  
**⚠️ IMPORTANTE: Solo se ejecuta si:**
- `pago.prestamo_id` NO es NULL
- **Y** `pago.conciliado = True` **O** `pago.verificado_concordancia = 'SI'`

**Proceso:**
```python
# 1. ✅ VERIFICAR QUE EL PAGO ESTÉ CONCILIADO
if not pago.conciliado:
    verificado_ok = getattr(pago, "verificado_concordancia", None) == "SI"
    if not verificado_ok:
        logger.warning("Pago NO está conciliado. No se aplicará a cuotas.")
        return 0  # ⚠️ NO SE APLICA A CUOTAS

# 2. Validar que el pago tiene prestamo_id
validacion_ok, _ = _verificar_prestamo_y_cedula(pago, db)
#    Si prestamo_id es NULL → retorna False y NO aplica a cuotas

# 3. Verificar que el préstamo existe y la cédula coincide
if not pago.prestamo_id:
    logger.warning("Pago no tiene prestamo_id. No se aplicará a cuotas.")
    return 0  # ⚠️ NO SE APLICA A CUOTAS

# 3. Obtener cuotas pendientes (ordenadas por fecha_vencimiento)
cuotas = _obtener_cuotas_pendientes(db, pago.prestamo_id)

# 4. Aplicar pago iterativamente a cuotas
cuotas_completadas, saldo_restante = _aplicar_pago_a_cuotas_iterativas(
    cuotas, pago.monto_pagado, pago.fecha_pago, fecha_hoy, db
)

# 5. Si sobra saldo, aplicar a siguiente cuota
if saldo_restante > Decimal("0.00"):
    cuotas_completadas += _aplicar_exceso_a_siguiente_cuota(...)

# 6. Commit a la base de datos
db.commit()
```

**Función interna:** `_aplicar_monto_a_cuota()` (líneas 1055-1124)
```python
# ACTUALIZAR total_pagado (SUMA ACUMULATIVA)
cuota.total_pagado += monto_aplicar  # ⭐ SE ACTUALIZA cuotas.total_pagado
cuota.capital_pagado += capital_aplicar
cuota.interes_pagado += interes_aplicar
```

---

## 📋 Tabla Resumen: Proceso Completo

| Fase | Tabla | Operación | Campo Afectado | Valor | Condición |
|------|-------|-----------|----------------|-------|-----------|
| **1** | `pagos` | INSERT | `pagos.monto_pagado` | `pago_data.monto_pagado` | Crear pago (manual o masivo) |
| **1** | `pagos` | INSERT | `pagos.cedula` | `pago_data.cedula` | Crear pago |
| **1** | `pagos` | INSERT | `pagos.fecha_pago` | `pago_data.fecha_pago` | Crear pago |
| **1** | `pagos` | INSERT | `pagos.prestamo_id` | `pago_data.prestamo_id` (opcional) | Crear pago |
| **1** | `pagos` | INSERT | `pagos.numero_documento` | `pago_data.numero_documento` | Crear pago |
| **1** | `pagos` | INSERT | `pagos.conciliado` | `false` (default) o `true` (si ya existe) | Crear pago |
| **1** | `pagos` | INSERT | `pagos.fecha_conciliacion` | `NULL` o `datetime.now()` (si ya existe) | Crear pago |
| **1** | `pagos` | INSERT | `pagos.verificado_concordancia` | `'NO'` (default) | Crear pago |
| **1** | `pagos` | INSERT | `pagos.activo` | `true` (default) | Crear pago |
| **1** | `pagos` | INSERT | `pagos.usuario_registro` | `current_user.email` | Crear pago |
| **1** | `pagos` | INSERT | `pagos.fecha_registro` | `datetime.now()` | Crear pago |
| **2** | `cuotas` | UPDATE | `cuotas.total_pagado` | `+= monto_aplicar` | Aplicar pago a cuotas (automático) |
| **2** | `cuotas` | UPDATE | `cuotas.capital_pagado` | `+= capital_aplicar` | Aplicar pago a cuotas |
| **2** | `cuotas` | UPDATE | `cuotas.interes_pagado` | `+= interes_aplicar` | Aplicar pago a cuotas |
| **2** | `cuotas` | UPDATE | `cuotas.fecha_pago` | `fecha_pago` (si es primera vez) | Aplicar pago a cuotas |
| **2** | `cuotas` | UPDATE | `cuotas.dias_morosidad` | Recalculado automáticamente | Aplicar pago a cuotas |
| **2** | `cuotas` | UPDATE | `cuotas.monto_morosidad` | Recalculado automáticamente | Aplicar pago a cuotas |
| **2** | `cuotas` | UPDATE | `cuotas.estado` | `'PAGADO'`, `'PARCIAL'`, `'PENDIENTE'`, etc. | Aplicar pago a cuotas |

---

## ✅ Confirmación: Dónde se Almacena el Monto del Pago

### **Tabla `pagos` - Registro Individual**

| Campo | Tipo | Descripción | Cuándo se establece |
|-------|------|-------------|---------------------|
| `pagos.monto_pagado` | `numeric(12,2)` | **Monto del pago individual** | Al crear el pago (manual o masivo) |
| `pagos.id` | `integer` | ID único del pago | Auto-generado |
| `pagos.cedula` | `character varying(20)` | Cédula del cliente | Del request/Excel |
| `pagos.fecha_pago` | `timestamp without time zone` | Fecha y hora del pago | Del request/Excel |
| `pagos.prestamo_id` | `integer` | ID del préstamo (opcional) | Del request/Excel o búsqueda automática |
| `pagos.numero_documento` | `character varying` | Número de documento bancario | Del request/Excel |
| `pagos.conciliado` | `boolean` | Estado de conciliación | `false` (default) o `true` (si ya existe) |
| `pagos.fecha_conciliacion` | `timestamp without time zone` | Fecha de conciliación | `NULL` (default) o `datetime.now()` (si ya existe) |
| `pagos.verificado_concordancia` | `character varying(2)` | Verificación de concordancia | `'NO'` (default) |
| `pagos.activo` | `boolean` | Estado activo | `true` (default) |

**Característica:** Cada pago crea un **nuevo registro** en la tabla `pagos`. Múltiples pagos = múltiples registros.

---

### **Tabla `cuotas` - Suma Acumulativa**

| Campo | Tipo | Descripción | Cuándo se actualiza |
|-------|------|-------------|---------------------|
| `cuotas.total_pagado` | `numeric(12,2)` | **SUMA ACUMULATIVA de todos los pagos** | Automáticamente al aplicar pago a cuotas |
| `cuotas.capital_pagado` | `numeric(12,2)` | Suma acumulativa de capital | Automáticamente al aplicar pago |
| `cuotas.interes_pagado` | `numeric(12,2)` | Suma acumulativa de interés | Automáticamente al aplicar pago |

**Característica:** Se **incrementa** (`+=`) cada vez que se aplica un pago. Un solo campo por cuota que acumula todos los pagos.

---

## 🔄 Flujo Detallado: Pago Manual

```
1. Usuario ingresa datos del pago en frontend
   └─ monto_pagado: 500.00
   └─ cedula: "12345678"
   └─ fecha_pago: "2025-11-15"
   └─ numero_documento: "DOC-001"

2. Frontend envía POST /api/v1/pagos/
   └─ Body: { "monto_pagado": 500.00, "cedula": "12345678", ... }

3. Backend: crear_pago()
   └─ Validar cliente existe
   └─ Crear registro en tabla pagos:
      └─ pagos.monto_pagado = 500.00  ⭐ SE GUARDA AQUÍ
      └─ pagos.cedula = "12345678"
      └─ pagos.fecha_pago = "2025-11-15 00:00:00"
      └─ pagos.numero_documento = "DOC-001"
      └─ pagos.conciliado = false
      └─ pagos.activo = true
   └─ db.commit()  ✅ PAGO GUARDADO EN pagos.monto_pagado

4. Backend: aplicar_pago_a_cuotas() (automático)
   └─ Buscar préstamo por cedula
   └─ Obtener cuotas pendientes
   └─ Aplicar pago a cuotas:
      └─ Cuota 1: cuotas.total_pagado += 300.00
      └─ Cuota 2: cuotas.total_pagado += 200.00
   └─ db.commit()  ✅ CUOTAS ACTUALIZADAS

5. Respuesta al frontend
   └─ Pago creado exitosamente
   └─ Cuotas actualizadas
```

---

## 🔄 Flujo Detallado: Pago Masivo (Excel)

```
1. Usuario sube archivo Excel con pagos
   └─ Fila 1: monto_pagado=200.00, cedula="12345678", numero_documento="DOC-001"
   └─ Fila 2: monto_pagado=150.00, cedula="12345678", numero_documento="DOC-002"
   └─ Fila 3: monto_pagado=150.00, cedula="87654321", numero_documento="DOC-003"

2. Frontend envía POST /api/v1/pagos/cargar-masiva
   └─ File: pagos.xlsx

3. Backend: procesar_archivo_pagos()
   └─ Leer Excel fila por fila
   └─ Para cada fila: _procesar_fila_pago()

4. Backend: _procesar_fila_pago() (por cada fila)
   └─ Leer: monto_pagado, cedula, fecha_pago, numero_documento
   └─ Verificar si numero_documento ya existe:
      └─ Si existe: conciliado = True, fecha_conciliacion = datetime.now()
      └─ Si no existe: conciliado = False, fecha_conciliacion = NULL
   └─ Crear registro en tabla pagos:
      └─ pagos.monto_pagado = 200.00  ⭐ SE GUARDA AQUÍ
      └─ pagos.cedula = "12345678"
      └─ pagos.numero_documento = "DOC-001"
      └─ pagos.conciliado = True/False (según si ya existe)
   └─ db.commit()  ✅ PAGO GUARDADO EN pagos.monto_pagado

5. Backend: aplicar_pago_a_cuotas() (automático, si tiene prestamo_id)
   └─ Aplicar pago a cuotas correspondientes
   └─ Actualizar cuotas.total_pagado

6. Respuesta al frontend
   └─ Total procesados: 3
   └─ Exitosos: 3
   └─ Errores: 0
```

---

## ⚠️ Diferencias Clave: Manual vs Masivo

| Aspecto | Pago Manual | Pago Masivo |
|---------|-------------|-------------|
| **Endpoint** | `POST /api/v1/pagos/` | `POST /api/v1/pagos/cargar-masiva` |
| **Archivo** | `pagos.py` | `pagos_upload.py` |
| **Función** | `crear_pago()` | `_procesar_fila_pago()` |
| **Datos** | JSON del request | Excel (filas) |
| **Búsqueda automática de préstamo** | ✅ SÍ (busca por `cedula` y `estado = 'APROBADO'` si no viene en request) | ✅ SÍ (busca por `cedula` y `estado = 'APROBADO'`) |
| **Asignación de prestamo_id** | Del request o automática (`prestamo.id if prestamo else None`) | Automática (`prestamo.id if prestamo else None`) |
| **Conciliación automática** | ❌ NO | ✅ SÍ (si `numero_documento` ya existe) |
| **Validación cliente** | ✅ SÍ (debe existir) | ✅ SÍ (debe existir) |
| **Aplicación a cuotas** | ✅ Automática (solo si está conciliado y tiene `prestamo_id`) | ✅ Automática (solo si está conciliado y tiene `prestamo_id`) |
| **Campo donde se guarda** | `pagos.monto_pagado` | `pagos.monto_pagado` |

---

## ⚠️ IMPORTANTE: Relación con Préstamo

### **Regla de Negocio:**
**El pago DEBE estar relacionado con un préstamo Y estar conciliado para aplicarse a cuotas.**

**Condiciones para aplicar pago a cuotas:**
1. ✅ `pagos.prestamo_id` NO es NULL
2. ✅ `pagos.conciliado = True` **O** `pagos.verificado_concordancia = 'SI'`
3. ✅ El préstamo existe y la cédula coincide

### **Comportamiento Actual:**

#### **Pago Manual:**
- `prestamo_id` puede venir en el request (opcional en schema)
- ✅ **Si NO viene `prestamo_id` → SÍ se busca automáticamente** por `cedula` y `estado = 'APROBADO'`
- Si encuentra préstamo → asigna `prestamo_id = prestamo.id`
- Si NO encuentra → `prestamo_id = None` (no se aplica a cuotas)
- ⚠️ **NO se aplica a cuotas inmediatamente** - Solo cuando se concilia (`conciliado = True` o `verificado_concordancia = 'SI'`)

#### **Pago Masivo:**
- ✅ **SÍ busca automáticamente** el préstamo por `cedula` y `estado = 'APROBADO'`
- Si encuentra préstamo → asigna `prestamo_id = prestamo.id`
- Si NO encuentra → `prestamo_id = None` (no se aplica a cuotas)
- ⚠️ **NO se aplica a cuotas inmediatamente** - Solo cuando se concilia (`conciliado = True` o `verificado_concordancia = 'SI'`)

### **Código de Búsqueda Automática (Pago Manual y Carga Masiva):**
```python
# Buscar préstamo del cliente automáticamente si no viene en request
prestamo_id = pago_data.prestamo_id  # Del request (puede ser None)
if not prestamo_id:
    prestamo = db.query(Prestamo).filter(
        Prestamo.cedula == cedula, 
        Prestamo.estado == "APROBADO"
    ).first()
    if prestamo:
        prestamo_id = prestamo.id  # ✅ ASIGNADO AUTOMÁTICAMENTE
```

### **Validación en Aplicación a Cuotas:**
```python
def aplicar_pago_a_cuotas(pago: Pago, db: Session, current_user: User):
    # ✅ VERIFICAR QUE EL PAGO ESTÉ CONCILIADO
    if not pago.conciliado:
        verificado_ok = getattr(pago, "verificado_concordancia", None) == "SI"
        if not verificado_ok:
            logger.warning("Pago NO está conciliado. No se aplicará a cuotas.")
            return 0  # ⚠️ NO SE APLICA A CUOTAS
    
    # Verificar prestamo_id
    if not pago.prestamo_id:
        logger.warning("Pago no tiene prestamo_id. No se aplicará a cuotas.")
        return 0  # ⚠️ NO SE APLICA A CUOTAS
    # ... resto de validación y aplicación
```

---

## ✅ Confirmación Final

**Cuando se paga manual o masivamente:**
1. ✅ Se crea un registro en la tabla `pagos`
2. ✅ El monto se guarda en `pagos.monto_pagado` (campo individual)
3. ✅ **El pago DEBE estar relacionado con un préstamo** (`pagos.prestamo_id`)
   - **Pago manual:** Se busca automáticamente por `cedula` y `estado = 'APROBADO'` si no viene en el request
   - **Carga masiva:** Se busca automáticamente por `cedula` y `estado = 'APROBADO'`
4. ⚠️ **El pago NO se aplica a cuotas inmediatamente** - Solo cuando se concilia
5. ✅ **Cuando el pago se concilia** (`conciliado = True` o `verificado_concordancia = 'SI'`), se aplica automáticamente a cuotas
6. ✅ Se actualiza `cuotas.total_pagado` (suma acumulativa) automáticamente cuando el pago está conciliado

**Campos clave:**
- `pagos.monto_pagado` = **REGISTRO INDIVIDUAL** de cada pago
- `pagos.prestamo_id` = **DEBE estar relacionado** para aplicar a cuotas
- `cuotas.total_pagado` = **SUMA ACUMULATIVA** de todos los pagos aplicados

---

## 🔍 Validación del Proceso en Backend

### **Pago Manual (`crear_pago`):**
- ✅ Valida que cliente existe
- ✅ **SÍ busca automáticamente** el préstamo por `cedula` y `estado = 'APROBADO'` si no viene en request
- ✅ Crea registro en `pagos` con `monto_pagado` y `prestamo_id` (del request o encontrado automáticamente)
- ⚠️ **NO llama a `aplicar_pago_a_cuotas()` inmediatamente** - Solo cuando se concilia
- ⚠️ Si NO se encuentra préstamo → `prestamo_id = None` → NO se aplica a cuotas

### **Pago Masivo (`_procesar_fila_pago`):**
- ✅ Valida que cliente existe
- ✅ **SÍ busca automáticamente** el préstamo por `cedula` y `estado = 'APROBADO'`
- ✅ Crea registro en `pagos` con `monto_pagado` y `prestamo_id` (si se encontró)
- ⚠️ **NO llama a `aplicar_pago_a_cuotas()` inmediatamente** - Solo cuando se concilia
- ⚠️ Si NO se encuentra préstamo → `prestamo_id = None` → NO se aplica a cuotas

### **Conciliación de Pago (`_conciliar_pago` en `pagos_conciliacion.py`):**
- ✅ Marca `pago.conciliado = True` y `pago.verificado_concordancia = 'SI'`
- ✅ **Llama a `aplicar_pago_a_cuotas()` automáticamente** cuando se concilia
- ✅ Aplica el pago a las cuotas correspondientes

### **Aplicación a Cuotas (`aplicar_pago_a_cuotas`):**
- ✅ **Verifica que el pago esté conciliado** (`conciliado = True` o `verificado_concordancia = 'SI'`)
- ✅ Verifica que `pago.prestamo_id` NO sea NULL
- ✅ Verifica que el préstamo existe
- ✅ Verifica que `pago.cedula == prestamo.cedula`
- ✅ Obtiene cuotas pendientes del préstamo
- ✅ Aplica pago a cuotas (más antiguas primero)
- ✅ Actualiza `cuotas.total_pagado` (suma acumulativa)

---

**Última actualización:** 2025-11-06

