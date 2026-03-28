# Implementación: Recalcular Fechas de Amortización

## Resumen

Se implementó un flujo completo para recalcular **solo las fechas de vencimiento** de las cuotas cuando se modifica la **fecha de aprobación** de un préstamo APROBADO.

## Funcionamiento

### 1. **Identificación del Formulario**
El formulario está en: `Modal "Editar Préstamo"` → campo `Fecha de aprobación`
- **Ubicación en UI**: `/pagos/prestamos` → Click en préstamo APROBADO → Modal "Editar Préstamo"
- **Componente Frontend**: `CrearPrestamoForm.tsx`

### 2. **Cambios Realizados**

#### Backend (`app/api/v1/endpoints/prestamos.py`)

**Función auxiliar:** `_recalcular_fechas_vencimiento_cuotas(db, p, fecha_base)`
- Recalcula **solo** fechas de vencimiento desde nueva fecha de aprobación
- Mantiene intactos:
  - ✅ Montos de cuota
  - ✅ Pagos registrados (total_pagado)
  - ✅ Saldos de capital
- Recalcula:
  - 📅 `fecha_vencimiento` (usando misma lógica: MENSUAL, QUINCENAL, SEMANAL)
  - 🔄 `estado` de cuota (VENCIDO, PENDIENTE, MOROSO, etc.)

**Endpoint nuevo:** `POST /{prestamo_id}/recalcular-fechas-amortizacion`
- Actualiza fecha de aprobación
- Invoca recálculo de fechas
- Retorna cantidad de cuotas actualizadas

#### Frontend (`src/components/prestamos/CrearPrestamoForm.tsx`)

**Nuevos estados:**
- `isRecalculatingAmortizacion`: bandera de carga
- `fechaAprobacionAnterior`: guarda la fecha original para detectar cambios

**Nueva función:** `recalcularAmortizacion()`
```typescript
// Flujo:
1. Valida que fecha de aprobación cambió
2. Actualiza fecha_aprobacion en BD (PUT)
3. Invoca endpoint de recálculo
4. Actualiza estado local
5. Muestra toast de éxito
```

**Nuevo botón UI:**
- Aparece cuando:
  - Prestamo está en estado APROBADO
  - Fecha de aprobación cambió
  - No está en modo solo-lectura
- Llama a `recalcularAmortizacion()` al hacer clic

**Nuevo servicio:** `prestamoService.recalcularFechasAmortizacion(prestamoId)`
- Endpoint: `POST /prestamos/{id}/recalcular-fechas-amortizacion`

### 3. **Flujo de Usuario**

```
1. Usuario abre modal "Editar Préstamo" (en APROBADO)
2. Cambia "Fecha de aprobación" (ej: 19/03/2026 → 20/03/2026)
3. Botón "Recalcular Amortización" aparece
4. Usuario hace clic en botón
5. Sistema:
   - Actualiza fecha_aprobacion en BD
   - Recalcula fechas de vencimiento de TODAS las cuotas
   - Recalcula estados (VENCIDO si ya pasó, PENDIENTE si es futuro, etc.)
   - Mantiene pagos asociados a cada cuota
6. Toast muestra: "Amortización recalculada: 12 cuota(s) actualizadas"
7. Modal puede cerrarse (cambios guardados en BD)
```

### 4. **Características Importantes**

✅ **Atómico**: Actualiza fecha + recalcula fechas en una transacción  
✅ **Seguro**: Valida que préstamo exista y esté en estado APROBADO  
✅ **Preservador de datos**: No toca montos ni pagos  
✅ **Estados dinámicos**: Recalcula VENCIDO/PENDIENTE según fecha + hoy  
✅ **Respeta modalidad**: Mantiene MENSUAL/QUINCENAL/SEMANAL  

### 5. **Ejemplo de Cambio**

**Antes:**
```
Cuota 1: Vencimiento 17/01/2025, Pagado: 96 USD
Cuota 2: Vencimiento 01/02/2025, Pagado: 0 USD (VENCIDO)
...
```

**Usuario cambia fecha de aprobación a 20/03/2026**

**Después:**
```
Cuota 1: Vencimiento 20/04/2026, Pagado: 96 USD (PENDIENTE o PAGADO_ADELANTADO)
Cuota 2: Vencimiento 20/05/2026, Pagado: 0 USD (PENDIENTE)
...
```

### 6. **Archivos Modificados**

1. **Backend**:
   - `backend/app/api/v1/endpoints/prestamos.py`
     - Agregó: `_recalcular_fechas_vencimiento_cuotas()` (línea ~1875)
     - Agregó: `@router.post("/{prestamo_id}/recalcular-fechas-amortizacion")` (línea ~2572)

2. **Frontend**:
   - `frontend/src/components/prestamos/CrearPrestamoForm.tsx`
     - Agregó: estados `isRecalculatingAmortizacion`, `fechaAprobacionAnterior`
     - Agregó: función `recalcularAmortizacion()`
     - Agregó: botón UI en sección de fecha de aprobación
   
   - `frontend/src/services/prestamoService.ts`
     - Agregó: método `recalcularFechasAmortizacion(prestamoId)`

### 7. **Validaciones**

| Validación | Error |
|-----------|-------|
| Préstamo no encontrado | 404 Préstamo no encontrado |
| Sin fecha de aprobación | 400 Debe tener fecha de aprobación |
| Sin cuotas existentes | 400 Préstamo no tiene cuotas |
| Fecha no cambió | Info "La fecha de aprobación no cambió" |

### 8. **Testing Manual**

```bash
# 1. Backend: Verificar endpoint
curl -X POST http://localhost:8000/api/v1/prestamos/123/recalcular-fechas-amortizacion

# 2. Frontend: 
# - Ir a /pagos/prestamos
# - Clickear préstamo APROBADO
# - Cambiar "Fecha de aprobación"
# - Botón "Recalcular Amortización" debe aparecer
# - Clickear y esperar mensaje de éxito
# - Verificar en "Tabla de Amortización" que fechas cambiaron
```

---

**Estado**: ✅ Implementado y compilado  
**Último commit**: Cambios en backend y frontend listos para probar
