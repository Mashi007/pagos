# ✅ Fix: Escanear SIN Cédula Previa para Extraer Cédula del Comprobante

## Commit: `5288f762f`

---

## ¿Cuál Era el Problema?

El botón "Escanear" validaba que **ya hubiera una cédula ingresada**, lo que creaba un flujo circular:

```
❌ Antes:
1. Usuario abre modal de edición
2. Intenta escanear (comprobante está guardado)
3. Error: "Ingrese una cédula válida antes de escanear"
4. Pero quiere escanear para OBTENER la cédula...
```

---

## ¿Qué Se Arregló?

Ahora el sistema **permite escanear sin cédula** si **hay comprobante guardado**:

```
✅ Después:
1. Usuario abre modal de edición
2. Hay comprobante guardado pero sin cédula
3. Clic en "Escanear" → Se permite re-escaneo
4. Extrae cédula del comprobante (Mercantil/BNC)
5. Pre-rellena campo cedula_cliente automáticamente
```

---

## Cambios Técnicos

**Archivo**: `frontend/src/components/pagos/RegistrarPagoForm.tsx`

### Lógica Nueva (líneas 446-474)

```typescript
let cedulaPartes = descomponerCedula(formData.cedula_cliente)

// ← NUEVO: Permitir re-escaneo sin cédula si hay comprobante guardado
const tieneComprobanteGuardado = Boolean(linkComprobanteParaVista && !archivoComprobante)

if (!cedulaPartes && !tieneComprobanteGuardado) {
  toast.error('Ingrese una cédula válida antes de escanear.')
  return
}

// Si no hay cédula pero hay comprobante, usar cédula dummy para escaneo
if (!cedulaPartes && tieneComprobanteGuardado) {
  cedulaPartes = { tipo: 'V', numero: '0' }
  toast.info('Re-escaneando para extraer cédula del comprobante...')
}
```

### Type Safety (línea 499-500)

```typescript
// Aseguramos que cedulaPartes no es null con non-null assertion (!)
fd.append('tipo_cedula', cedulaPartes!.tipo)
fd.append('numero_cedula', cedulaPartes!.numero)
```

---

## Flujo Mejorado

```
┌─────────────────────────────────────────────┐
│ Modal: Editar Pago                          │
│ - Cédula Cliente: [vacío]                   │
│ - Comprobante: Guardado ✓                   │
│ - Banco: Mercantil                          │
│                                              │
│ Usuario clic "Escanear" →                   │
│                                              │
│ Sistema detecta:                             │
│ • No hay cédula                              │
│ • Pero hay comprobante guardado              │
│ → Permite escaneo                           │
│                                              │
│ OCR extrae cédula de comprobante             │
│ → Pre-rellena cedula_cliente                │
│                                              │
│ Resultado: Todos los campos listos ✨       │
└─────────────────────────────────────────────┘
```

---

## Validaciones

✅ **Type-check**: `npm run type-check` → PASA  
✅ **Format**: `npm run format` → OK  
✅ **Compilación**: Sin errores  
✅ **Git hooks**: Ejecutados correctamente  

---

## Caso de Uso Real

**Situación**: Estás en el modal de edición, hay un comprobante de Mercantil guardado, pero falta la cédula.

**Antes**: ❌ Error imposible de resolver sin salir del modal  
**Ahora**: ✅ Clic en "Escanear" → extrae cédula → campo se rellena  

---

## Resumen

| Aspecto | Antes | Después |
|---|---|---|
| **Sin cédula + comprobante guardado** | ❌ Error bloqueante | ✅ Permite escaneo |
| **Extrae cédula de comprobante** | Sí, pero no se podía usar | ✅ Se usa para pre-rellenar |
| **Flujo del usuario** | Circular, atrapado | ✅ Directo, sin fricciones |
| **Mercantil/BNC** | Cédula extraída pero ignorada | ✅ Campo se llena automáticamente |

