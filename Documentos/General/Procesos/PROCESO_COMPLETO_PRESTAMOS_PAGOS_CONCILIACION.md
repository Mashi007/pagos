# 📋 Proceso Completo: Préstamos, Pagos y Conciliación

## Descripción Paso a Paso con Tablas y Campos Afectados

---

## 🎯 FASE 1: APROBACIÓN DE PRÉSTAMO

### **Paso 1.1: Cambio de Estado a "APROBADO"**

**Endpoint:** `POST /api/v1/prestamos/{prestamo_id}/cambiar-estado`

**Función:** `procesar_cambio_estado()` en `prestamos.py` (línea 145)

#### **Tabla: `prestamos`**

| Campo | Valor Anterior | Valor Nuevo | Descripción |
|-------|----------------|-------------|-------------|
| `estado` | `"DRAFT"` / `"EN_REVISION"` | `"APROBADO"` | Estado del préstamo |
| `usuario_aprobador` | `NULL` | `current_user.email` | Email del usuario que aprueba |
| `fecha_aprobacion` | `NULL` | `datetime.now()` | Fecha y hora de aprobación |
| `tasa_interes` | (valor anterior) | (nuevo valor si se proporciona) | Tasa de interés aplicada |
| `fecha_base_calculo` | `NULL` | (fecha proporcionada) | Fecha base para cálculo de cuotas |

**Código:**
```python
if nuevo_estado == "APROBADO":
    prestamo.usuario_aprobador = current_user.email
    prestamo.fecha_aprobacion = datetime.now()
    if tasa_interes:
        prestamo.tasa_interes = tasa_interes
    if fecha_base_calculo:
        prestamo.fecha_base_calculo = fecha_base_calculo
```

---

### **Paso 1.2: Generación de Tabla de Amortización**

**Función:** `generar_tabla_amortizacion()` en `prestamo_amortizacion_service.py` (línea 20)

**Condición:** Solo si `prestamo.fecha_base_calculo` está definida

#### **Tabla: `cuotas`**

**Se crean N registros** (donde N = `prestamo.numero_cuotas`)

**Campos inicializados para cada cuota:**

| Campo | Valor Inicial | Descripción |
|-------|---------------|-------------|
| `id` | `AUTO_INCREMENT` | ID único de la cuota |
| `prestamo_id` | `prestamo.id` | ID del préstamo asociado |
| `numero_cuota` | `1, 2, 3, ..., N` | Número secuencial de la cuota |
| `fecha_vencimiento` | `fecha_base + relativedelta(months=numero_cuota)` | Fecha de vencimiento calculada |
| `fecha_pago` | `NULL` | Fecha real de pago (inicialmente NULL) |
| `monto_cuota` | `prestamo.cuota_periodo` | Monto total de la cuota |
| `monto_capital` | `monto_cuota - monto_interes` | Monto de capital |
| `monto_interes` | `saldo_capital * tasa_mensual` | Monto de interés |
| `saldo_capital_inicial` | `saldo_capital` | Saldo inicial antes de la cuota |
| `saldo_capital_final` | `saldo_capital - monto_capital` | Saldo final después de la cuota |
| `capital_pagado` | `0.00` | Capital pagado (inicialmente 0) |
| `interes_pagado` | `0.00` | Interés pagado (inicialmente 0) |
| `mora_pagada` | `0.00` | Mora pagada (inicialmente 0) |
| `total_pagado` | `0.00` | Total pagado (inicialmente 0) |
| `capital_pendiente` | `monto_capital` | Capital pendiente |
| `interes_pendiente` | `monto_interes` | Interés pendiente |
| `dias_mora` | `NULL` | Días de mora (inicialmente NULL) |
| `monto_mora` | `NULL` | Monto de mora (inicialmente NULL) |
| `tasa_mora` | `NULL` | Tasa de mora (inicialmente NULL) |
| `estado` | `"PENDIENTE"` | Estado inicial de la cuota |
| `dias_morosidad` | `0` | Días de morosidad calculados |
| `monto_morosidad` | `0.00` | Monto de morosidad calculado |

**Código:**
```python
for numero_cuota in range(1, prestamo.numero_cuotas + 1):
    fecha_vencimiento = fecha_base + relativedelta(months=numero_cuota)
    monto_interes = saldo_capital * tasa_mensual
    monto_capital = monto_cuota - monto_interes

    cuota = Cuota(
        prestamo_id=prestamo.id,
        numero_cuota=numero_cuota,
        fecha_vencimiento=fecha_vencimiento,
        monto_cuota=monto_cuota,
        monto_capital=monto_capital,
        monto_interes=monto_interes,
        estado="PENDIENTE",
        total_pagado=Decimal("0.00"),
        # ... otros campos inicializados
    )
    db.add(cuota)
db.commit()
```

---

## 💰 FASE 2: REGISTRO DE PAGO

### **Paso 2.1: Crear Registro de Pago**

**Endpoint:** `POST /api/v1/pagos/`

**Función:** `crear_pago()` en `pagos.py` (línea 596)

#### **Tabla: `pagos`**

**Se crea 1 nuevo registro**

| Campo | Valor | Descripción |
|-------|-------|-------------|
| `id` | `AUTO_INCREMENT` | ID único del pago |
| `cedula` | `pago_data.cedula` | Cédula del cliente |
| `prestamo_id` | `pago_data.prestamo_id` (opcional) | ID del préstamo asociado |
| `numero_cuota` | `pago_data.numero_cuota` (opcional) | Número de cuota (opcional) |
| `fecha_pago` | `pago_data.fecha_pago` | Fecha del pago |
| `fecha_registro` | `datetime.now()` | Fecha de registro en el sistema |
| `monto_pagado` | `pago_data.monto_pagado` | Monto pagado |
| `numero_documento` | `pago_data.numero_documento` | Número de documento bancario |
| `institucion_bancaria` | `pago_data.institucion_bancaria` (opcional) | Institución bancaria |
| `estado` | `"PAGADO"` (default) | Estado inicial del pago |
| `conciliado` | `False` (default) | Estado de conciliación |
| `fecha_conciliacion` | `NULL` | Fecha de conciliación (inicialmente NULL) |
| `verificado_concordancia` | `"NO"` (default) | Verificación de concordancia |
| `activo` | `True` (default) | Estado activo del pago |
| `usuario_registro` | `current_user.email` | Usuario que registró el pago |

**Código:**
```python
nuevo_pago = Pago(**pago_dict)
nuevo_pago.usuario_registro = current_user.email
nuevo_pago.fecha_registro = datetime.now()
db.add(nuevo_pago)
db.commit()
```

---

### **Paso 2.2: Aplicar Pago a Cuotas**

**Función:** `aplicar_pago_a_cuotas()` en `pagos.py` (línea 1232)

**Condición:** Solo si `pago.prestamo_id` está definido

#### **Tabla: `cuotas`**

**Se actualizan múltiples registros** (cuotas afectadas por el pago)

**Campos actualizados en cada cuota afectada:**

| Campo | Actualización | Descripción |
|-------|---------------|-------------|
| `capital_pagado` | `+= capital_aplicar` | Incrementa capital pagado |
| `interes_pagado` | `+= interes_aplicar` | Incrementa interés pagado |
| `total_pagado` | `+= monto_aplicar` | Incrementa total pagado |
| `capital_pendiente` | `-= capital_aplicar` (mínimo 0) | Reduce capital pendiente |
| `interes_pendiente` | `-= interes_aplicar` (mínimo 0) | Reduce interés pendiente |
| `fecha_pago` | `fecha_pago` (si es la primera vez) | Fecha de pago |
| `dias_mora` | Calculado si `fecha_pago > fecha_vencimiento` | Días de mora |
| `monto_mora` | Calculado si `fecha_pago > fecha_vencimiento` | Monto de mora |
| `tasa_mora` | Calculado si `fecha_pago > fecha_vencimiento` | Tasa de mora |
| `estado` | Actualizado según reglas | Estado de la cuota |
| `dias_morosidad` | Calculado automáticamente | Días de morosidad |
| `monto_morosidad` | Calculado automáticamente | Monto de morosidad |

**Código:**
```python
# Aplicar monto a cuota
cuota.capital_pagado += capital_aplicar
cuota.interes_pagado += interes_aplicar
cuota.total_pagado += monto_aplicar
cuota.capital_pendiente = max(0, cuota.capital_pendiente - capital_aplicar)
cuota.interes_pendiente = max(0, cuota.interes_pendiente - interes_aplicar)

# Calcular mora si fecha_pago > fecha_vencimiento
if fecha_pago > cuota.fecha_vencimiento:
    cuota.dias_mora = (fecha_pago - cuota.fecha_vencimiento).days
    cuota.monto_mora = calcular_mora(...)
    cuota.tasa_mora = tasa_mora_diaria

# Actualizar estado y morosidad
_actualizar_estado_cuota(cuota, fecha_hoy, db)
_actualizar_morosidad_cuota(cuota, fecha_hoy)
```

---

### **Paso 2.3: Actualizar Estado del Pago**

**Función:** `crear_pago()` en `pagos.py` (línea 650-658)

#### **Tabla: `pagos`**

| Campo | Valor Anterior | Valor Nuevo | Condición |
|-------|----------------|-------------|-----------|
| `estado` | `"PAGADO"` | `"PARCIAL"` | Si `prestamo_id` existe y `cuotas_completadas == 0` |
| `estado` | `"PAGADO"` | `"PAGADO"` | Si `prestamo_id` existe y `cuotas_completadas > 0` |
| `estado` | `"PAGADO"` | `"PAGADO"` | Si `prestamo_id` es NULL (sin cambios) |

**Código:**
```python
if nuevo_pago.prestamo_id and cuotas_completadas == 0:
    nuevo_pago.estado = "PARCIAL"
elif nuevo_pago.prestamo_id and cuotas_completadas > 0:
    nuevo_pago.estado = "PAGADO"
db.commit()
```

---

## 🔄 FASE 3: CONCILIACIÓN DE PAGOS

### **Paso 3.1: Conciliar Pago (Coincidencia de Número de Documento)**

**Endpoint:** `POST /api/v1/pagos/conciliacion/upload`

**Función:** `_conciliar_pago()` en `pagos_conciliacion.py` (línea 48)

**Condición:** `numero_documento` del Excel coincide EXACTAMENTE con `pago.numero_documento`

#### **Tabla: `pagos`**

| Campo | Valor Anterior | Valor Nuevo | Descripción |
|-------|----------------|-------------|-------------|
| `conciliado` | `False` | `True` | Estado de conciliación |
| `fecha_conciliacion` | `NULL` | `datetime.now()` | Fecha de conciliación |
| `verificado_concordancia` | `"NO"` | `"SI"` | Verificación de concordancia |
| `monto_pagado` | (sin cambios) | (sin cambios) | **NO se modifica** |
| `estado` | (sin cambios) | (sin cambios) | **NO se modifica** |

**Código:**
```python
pago.conciliado = True
pago.fecha_conciliacion = datetime.now()
pago.verificado_concordancia = "SI"
db.commit()  # ✅ Commit del pago conciliado
```

---

### **Paso 3.2: Actualizar Estado de Cuotas Después de Conciliación**

**Función:** `_conciliar_pago()` en `pagos_conciliacion.py` (línea 72-112)

**Condición:** Solo si `pago.prestamo_id` está definido y todos los pagos están conciliados

#### **Tabla: `cuotas`**

**Se actualizan múltiples registros** (cuotas con pagos aplicados)

**Campos actualizados:**

| Campo | Actualización | Condición |
|-------|---------------|-----------|
| `estado` | `"PENDIENTE"` → `"PAGADO"` | Si `total_pagado >= monto_cuota` Y todos los pagos conciliados |
| `estado` | `"PENDIENTE"` → `"PENDIENTE"` | Si `total_pagado >= monto_cuota` PERO NO todos conciliados |
| `estado` | `"PARCIAL"` / `"ATRASADO"` → `"PARCIAL"` | Si `total_pagado < monto_cuota` y `fecha_vencimiento < hoy` |
| `dias_morosidad` | Recalculado | Automáticamente |
| `monto_morosidad` | Recalculado | Automáticamente |

**Código:**
```python
if pago.prestamo_id:
    cuotas = db.query(Cuota).filter(
        Cuota.prestamo_id == pago.prestamo_id,
        Cuota.total_pagado > 0
    ).all()

    for cuota in cuotas:
        todos_conciliados = _verificar_pagos_conciliados_cuota(db, cuota.id, cuota.prestamo_id)

        if todos_conciliados:
            _actualizar_estado_cuota(cuota, fecha_hoy, db)
            # Si total_pagado >= monto_cuota → estado = "PAGADO"
            # Si total_pagado < monto_cuota → estado = "PARCIAL" o "PENDIENTE"

    db.commit()  # ✅ Commit de las actualizaciones de cuotas
```

---

## 📊 RESUMEN DE TABLAS Y CAMPOS AFECTADOS

### **Tabla: `prestamos`**

| Fase | Campos Afectados | Operación |
|------|------------------|-----------|
| **FASE 1.1** | `estado`, `usuario_aprobador`, `fecha_aprobacion`, `tasa_interes`, `fecha_base_calculo` | UPDATE |

### **Tabla: `cuotas`**

| Fase | Campos Afectados | Operación |
|------|------------------|-----------|
| **FASE 1.2** | Todos los campos (creación de N registros) | INSERT |
| **FASE 2.2** | `capital_pagado`, `interes_pagado`, `total_pagado`, `capital_pendiente`, `interes_pendiente`, `fecha_pago`, `dias_mora`, `monto_mora`, `tasa_mora`, `estado`, `dias_morosidad`, `monto_morosidad` | UPDATE |
| **FASE 3.2** | `estado`, `dias_morosidad`, `monto_morosidad` | UPDATE |

### **Tabla: `pagos`**

| Fase | Campos Afectados | Operación |
|------|------------------|-----------|
| **FASE 2.1** | Todos los campos (creación de 1 registro) | INSERT |
| **FASE 2.3** | `estado` | UPDATE |
| **FASE 3.1** | `conciliado`, `fecha_conciliacion`, `verificado_concordancia` | UPDATE |

---

## 🔄 FLUJO COMPLETO VISUAL

```
┌─────────────────────────────────────────────────────────────────┐
│ FASE 1: APROBACIÓN DE PRÉSTAMO                                  │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │ 1.1 Cambiar estado a APROBADO │
    │    Tabla: prestamos           │
    │    - estado                   │
    │    - usuario_aprobador        │
    │    - fecha_aprobacion         │
    │    - tasa_interes             │
    │    - fecha_base_calculo        │
    └───────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │ 1.2 Generar tabla amortización│
    │    Tabla: cuotas              │
    │    - INSERT N registros       │
    │    - Todos los campos         │
    │    - estado = "PENDIENTE"     │
    └───────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ FASE 2: REGISTRO DE PAGO                                        │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │ 2.1 Crear registro de pago    │
    │    Tabla: pagos               │
    │    - INSERT 1 registro        │
    │    - conciliado = False       │
    │    - estado = "PAGADO"        │
    └───────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │ 2.2 Aplicar pago a cuotas      │
    │    Tabla: cuotas               │
    │    - UPDATE múltiples          │
    │    - total_pagado += monto    │
    │    - Calcular mora si aplica   │
    │    - Actualizar estado         │
    └───────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │ 2.3 Actualizar estado pago     │
    │    Tabla: pagos               │
    │    - estado = "PARCIAL" o     │
    │      "PAGADO"                  │
    └───────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ FASE 3: CONCILIACIÓN DE PAGOS                                   │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │ 3.1 Conciliar pago            │
    │    Tabla: pagos               │
    │    - conciliado = True        │
    │    - fecha_conciliacion       │
    │    - verificado_concordancia  │
    └───────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │ 3.2 Actualizar estado cuotas  │
    │    Tabla: cuotas              │
    │    - estado = "PAGADO" si     │
    │      todos conciliados        │
    │    - Actualizar morosidad     │
    └───────────────────────────────┘
```

---

## ✅ REGLAS DE NEGOCIO CLAVE

### **Estado de Cuotas**

- **PAGADO:** `total_pagado >= monto_cuota` Y todos los pagos conciliados
- **PENDIENTE:** `total_pagado >= monto_cuota` PERO NO todos conciliados, O `total_pagado > 0` y `fecha_vencimiento >= hoy`
- **PARCIAL:** `total_pagado > 0` pero `< monto_cuota` y `fecha_vencimiento < hoy`
- **ATRASADO:** `total_pagado = 0` y `fecha_vencimiento < hoy`
- **ADELANTADO:** `total_pagado > 0` pero `< monto_cuota` y `fecha_vencimiento >= hoy`

### **Cálculo de Mora**

- Se calcula automáticamente si `fecha_pago > fecha_vencimiento`
- Fórmula: `monto_mora = monto_cuota * tasa_mora_diaria * dias_mora / 100`
- `dias_mora = (fecha_pago - fecha_vencimiento).days`

### **Conciliación**

- Requiere coincidencia EXACTA de `numero_documento`
- Una vez conciliado, NO se puede desconciliar automáticamente
- La conciliación actualiza automáticamente el estado de las cuotas si todos los pagos están conciliados

---

## 📝 NOTAS IMPORTANTES

1. **`monto_pagado` NO se modifica** durante la conciliación
2. **`pago.estado` NO se actualiza** durante la conciliación (solo al crear)
3. **Las cuotas se actualizan automáticamente** cuando todos los pagos están conciliados
4. **La mora se calcula automáticamente** cuando `fecha_pago > fecha_vencimiento`
5. **Los pagos se aplican a las cuotas más antiguas primero** (por `fecha_vencimiento`)

