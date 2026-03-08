# Correcciones para que compile useExcelUploadPagos.ts

El build falla por **errores de sintaxis** en este archivo. Aplica estos cambios:

## 1. Línea ~358 (addToast error Cédula)
**Buscar:**
```ts
addToast('error', `Fila ${row._rowIndex}: La CLa Cédula no existe en clientes.)
```
**Reemplazar por:**
```ts
addToast('error', `Fila ${row._rowIndex}: La Cedula no existe en clientes.`)
```
(Una sola “La”, “Cedula” sin tilde, y **backtick** antes del `)`.)

---

## 2. Línea ~362 (addToast warning crédito)
**Buscar:**
```ts
addToast('warning', `Fila ${row._rowIndex}: No hay crNo hay crédito asignado.)
```
**Reemplazar por:**
```ts
addToast('warning', `Fila ${row._rowIndex}: No hay credito asignado.`)
```
(Una sola “No hay cr”, “credito” sin tilde, y **backtick** antes del `)`.)

---

## 3. Línea ~652 (ternario del toast “pendientes”)
**Buscar:**
```ts
omitidos > 0
          ? ${omitidos} fila(s) pendientes: guarde uno a uno, corrija o envíe a revisar.: 'No hay filas que cumplan criterios para guardar en lote.'
```
**Reemplazar por:**
```ts
omitidos > 0
          ? `${omitidos} fila(s) pendientes: guarde uno a uno, corrija o envie a revisar.`
          : 'No hay filas que cumplan criterios para guardar en lote.'
```
(El primer branch del ternario debe ir entre **backticks** `` `...` `` y el segundo branch debe ser `: 'No hay...'` en una línea aparte.)

---

## Resumen
- Cierra bien los **template literals** con backtick antes de `)`.
- Evita texto duplicado (“La CLa”, “No hay crNo hay”).
- En el ternario, el mensaje con `${omitidos}` debe estar entre backticks y el `: 'No hay...'` en su propia línea.

Después de guardar, ejecuta: `npm run build`.
