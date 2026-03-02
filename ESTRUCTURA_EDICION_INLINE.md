# Estructura: Edición Inline en Carga Masiva

## Flujo Requerido

```
1. Usuario sube Excel
         ↓
2. Sistema parsea y valida
         ↓
3. Muestra PREVIEW EDITABLE con 3 secciones:
    ├─ ✅ FILAS VALIDAS (sin errores)
    │  └─ Tabla editable inline para revisar/corregir
    │     - Botones [Guardar Fila] para cada una
    │     - O [Guardar Todo Valido]
    │
    ├─ ⚠️ FILAS CON ERRORES (validacion falló)
    │  └─ Tabla editable inline con errores resaltados
    │     - Columnas con error en RED
    │     - User puede corregir en linea
    │     - Botones [Guardar] [Descartar] [Revisar]
    │
    └─ ❌ FILAS DESCARTADAS (user las eliminó)
         └─ Ocultas o en lista secundaria

4. Usuario puede:
   - Editar valores directly en tabla
   - Guardar filas válidas → tabla 'pagos'
   - Guardar filas corregidas → tabla 'pagos' (si ahora son válidas)
   - Dejar filas con error → tabla 'pagos_con_errores' (si no las corrige)
   - Revisar en "Revisar Pagos" → tabla 'revisar_pago'

5. Después de acciones:
   - Filas guardadas desaparecen del preview
   - Count actualiza automáticamente
   - Resultado final: Guardados + Con Error
```

## Interfaz Visual Requerida

```
┌──────────────────────────────────────────────────────────────┐
│ CARGA MASIVA DE PAGOS - PREVIEW EDITABLE                    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ ✅ FILAS VALIDAS (18)                                         │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ # │ Cédula   │ Monto  │ Fecha      │ Documento   │ ... │   │
│ ├────────────────────────────────────────────────────────┤   │
│ │ 2 │ V180007- │ 96    │ 31-10-2025 │ VE/5053... │ ✏️  │   │
│ │   │ 58       │       │            │            │     │   │
│ ├────────────────────────────────────────────────────────┤   │
│ │ 3 │ V180007- │ 96    │ 12-11-2025 │ VE/4909... │ ✏️  │   │
│ │   │ 58       │       │            │            │     │   │
│ └────────────────────────────────────────────────────────┘   │
│ [Guardar Todo Valido (18)]  [Descartar Todos]                │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ ⚠️ FILAS CON ERRORES (2)                                      │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ # │ Cédula   │ Monto     │ Fecha │ Documento      │ ... │   │
│ ├────────────────────────────────────────────────────────┤   │
│ │ 5 │ V209966- │ 740087... │ 28... │ 740087...     │ ✏️  │   │
│ │   │ 98       │ ❌Error   │ -8-2  │ ❌Overflow    │     │   │
│ │   │          │           │ 025   │               │     │   │
│ └────────────────────────────────────────────────────────┘   │
│ [Guardar Corregidas] [Revisar Todas] [Descartar Todas]       │
└──────────────────────────────────────────────────────────────┘

ACCIONES FINALES:
[✅ Guardar] - Guarda válidas en 'pagos'
[⚠️ Revisar] - Pasa errores a 'pagos_con_errores' + 'revisar_pago'
[❌ Cerrar] - Cierra modal, datos guardados
```

## Componentes Necesarios

### 1. Tabla Editable Principal
- Mostrar datos parseados del Excel
- Columnas: Cédula, Monto, Fecha, Documento (+ otros campos)
- Celdas editables (texto, números, fechas)
- Validación en tiempo real mientras edita
- Indicador visual de error en celdas inválidas (fondo rojo)
- Botones de acción por fila

### 2. Agrupación por Estado
- VALIDAS: sin errores
- CON ERRORES: con validación fallida
- DESCARTADAS: user las eliminó (opcional mostrar)

### 3. Validación Inline
Mientras user edita, re-validar:
- Monto: número, > 0, < 999,999,999,999.99
- Cédula: V/E/J/Z + dígitos
- Fecha: formato válido
- Documento: no duplicado (en lote + BD)

### 4. Acciones Por Fila
```
┌─────────────────┐
│ ✏️  Editar      │ (abre modo edición para esa fila)
├─────────────────┤
│ ✅ Guardar      │ (si es válida: INSERT pagos)
├─────────────────┤
│ ⚠️  Revisar    │ (si error: INSERT pagos_con_errores)
├─────────────────┤
│ ❌ Descartar    │ (elimina de tabla)
└─────────────────┘
```

### 5. Acciones Globales
```
[✅ Guardar Todo Valido]   - Todas las filas sin error
[⚠️ Revisar Todas]         - Las filas con error
[❌ Descartar Todas]       - Elimina todas las seleccionadas
[🔄 Recargar]              - Vuelve a cargar el Excel
```

## Hook Functions Necesarias

Revisar si existen:
- ✅ `updateCellValue(rowIndex, field, value)` - modificar celda
- ❓ `validateRow(rowIndex)` - re-validar fila después edición
- ❓ `saveRow(rowIndex)` - guardar una fila en BD
- ❓ `saveAllValidRows()` - guardar todas las válidas
- ❓ `sendRowsToReview(rowIndices)` - enviar a revisar_pagos
- ❓ `discardRows(rowIndices)` - eliminar de tabla
- ✅ `saveAllValid()` - existe pero ¿guarda desde preview?

## Estado del Hook

Revisar si maneja:
- ✅ `excelData` - datos parseados
- ✅ `showPreview` - mostrar/ocultar preview
- ✅ `updateCellValue` - función para editar
- ❓ `rowValidation` - estado de validación por fila
- ❓ `rowEditing` - qué fila está siendo editada
- ❓ `rowStates` - válida, error, descartada, etc.

## Flujo Almacenamiento

### Opción A: Guardar Inmediato
```
User hace cambio en celda
    ↓
Re-validar
    ↓
Si es válida:
  - Guardar en BD (INSERT pagos)
  - Remover de tabla
Si tiene error:
  - Mostrar error en rojo
  - User puede corregir o descartar
```

### Opción B: Guardar Al Final
```
User edita múltiples celdas
    ↓
Click [Guardar Todo]
    ↓
Sistema:
  - Valida todas
  - Separa: válidas vs errores
  - Guarda válidas en 'pagos'
  - Guarda errores en 'pagos_con_errores'
    ↓
Muestra resultado: "18 guardadas, 2 para revisar"
```

## Preguntas de Clarificación

1. **¿Guardar inmediato o al final?**
   - Por fila cuando user termina de editar (inmediato)
   - O al click "Guardar Todo" (final)

2. **¿Columnas editables?**
   - Todas: Cédula, Monto, Fecha, Documento
   - Solo algunas: Cédula, Monto (document+fecha read-only)

3. **¿Validación durante edición?**
   - En tiempo real (user ve error mientras escribe)
   - Solo al guardar fila

4. **¿Re-validar documento duplicado?**
   - En lote (entre filas del Excel)
   - En BD (documentos ya registrados)
   - Ambos

5. **¿Mostrar filas descartadas?**
   - Eliminarlas completamente
   - Mostrar en sección colapsada
   - Contarlas en resumen

6. **¿Confirmación antes de guardar?**
   - Guardar directo
   - Confirmación por fila
   - Confirmación al final

## Siguiente Paso

- ¿Confirmamos estructura?
- ¿Responden las preguntas?
- ¿Reviso qué ya existe en el código?
