# FIX: Validación de Coherencia de Fechas

## Problema Identificado

El usuario reportó error:
```
"La fecha de requerimiento (2026-03-22) no puede ser posterior a la fecha 
de aprobación (2026-02-23)."
```

Pero en el formulario mostró:
- Fecha de requerimiento: 20/02/2026  ✅
- Fecha de aprobación: 23/02/2026    ✅

Esto indicaba que el formul ario estaba enviando **fechas en formato incorrecto** o sin conversión a datetime ISO.

---

## Causas del Bug

### 1. **Frontend**: Formato incorrecto de `fecha_requerimiento`

**Antes:**
```typescript
prestamoData.fecha_requerimiento = formData.fecha_requerimiento  
// Enviaba: "2026-02-20" (string plano, sin hora)
```

**Problema:** 
- `fecha_aprobacion` se convertía a ISO completo: `"2026-02-23T00:00:00"`
- `fecha_requerimiento` se enviaba sin hora
- Backend no normalizaba correctamente
- Comparación datetime vs date fallaba

### 2. **Backend**: Comparación de tipos incorrecta

**Antes:**
```python
ap_date = row.fecha_aprobacion.date()  # → date
if row.fecha_requerimiento > ap_date:  # Comparar datetime > date ❌
```

**Problema:**
- `row.fecha_requerimiento` es `datetime` 
- `ap_date` es `date`
- Python puede comparar datetime vs date, pero dependiendo de la hora puede fallar

---

## Solución Implementada

### 1. **Frontend - CrearPrestamoForm.tsx**

✅ **Ahora ambas fechas se formatean igual:**

```typescript
// Extraer fechas del formulario
const fechaReq = formData.fecha_requerimiento
  ? String(formData.fecha_requerimiento).trim()
  : ''

const fechaApr = formData.fecha_aprobacion
  ? String(formData.fecha_aprobacion).trim()
  : ''

// Formatear como ISO completo (datetime)
if (fechaReq !== '') {
  prestamoData.fecha_requerimiento = `${fechaReq}T00:00:00`  // ← NUEVO
} else {
  delete prestamoData.fecha_requerimiento
}

if (fechaApr !== '') {
  prestamoData.fecha_aprobacion = `${fechaApr}T00:00:00`
} else {
  delete prestamoData.fecha_aprobacion
}
```

### 2. **Backend - prestamos.py (línea ~3974)**

✅ **Ahora ambas se normalizan a `date` para comparación segura:**

```python
# Coherencia: si hay fecha de aprobación, la fecha de requerimiento no puede ser posterior

if row.fecha_aprobacion and row.fecha_requerimiento:
    
    # Normalizar ambas fechas a date para comparación correcta
    ap_date = row.fecha_aprobacion.date() if hasattr(row.fecha_aprobacion, "date") else row.fecha_aprobacion
    req_date = row.fecha_requerimiento.date() if hasattr(row.fecha_requerimiento, "date") else row.fecha_requerimiento
    
    # Ahora se comparan date vs date (seguro)
    if req_date > ap_date:
        raise HTTPException(...)
```

---

## Resultado

| Aspecto | Antes | Después |
|---------|-------|---------|
| `fecha_requerimiento` enviado | `"2026-02-20"` (string) | `"2026-02-20T00:00:00"` (ISO) |
| `fecha_aprobacion` enviado | `"2026-02-23T00:00:00"` (ISO) | `"2026-02-23T00:00:00"` (ISO) |
| Backend compara | `datetime > date` ❌ | `date > date` ✅ |
| Validación | Inconsistente | Consistente |
| Error de usuario | Sí (falsa validación) | No ✅ |

---

## Testing

```
1. Ir a /pagos/prestamos
2. Editar préstamo APROBADO
3. Cambiar "Fecha de requerimiento"
4. Guardar
5. ✅ No debe mostrar error "no puede ser posterior"
6. ✅ Formulario debe guardar sin problema
```

---

## Archivos Modificados

1. **frontend/src/components/prestamos/CrearPrestamoForm.tsx** (línea ~637-698)
   - Agregó formateo de `fecha_requerimiento`

2. **backend/app/api/v1/endpoints/prestamos.py** (línea ~3974-3991)
   - Mejoró comparación a normalizar ambas fechas

---

## Cambios Compilados ✅

- TypeScript: Sin errores
- Python: Sin errores
