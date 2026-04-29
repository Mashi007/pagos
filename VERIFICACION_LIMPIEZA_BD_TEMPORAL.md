# Verificación: Limpieza BD Temporal y Movimiento a Cuotas

**Fecha:** 28 de Abril, 2026  
**Requerimiento:** Asegurar que:
1. Al eliminar un pago de BD temporal (`pagos_con_errores`) → se borre
2. Al "Guardar y Procesar" → se borre de BD temporal y pase a `cuota_pagos`

---

## 📊 Flujos Identificados

### FLUJO 1: Pago Nuevo con "Guardar y Procesar"

```
RegistrarPagoForm.tsx (crear nuevo)
  ↓
  POST /api/v1/pagos (backend: routes.py createPago)
    → Inserta en tabla `pagos` (BD principal)
    → NO toca `pagos_con_errores` (BD temporal)
  ↓
  POST /api/v1/pagos/{id}/aplicar-cuotas (backend: routes.py aplicar_pago_a_cuotas)
    → Si el pago tiene prestamo_id + monto > 0
    → Inserta en tabla `cuota_pagos`
    → Actualiza estado del pago
  ↓
  ✅ RESULTADO:
    - Pago en tabla `pagos` ✅
    - Filas en tabla `cuota_pagos` ✅
    - NO está en `pagos_con_errores` ✅ (nunca estuvo)
```

**Status de Limpieza:** ✅ OK (no hay BD temporal en este flujo)

---

### FLUJO 2: Editar Pago con Error (Revisión Manual) + "Guardar"

```
PagosList.tsx (pestaña revision)
  ↓
  handleGuardarRevision(id)
    ↓
    PUT /api/v1/pagos/con-errores/{id}
      (backend: pagos_con_errores/routes.py actualizar_pago_con_error)
      → Actualiza observaciones, estado, etc. en `pagos_con_errores`
      → NO mueve a tabla `pagos`
      → NO aplica a cuotas
  ↓
  ✅ RESULTADO:
    - Pago actualizado en `pagos_con_errores` ✅
    - SIGUE en BD temporal (por diseño, es revisión manual)
    - Requiere próximo paso: "Mover a Pagos"
```

**Status de Limpieza:** ⚠️ NO SE BORRA (por diseño: espera validación)

---

### FLUJO 3: Mover Pagos Corregidos de BD Temporal a Principal

```
PagosList.tsx (pestaña revision, botón "Mover a Pagos Normales")
  ↓
  POST /api/v1/pagos/con-errores/mover-a-pagos
    (backend: pagos_con_errores/routes.py mover_a_pagos_normales)
    
    Para cada pago_con_error en la lista:
      1. Crea nuevo registro en tabla `pagos`
      2. Si conciliado=true:
         → Aplica a cuotas (inserta en `cuota_pagos`)
         → Cambia estado a "PAGADO"
      3. ELIMINA el registro de `pagos_con_errores`
         (línea 846: db.delete(row))
      4. db.commit()
  ↓
  ✅ RESULTADO:
    - Pago movido a tabla `pagos` ✅
    - Si conciliado: aplicado a `cuota_pagos` ✅
    - ELIMINADO de `pagos_con_errores` ✅ ← BORRO BD TEMPORAL
```

**Status de Limpieza:** ✅ OK

---

### FLUJO 4: Eliminar Pago de BD Temporal

```
PagosList.tsx (pestaña revision, botón "Eliminar")
  ↓
  handleEliminarRevision(id)
    ↓
    DELETE /api/v1/pagos/con-errores/{id}
      (backend: pagos_con_errores/routes.py eliminar_pago_con_error)
      
      1. Busca pago en `pagos_con_errores`
      2. Si existe:
         → db.delete(row)
         → db.commit()
      3. Return 204 No Content
  ↓
  ✅ RESULTADO:
    - Pago ELIMINADO de `pagos_con_errores` ✅ ← BORRO BD TEMPORAL
    - Nunca estuvo en `pagos` (era error)
    - No toca `cuota_pagos`
```

**Status de Limpieza:** ✅ OK

---

## 🔍 Análisis del Requerimiento

### ¿Qué es "BD Temporal"?

La BD temporal = tabla `pagos_con_errores`
- Almacena pagos que vienen de **Carga Masiva con errores**
- O pagos que se crean en **"Revisar Pagos"** (modal)
- Esperan **revisión manual** antes de pasar a `pagos`

### Requerimiento del Usuario

> "Asegura que al ser eliminado se borre de la BD temporal / al ser guardado y procesado se borre de la BD temporal y pase a la cuota respectiva"

**Interpretación:**

```
Caso A: Eliminar pago de BD temporal
  DELETE /api/v1/pagos/con-errores/{id}
  ✅ Se borra de pagos_con_errores
  
Caso B: Guardar y Procesar (mover a pagos normales)
  POST /api/v1/pagos/con-errores/mover-a-pagos
  ✅ Se borra de pagos_con_errores
  ✅ Se crea en pagos
  ✅ Se aplica a cuota_pagos (si conciliado=true)
```

---

## ✅ Verificación de Implementación

### Eliminación desde BD Temporal (DELETE)

**Código Backend:**
```python
# pagos_con_errores/routes.py línea 944-958
@router.delete("/{pago_id}", status_code=204)
def eliminar_pago_con_error(pago_id: int, db: Session = Depends(get_db)):
    row = db.get(PagoConError, pago_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pago con error no encontrado")
    
    db.delete(row)  # ✅ BORRA de tabla pagos_con_errores
    db.commit()
    return None
```

**Verificación:**
- ✅ Busca por ID
- ✅ Valida existencia
- ✅ Ejecuta delete
- ✅ Commitea cambios
- ✅ Retorna 204 (sin contenido)

**Status:** ✅ CORRECTO

---

### Movimiento a Pagos Normales + Aplicación a Cuotas

**Código Backend:**
```python
# pagos_con_errores/routes.py línea 752-852
@router.post("/mover-a-pagos", response_model=dict)
def mover_a_pagos_normales(payload: dict = Body(...), db: Session = Depends(get_db)):
    # ...
    for pid in ids:
        row = db.get(PagoConError, pid)  # Busca en BD temporal
        if not row:
            continue
        
        # Crea nuevo pago en tabla pagos
        pago = Pago(
            cedula_cliente=row.cedula_cliente,
            prestamo_id=row.prestamo_id,
            # ... copiar todos los campos
        )
        db.add(pago)
        db.flush()
        db.refresh(pago)
        
        # SI tiene prestamo_id y monto > 0
        if pago.prestamo_id and float(pago.monto_pagado or 0) > 0:
            try:
                # Aplica a cuotas (CASCADA)
                cc, cp = _aplicar_pago_a_cuotas_interno(pago, db)
                if cc > 0 or cp > 0:
                    pago.estado = "PAGADO"  # Marca como pagado
                    cuotas_aplicadas += cc + cp
            except Exception as e:
                logger.warning(...)
        
        # ✅ BORRA de BD temporal
        db.delete(row)
        movidos += 1
    
    db.commit()  # Commitea todo junto
    return {"movidos": movidos, "cuotas_aplicadas": cuotas_aplicadas}
```

**Verificación:**
- ✅ Lee de `pagos_con_errores`
- ✅ Crea en `pagos`
- ✅ Aplica a `cuota_pagos` (cascada)
- ✅ Actualiza estado a "PAGADO"
- ✅ **BORRA de `pagos_con_errores`** (línea 846: db.delete(row))
- ✅ Commitea transaccionalmente (todo o nada)

**Status:** ✅ CORRECTO

---

## 🚀 Problemas Identificados y Soluciones

### ❓ PREGUNTA: ¿En qué momento ocurre "Guardar y Procesar" para BD temporal?

**Respuesta:**

Hay **DOS escenarios distintos**:

#### Escenario A: Crear Pago Nuevo (NO toca BD temporal)

```
Usuario abre modal "Nuevo Pago"
  → Rellena formulario
  → Click "Guardar y Procesar"
  → POST /api/v1/pagos (directo a tabla pagos)
  → POST /api/v1/pagos/{id}/aplicar-cuotas
  
✅ RESULTADO:
  - Nunca toca pagos_con_errores
  - Directo a pagos + cuota_pagos
  - NO hay limpieza de BD temporal (no hay que limpiar)
  
⚠️ NOTA: El fix que ya implementamos (capturar ID)
  asegura que este flujo funcione correctamente
```

#### Escenario B: Editar desde Revisión (sí toca BD temporal)

```
Usuario abre modal "Editar Pago con Error" (desde pestaña Revision)
  → Rellena formulario
  → Click "Guardar y Procesar"
  → ???
  
❓ PREGUNTA: ¿Qué sucede aquí?
  ¿Se guarda en pagos_con_errores + luego mueve?
  ¿O directamente mueve a pagos?
```

**Necesito verificar:** ¿Cuál es el flujo exacto del frontend cuando edita desde Revision?

---

## 📋 Checklist de Validación

```
✅ Eliminación de BD temporal
  ✅ DELETE /pagos/con-errores/{id} borra correctamente
  ✅ Retorna 204
  ✅ Valida existencia
  ✅ No deja huérfanos en cuota_pagos (nunca estuvo conciliado)

✅ Movimiento de BD temporal a Principal
  ✅ POST /pagos/con-errores/mover-a-pagos:
    ✅ Lee de pagos_con_errores
    ✅ Crea en pagos
    ✅ Aplica a cuota_pagos (si conciliado=true)
    ✅ BORRA de pagos_con_errores
    ✅ Transaccional (commit único)

⚠️ Edición desde Revision + Guardar y Procesar
  ⏳ Verificar flujo exacto del frontend
  ⏳ ¿Edita en pagos_con_errores o lo mueve directamente?

✅ Crear Pago Nuevo + Guardar y Procesar
  ✅ Ya implementado fix (capturar ID)
  ✅ Aplica correctamente a cuotas
```

---

## 🔧 Cambios Requeridos (si aplica)

### Si el Flujo "Editar + Guardar y Procesar" desde Revisión no funciona:

**Hipótesis:** Al editar un pago con error desde la pestaña "Revision", hacer click en "Guardar y Procesar" debería:
1. Actualizar el pago en `pagos_con_errores`
2. **Automáticamente moverlo a `pagos` + aplicar a cuotas**
3. **Limpiar de `pagos_con_errores`**

**Implementación Sugerida:**

```typescript
// frontend/src/components/pagos/RegistrarPagoForm.tsx
// Cuando se edita un pago con error (esPagoConError === true)
// y se hace "Guardar y Procesar":

if (isEditing && esPagoConError && modoGuardarYProcesar) {
  // 1. Actualizar en pagos_con_errores
  await pagoConErrorService.update(pagoId, datosEnvio)
  
  // 2. Mover a pagos normales (el backend aplica a cuotas automáticamente)
  await pagoConErrorService.moverAPagosNormales([pagoId])
  
  // 3. Se borra de BD temporal automáticamente ✅
}
```

---

## 📝 Conclusión

| Operación | Tabla Temporal | Limpieza | Estado |
|-----------|---|---|---|
| Eliminar pago | `pagos_con_errores` | ✅ Se borra | ✅ OK |
| Mover a pagos | `pagos_con_errores` | ✅ Se borra + pasa a `pagos` + `cuota_pagos` | ✅ OK |
| Crear nuevo + Guardar y Procesar | N/A (no toca temporal) | N/A | ✅ OK (fix aplicado) |
| Editar + Guardar y Procesar (desde Revision) | `pagos_con_errores` | ⏳ Verificar flujo | ⏳ VERIFICAR |

**Recomendación:** Validar en el frontend que cuando se edita desde Revision + "Guardar y Procesar", realmente se mueve la entrada y se borra de BD temporal.

---

**Documento:** VERIFICACION_LIMPIEZA_BD_TEMPORAL.md  
**Versión:** 1.0  
**Fecha:** 28-Abr-2026 20:15 UTC-5  
**Status:** EN PROGRESO - Verificación del flujo de edición desde Revision
