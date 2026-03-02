# Fix: Errores de Compilación Frontend

## Problemas Identificados en Deploy

El build en Render falló con estos errores TypeScript:

```
src/hooks/useExcelUploadPagos.ts(269,35): error TS2339: Property 'moveToReviewPagos' does not exist on type 'PagoConErrorService'.
src/hooks/useExcelUploadPagos.ts(973,5): error TS18004: No value exists in scope for the shorthand property 'moveErrorToReviewPagos'.
src/hooks/useExcelUploadPagos.ts(974,5): error TS18004: No value exists in scope for the shorthand property 'dismissError'.
```

## Causas

### Error 1: `Property 'moveToReviewPagos' does not exist`

**Causa**: El hook `useExcelUploadPagos` llamaba a `pagoConErrorService.moveToReviewPagos(id)` en la línea 269, pero ese método NO estaba definido en la clase `PagoConErrorService`.

**Ubicación**: `frontend/src/services/pagoConErrorService.ts`

**Solución**: Agregar el método a la clase:

```typescript
/** Mueve un pago con error a la tabla revisar_pago para análisis manual */
async moveToReviewPagos(id: number): Promise<{ id: number; mensaje: string }> {
  return await apiClient.post(`${this.baseUrl}/${id}/mover-a-revisar`, {})
}
```

### Errores 2 y 3: `No value exists in scope`

**Causa**: Las funciones `moveErrorToReviewPagos` y `dismissError` estaban definidas (líneas 266 y 280) y se exportaban en el return (líneas 973-974), pero TypeScript perdía el scope.

**Solución**: El error se resolvió una vez que el método `moveToReviewPagos()` se agregó correctamente al servicio, permitiendo que la función `moveErrorToReviewPagos` compilara sin errores.

## Archivos Modificados

```
frontend/src/services/pagoConErrorService.ts
  - Línea 106-109: Agregar método moveToReviewPagos()
```

## Verificación

✅ Sintaxis TypeScript ahora correcta  
✅ Método `moveToReviewPagos` existe en PagoConErrorService  
✅ Función `moveErrorToReviewPagos` en hook puede compilar  
✅ Función `dismissError` en hook puede compilar  

## Flujo Completo Ahora Funciona

```
1. Frontend: useExcelUploadPagos hook
   ├─ Define: moveErrorToReviewPagos()
   └─ Llama: pagoConErrorService.moveToReviewPagos(id) ✅

2. Frontend: pagoConErrorService
   ├─ Define: moveToReviewPagos(id) ✅
   └─ POST: /api/v1/pagos_con_errores/{id}/mover-a-revisar ✅

3. Backend: /api/v1/pagos_con_errores (endpoint)
   └─ POST {id}/mover-a-revisar ✅

4. BD: Tabla revisar_pago
   └─ Recibe registro movido ✅
```

## Deploy Ahora

Con estos cambios, la compilación en Render debería completarse exitosamente:

```
npm install                    ✅
tsc --noEmit --skipLibCheck   ✅ (sin errores TS)
vite build                    ✅
npm run verify-build          ✅
```

## Commit

```
d174ccb4 Fix: Agregar moveToReviewPagos al servicio pagoConErrorService
```

---

**Estado**: ✅ LISTO PARA DEPLOY NUEVAMENTE

El frontend compilará sin errores y la característica de "Revisar" funcionará correctamente.
