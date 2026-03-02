# ✅ FASE 1 COMPLETADA - Próximos Pasos

## 🎯 ESTADO ACTUAL

**Commits implementados**:
- `768645e1`: Endpoint + Servicio + Componente base
- `37df00b6`: Hook + saveRowIfValid
- `d93e63a1`: Auto-guardado automático

**Lo que está listo**:
1. ✅ Backend endpoint `/guardar-fila-editable` (POST)
2. ✅ Componente `TablaEditablePagos` con UI completa
3. ✅ Función `saveRowIfValid` con auto-guardado
4. ✅ Auto-disparo en `updateCellValue`
5. ✅ Servicio `pagoService.guardarFilaEditable`

**Lo que FALTA INTEGRAR**:
- ExcelUploaderPagosUI no está usando TablaEditablePagos aún
- Auto-guardado existe pero no se ve en acción (falta integración)

---

## 🚀 PRÓXIMA TAREA (CRÍTICA)

### Integrar TablaEditablePagos en ExcelUploaderPagosUI

**Archivo**: `frontend/src/components/pagos/ExcelUploaderPagosUI.tsx`

**Cambio**:

```typescript
// ANTES: Tabla estática con botones manuales
<table className="w-full">
  {excelData.map(row => (
    <tr>
      <input onChange={(e) => updateCellValue(row, 'cedula', e.target.value)} />
      {/* ... */}
      <Button onClick={() => saveIndividualPago(row)}>Guardar</Button>
    </tr>
  ))}
</table>

// DESPUÉS: Tabla editable con auto-guardado
<TablaEditablePagos
  rows={excelData}
  prestamosPorCedula={prestamosPorCedula}
  onRowsChange={setExcelData}
  onUpdateCell={updateCellValue}
  saveRowIfValid={saveRowIfValid}
/>
```

**Pasos exactos**:
1. Importar `TablaEditablePagos` desde `./TablaEditablePagos`
2. Reemplazar la sección `<table>` (líneas ~243-410) con el componente
3. Cambiar `showPreview` para mostrar `TablaEditablePagos` en lugar de tabla HTML
4. Remover lógica de tabla inline (ya está en TablaEditablePagos)
5. Mantener otros botones y funcionalidad (Enviar a Revisar, etc.)

---

## 📋 CHECKLIST: FASE 2 (INTEGRACIÓN)

### A. Reemplazar Preview Actual
- [ ] Importar TablaEditablePagos en ExcelUploaderPagosUI
- [ ] Remover tabla HTML (líneas ~243-410)
- [ ] Insertar componente con props correctos
- [ ] Verificar que funciona el flujo:
  - User abre Excel
  - Ve preview editable
  - Edita celda
  - Se valida inline
  - Si cumple → auto-guarda (fila desaparece)
  - Encabezado actualiza

### B. Testing Manual
- [ ] Upload Excel válido → preview muestra filas
- [ ] Editar cédula inválida → celda rojo + error
- [ ] Corregir cédula → verde + valida
- [ ] Editar monto válido → si todas cumplen → auto-guarda
- [ ] Verificar BD: INSERT en pagos + cuotas

### C. Refinamientos Post-Integración
- [ ] Toasts para éxito/error de auto-guardado
- [ ] Loading states visuales
- [ ] Manejo de 409 (duplicado) → enviar a Revisar Pagos automáticamente
- [ ] Mensaje "Fila guardada" o similar

---

## 🎬 CÓMO HACER LA INTEGRACIÓN

### Paso 1: Abrir ExcelUploaderPagosUI.tsx

```bash
# En Cursor:
frontend/src/components/pagos/ExcelUploaderPagosUI.tsx
```

### Paso 2: Importar el componente (al inicio del archivo)

```typescript
import { TablaEditablePagos } from './TablaEditablePagos'
```

### Paso 3: Encontrar la sección de preview

Buscar línea `showPreview ? (` alrededor de línea 135

### Paso 4: Reemplazar tabla actual

La tabla actual (dentro de `<Card>` en preview) se ve así:

```typescript
<Card>
  <CardHeader>
    <CardTitle>Previsualización</CardTitle>
  </CardHeader>
  <CardContent>
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        {/* ... toda la lógica de filas ... */}
      </table>
    </div>
  </CardContent>
</Card>
```

Cambiar por:

```typescript
<TablaEditablePagos
  rows={excelData}
  prestamosPorCedula={prestamosPorCedula}
  onRowsChange={setExcelData}
  onUpdateCell={updateCellValue}
  saveRowIfValid={saveRowIfValid}
/>
```

### Paso 5: Verificar compilación

```bash
npm run build
# o
npm run dev
```

### Paso 6: Test manual en navegador

1. Ir a CARGA MASIVA
2. Upload Excel
3. Ver preview en TablaEditablePagos
4. Editar celda
5. Verificar auto-guardado

---

## 📊 FLUJO COMPLETO DESPUÉS DE INTEGRACIÓN

```
┌─────────────────────────────────────┐
│ User abre CARGA MASIVA DE PAGOS     │
└──────────────┬──────────────────────┘
               │
               ↓
    ┌──────────────────────┐
    │ Sube Excel (20 filas)│
    └──────────┬───────────┘
               │
               ↓
    ┌──────────────────────────────────────┐
    │ TablaEditablePagos mostrada          │
    │ Cargados: 20 | Guardados: 0          │
    │ A Revisar: 0                         │
    └──────────┬───────────────────────────┘
               │
               ↓
    ┌──────────────────────────────────────┐
    │ User edita celda Monto en Fila 1     │
    │ "100" → validación inline            │
    │ ✅ Cédula OK | ✅ Monto OK |...      │
    └──────────┬───────────────────────────┘
               │
               ↓
    ┌──────────────────────────────────────┐
    │ updateCellValue() dispara             │
    │ Detecta: !_hasErrors → saveRowIfValid │
    └──────────┬───────────────────────────┘
               │
               ↓
    ┌──────────────────────────────────────┐
    │ saveRowIfValid() llama                │
    │ pagoService.guardarFilaEditable       │
    └──────────┬───────────────────────────┘
               │
               ↓
    ┌──────────────────────────────────────┐
    │ Backend: POST /guardar-fila-editable  │
    │ - INSERT pagos                        │
    │ - INSERT cuotas (reglas negocio)     │
    │ - Retorna pago_id                     │
    └──────────┬───────────────────────────┘
               │
               ↓
    ┌──────────────────────────────────────┐
    │ Frontend: saveRowIfValid éxito        │
    │ - Remueve fila de excelData           │
    │ - Llamaa refreshPagos()               │
    │ - Animación de salida                 │
    └──────────┬───────────────────────────┘
               │
               ↓
    ┌──────────────────────────────────────┐
    │ TablaEditablePagos actualiza          │
    │ Cargados: 20 | Guardados: 1 ✅       │
    │ A Revisar: 0                         │
    │ Fila 1 desaparece (animación)         │
    └──────────────────────────────────────┘
```

---

## ⚠️ CONSIDERACIONES

1. **Toasts**: Actualmente auto-guardado es silencioso. Si user lo prefiere, agregar toast "Fila guardada" en saveRowIfValid
2. **Errores 409 (duplicado)**: Debería auto-enviar a Revisar Pagos, no solo fallar silencioso
3. **Errores 422 (validación)**: Mantener silencioso (fila tiene errores de validación, user ve indicador rojo)
4. **Performance**: Con 100+ filas, el auto-guardado podría generar muchas peticiones simultaneas
   - Solución: Debounce en updateCellValue (esperar 500ms antes de auto-guardar)

---

## 🔄 ALTERNATIVA: Opción Conservadora

Si prefieres controlar el guardado manualmente por ahora:

1. Mantener TablaEditablePagos sin auto-guardado automático
2. Agregar botón "Guardar" en cada fila (o "Guardar Todos")
3. Cuando user presiona → ejecuta saveRowIfValid manualmente
4. Activar auto-guardado automático en una FASE 3 cuando todo esté probado

---

## 📅 ESTIMADO DE TIEMPO

- **Integración**: 20-30 min
- **Testing manual**: 15-20 min
- **Refinamientos**: 30-45 min
- **Total**: 1-1.5 horas

---

## 🎬 AHORA QUÉ

**Para el usuario**:
1. Hacer la integración siguiendo los pasos arriba
2. Test manual
3. Si todo funciona → listo para Render deploy
4. Si hay errores → compartir logs + screenshot

**Para asegurar éxito**:
- Compilación sin errores (`npm run build`)
- No romper funcionalidad existente (Enviar Revisar, etc.)
- Verificar BD: rows insertadas en pagos + cuotas

---

## 📚 REFERENCIAS

- TablaEditablePagos: `frontend/src/components/pagos/TablaEditablePagos.tsx`
- Hook: `frontend/src/hooks/useExcelUploadPagos.ts`
- Service: `frontend/src/services/pagoService.ts`
- Endpoint: `backend/app/api/v1/endpoints/pagos.py` (líneas 760+)
- Especificación: `ESPECIFICACION_FINAL_EDICION_INLINE.md`
