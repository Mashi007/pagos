# Plan de Implementación: Edición Inline en Carga Masiva

## Especificaciones Confirmadas

### 1. **Tabla Editable**
- ✅ Grid tipo hoja de cálculo
- ✅ Click en celda → edición inline
- ✅ Validación mientras escribe (tiempo real)
- ✅ Guardar fila individual SI cumple validadores
- ✅ Guardar TODOS los que cumplen validadores

### 2. **Validaciones por Columna**

#### **Cédula**
- Formato: V/E/J/Z + 6-11 dígitos
- Rojo si no cumple
- User puede editar

#### **Monto**
- Máximo 2 decimales (99.99, 100.00, etc.)
- Rango: 0.01 a 999,999,999,999.99
- Rojo si: tiene 3+ decimales, <= 0, o > límite
- User puede editar

#### **Fecha**
- Formato: DD-MM-YYYY o DD/MM/YYYY
- Mínimo: 01-07-2024
- Máximo: HOY
- Rojo si fuera de rango o formato inválido
- User puede editar

#### **Documentos**
- Acepta TODOS los formatos (BNC/, ZELLE/, números, etc.)
- NO duplicado en Excel (en mismo lote)
- NO duplicado en tabla pagos (BD)
- Rojo si duplicado
- User puede editar (cambiar documento)

### 3. **Descarga de Excel (desde Revisar Pagos)**

#### **Estructura del Excel Descargado**
```
Columnas:
- Cédula
- Monto
- Fecha
- Documento
- Observaciones (NUEVA - automática)
  └─ Texto describiendo por qué no pasó
     Ejemplo: "Cédula inválida; Monto con 3 decimales; Documento duplicado"

Filas:
- SOLO aquellas que NO cumplen validadores
- Todas las de tabla pagos_con_errores
```

#### **Automático al Descargar**
- DELETE FROM pagos_con_errores (elimina automático)
- Excel listo para corrección offline

### 4. **Flujo En Interfaz**

#### **Encabezado del Preview**
```
┌────────────────────────────────────────────┐
│ CARGA MASIVA - PREVIEW EDITABLE            │
│                                             │
│ ✅ Válidas: 18  │  ⚠️ Errores: 2           │
│                                             │
│ [✅ Guardar Todo Válido (18)]               │
│ [⚠️ Enviar a Revisión de Pagos (2)]        │
└────────────────────────────────────────────┘
```

#### **Tabla Principal**
```
# │ Cédula  │ Monto    │ Fecha      │ Documento │ Acción
──┼─────────┼──────────┼────────────┼───────────┼────────
1 │ V18007  │ 96       │ 31-10-2025 │ VE/50533  │ [✅]
2 │ V18007  │ 96       │ 12-11-2025 │ VE/49097  │ [✅]
3 │ V20996  │ 740087.. │ 28-08-2025 │ 740087..  │ [⚠️]
  │ ❌      │ ❌       │ ❌         │ ❌        │
4 │ V18464  │ 96       │ 03-09-2025 │ BNC/1304  │ [✅]
```

#### **Edición Inline**
```
User click en celda:
    ↓
Celda se vuelve input editable
    ↓
User escribe
    ↓
Validación INMEDIATA (mientras escribe)
    ↓
Si cumple: quita rojo, muestra ✅
Si NO cumple: muestra ROJO
    ↓
User presiona Enter o Tab
    ↓
Si toda la fila es válida: botón [✅ Guardar] se activa
```

### 5. **Acciones Por Fila**

#### **Fila Válida**
```
[✅ Guardar] → INSERT INTO pagos + removerow
```

#### **Fila Con Error**
```
[⚠️ Revisar] → INSERT INTO pagos_con_errores + removerow
```

### 6. **Acciones Globales**

#### **[✅ Guardar Todo Válido]**
```
Inserta TODOS las filas sin error
    ↓
Actualiza contadores
    ↓
Si quedan errores: solo esos visibles
```

#### **[⚠️ Enviar a Revisión de Pagos]**
```
Inserta TODOS las filas con error en pagos_con_errores
    ↓
Muestra: "2 filas enviadas a revisión"
    ↓
Usuario puede ir a "Revisar Pagos" para descargar Excel
```

### 7. **Módulo Revisar Pagos**

#### **Acceso**
```
GET /pagos_con_errores
    ↓
Muestra lista de filas con error
    ↓
[📥 Descargar Excel] → botón para cada fila o global
```

#### **Descarga**
```
Click [📥 Descargar]
    ↓
Genera Excel con:
  - Cédula, Monto, Fecha, Documento
  - Observaciones (por qué no pasó)
    └─ Ejemplo: "Monto: 3 decimales; Documento: duplicado en BD"
    ↓
DELETE FROM pagos_con_errores (automático)
    ↓
Descarga completa, tabla vacía
```

#### **Re-upload**
```
User corrige Excel offline
    ↓
Sube nuevamente
    ↓
Mismo flujo: Preview editable
    ↓
Intenta pasar validadores nuevamente
```

---

## Componentes Necesarios

### **1. Tabla Editable (Nuevo)**
```typescript
// componentes/pagos/TablaEditablePagos.tsx
export function TablaEditablePagos({
  datos,
  validaciones,
  onCellChange,
  onRowSave,
  onRowDiscard,
  onRowReview,
})
```

**Features:**
- Grid editable
- Validación en tiempo real
- Filas rojo/verde
- Botones por fila

### **2. Hook Actualizado**
```typescript
// hooks/useExcelUploadPagos.ts
- validarCelda(field, value, rowIndex) - valida mientras escribe
- guardarFila(rowIndex) - INSERT si cumple validadores
- guardarTodasValidas() - INSERT múltiples
- enviarARevision(rowIndices) - INSERT pagos_con_errores
- descargarExcelErrores(rowIndices) - genera Excel + DELETE
```

### **3. Validadores Específicos**
```typescript
// utils/pagoExcelValidation.ts - ACTUALIZAR

validarCedula(cedula: string)
  → /^[VEJZ]\d{6,11}$/i

validarMonto(monto: string | number)
  → parseFloat(monto) > 0
  → parseFloat(monto) <= 999_999_999_999.99
  → decimales <= 2

validarFecha(fecha: string)
  → formato DD/MM/YYYY
  → >= 01-07-2024
  → <= hoy

validarDocumento(doc: string, allDocs: string[], bdDocs: string[])
  → !allDocs.includes(doc) (sin duplicado en Excel)
  → !bdDocs.includes(doc) (sin duplicado en BD)
```

### **4. Columna Observaciones**
```typescript
// Generar automáticamente según errores
generarObservaciones(fila, errores): string
  → "Monto: 3 decimales; Documento: duplicado en BD"
```

---

## API Endpoints Necesarios

### **Existentes (verificar)**
- ✅ `POST /api/v1/pagos` - guardar pago
- ✅ `POST /api/v1/pagos/upload` - carga masiva
- ✅ `GET /api/v1/pagos_con_errores` - listar errores
- ✅ `DELETE /api/v1/pagos_con_errores/{id}` - eliminar error

### **Nuevos (crear)**
- ❓ `POST /api/v1/pagos/validar-fila` - validar antes de guardar
- ❓ `POST /api/v1/pagos_con_errores/auto-delete-al-descargar` - delete + genera Excel
- ❓ `GET /api/v1/pagos?numero_documento={doc}` - verificar duplicado en BD

---

## Frontend: Estructura de Datos

### **Estado en Hook**
```typescript
excelData: {
  rows: Array<{
    id: string                    // temporal (UUID)
    cedula: string
    monto: number
    fecha: Date
    documento: string
    estado: "valida" | "error"
    errores: string[]            // qué no pasó
    editando: boolean            // está en edición
    guardada: boolean            // ya insertada en BD
  }>
  validaciones: Record<string, Record<string, boolean>>  // por fila, por campo
  observaciones: Record<string, string>                  // por fila
}
```

### **Renderizado**
```typescript
// Agrupar por estado
filasValidas = excelData.rows.filter(r => r.estado === "valida")
filasError = excelData.rows.filter(r => r.estado === "error")

// Renderizar tablas
<TablaEditablePagos datos={filasValidas} estado="valida" />
<TablaEditablePagos datos={filasError} estado="error" />
```

---

## Preguntas Técnicas Finales

### **1. ¿Guardar fila AUTOMÁTICO o botón?**
- A) User termina de editar → auto-guardar si válida
- B) User presiona [✅ Guardar] por fila

### **2. ¿Editar después de guardar?**
- A) Fila desaparece tras guardar
- B) Fila permanece editable (allow re-edit)

### **3. ¿Validar documento duplicado?**
- A) En tiempo real: mientras escribe documento
- B) Solo al guardar fila
- C) Ambos

### **4. ¿Mensaje de observaciones donde?**
- A) Tooltip hover en celda roja
- B) Columna "Observaciones" visible
- C) Popup al click en error

### **5. ¿Prioridad de implementación?**
- A) Tabla editable primero
- B) Validadores primero
- C) Ambos en paralelo

---

## Timeline Estimado

Si todas las respuestas son "A" (opciones simples):

- **Tabla Editable**: 2-3 horas
- **Validadores**: 1-2 horas
- **Acciones (guardar/revisar)**: 2-3 horas
- **Descarga Excel**: 1-2 horas
- **Testing**: 1-2 horas

**Total: 8-12 horas**

---

¿Confirmamos estructura y responde las preguntas técnicas?
