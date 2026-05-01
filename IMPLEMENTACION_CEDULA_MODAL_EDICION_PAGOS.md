# Implementación: Extracción de Cédula en Modal de Edición de Pagos

## Resumen

Se ha implementado la **extracción automática de cédula del pagador** en el botón "Escanear" del modal de edición de pagos. Ahora, cuando se escanea un comprobante de Mercantil o BNC, el sistema automáticamente:

1. ✅ Detecta la cédula del pagador desde la imagen
2. ✅ Pre-rellena el campo "Cédula Cliente"
3. ✅ Resetea el préstamo (para búsqueda nueva con la cédula detectada)
4. ✅ Muestra toast confirmando la cédula detectada

---

## Cambios Implementados

### Archivo: `frontend/src/components/pagos/RegistrarPagoForm.tsx`

#### Modificación: Función `handleReescanearDesdeComprobanteActual`

**Antes** (línea 515-523):
```typescript
setFormData(prev => ({
  ...prev,
  fecha_pago: (s.fecha_pago || '').trim() || prev.fecha_pago,
  institucion_bancaria:
    (s.institucion_financiera || '').trim() || prev.institucion_bancaria,
  numero_documento:
    (s.numero_operacion || '').trim() || prev.numero_documento,
  monto_pagado: nextMonto,
}))
```

**Después** (línea 505-537):
```typescript
// Procesar cédula extraída del comprobante (solo dígitos para Mercantil/BNC)
let nextCedula = formData.cedula_cliente
const cedulaExtraida = (s.cedula_pagador_en_comprobante || '').trim()
if (cedulaExtraida) {
  // La API retorna solo dígitos; agregar prefijo por defecto (V)
  nextCedula = `V${cedulaExtraida}`
}

setFormData(prev => ({
  ...prev,
  cedula_cliente: nextCedula,
  fecha_pago: (s.fecha_pago || '').trim() || prev.fecha_pago,
  institucion_bancaria:
    (s.institucion_financiera || '').trim() || prev.institucion_bancaria,
  numero_documento:
    (s.numero_operacion || '').trim() || prev.numero_documento,
  monto_pagado: nextMonto,
  prestamo_id: null, // Reset préstamo al cambiar cédula
}))
```

#### Modificación: Toast informativo

**Antes** (línea 533):
```typescript
toast.success('Campos actualizados desde el comprobante.')
```

**Después** (línea 539-546):
```typescript
if (cedulaExtraida) {
  toast.success(
    `Campos actualizados desde el comprobante. Cédula detectada: ${nextCedula}`
  )
} else {
  toast.success('Campos actualizados desde el comprobante.')
}
```

---

## Flujo de Uso

```
1. Usuario abre modal "Editar Pago"
   ↓
2. Clic en botón "Escanear" (lado derecho)
   ↓
3. Gemini OCR procesa comprobante:
   - Mercantil: busca en líneas RECAUDACION o DP:
   - BNC: busca línea "DP: V-XXXXX"
   ↓
4. API retorna:
   - cedula_pagador_en_comprobante: "12345678" (solo dígitos)
   - fecha_pago, institucion_financiera, numero_operacion, monto
   ↓
5. Frontend pre-rellena:
   - cedula_cliente: "V12345678" (agrega prefijo V)
   - Otros campos normalmente
   - prestamo_id: null (reset para nueva búsqueda)
   ↓
6. Toast: "Campos actualizados desde el comprobante. Cédula detectada: V12345678"
   ↓
7. Usuario ve cédula auto-rellenada, busca préstamo, continúa normalmente
```

---

## Bancos Soportados

| Banco | Detección | Resultado |
|---|---|---|
| **Mercantil** | ✅ Busca en recibos RECAUDACIÓN | Cédula extraída ↓ Campo relleno |
| **BNC** | ✅ Busca línea "DP: V-XXXXX" | Cédula extraída ↓ Campo relleno |
| **Otros** | ⚠️ Si no está disponible | Campo queda igual (sin error) |

---

## Beneficios

1. **Automatización**: La cédula se rellena sola para Mercantil/BNC
2. **Reducción de errores**: No necesita tipeo manual
3. **UX mejorada**: Toast confirma lo que se detectó
4. **Sin roturas**: Si no hay cédula, funciona normal (no es error)
5. **Flujo natural**: Reset de préstamo permite búsqueda con nueva cédula

---

## Validaciones Técnicas

✅ **Type-check**: `npm run type-check` pasa sin errores  
✅ **Formato**: `npm run format` ejecuta correctamente  
✅ **Backend ya funciona**: OCR extrae y retorna correctamente  

---

## Archivo Modificado

- `frontend/src/components/pagos/RegistrarPagoForm.tsx` (2 secciones)

---

## Notas

- **Prefijo por defecto**: La API retorna solo dígitos, así que el frontend agrega "V" (prefijo estándar de cédula venezolana)
- Si la API retorna prefijo en el futuro, se puede ajustar fácilmente
- El reset de `prestamo_id` es importante para evitar inconsistencias si cambió la cédula

