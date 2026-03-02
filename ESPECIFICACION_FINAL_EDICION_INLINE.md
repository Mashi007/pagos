# Especificación Final: Edición Inline en Carga Masiva

## ✅ CONFIRMADO - LISTO PARA IMPLEMENTAR

### **Respuestas Técnicas Confirmadas**

| Pregunta | Respuesta | Acción |
|----------|-----------|--------|
| 1. Auto-guardar | **1A: Inmediato** | INSERT pagos + Cuotas + Conciliado='SI' |
| 2. Fila cumple tras editar | **2A: Auto-guardar** | Desaparece de tabla |
| 3. Error duplicado | **Por tipo** | CEDULA, FECHA, DOCUMENTO en interfaz + Observaciones |
| 4. Descartar | **NO descartar** | Auto-guardar si cumple → Cuotas | No cumple → Revisar |
| 5. Encabezado | **5A: Auto-actualizar** | Tiempo real mientras edita |

---

## 🎯 **FLUJO FINAL CONFIRMADO**

### **Fase 1: Upload**
```
User sube Excel
    ↓
Sistema parsea 20 filas
```

### **Fase 2: Preview Editable**
```
┌──────────────────────────────────────────────────────┐
│ CARGA MASIVA - PREVIEW EDITABLE                      │
├──────────────────────────────────────────────────────┤
│ Cargados: 20 | ✅ Guardados: 18 | ⚠️ A Revisar: 2   │
├──────────────────────────────────────────────────────┤
│                                                       │
│ # │ Cédula     │ Monto    │ Fecha      │ Documento   │
│ ──┼────────────┼──────────┼────────────┼─────────────│
│ 1 │ V1800075   │ 96       │ 31-10-2025 │ VE/5053     │
│   │ ✅ OK      │ ✅ OK    │ ✅ OK      │ ✅ OK       │
│ ──┼────────────┼──────────┼────────────┼─────────────│
│ 2 │ V1800075   │ 96       │ 12-11-2025 │ VE/4909     │
│   │ ✅ OK      │ ✅ OK    │ ✅ OK      │ ✅ OK       │
│ ──┼────────────┼──────────┼────────────┼─────────────│
│ 3 │ V2099669   │ ❌740... │ 28-08-2025 │ 740087...   │
│   │ ✅ OK      │ ❌ERROR  │ ✅ OK      │ ❌DUPLICADO │
│   │            │ (3 dec)  │            │ EN BD       │
│ ──┼────────────┼──────────┼────────────┼─────────────│
│ 4 │ V1846480   │ 96       │ 03-09-2025 │ BNC/1304    │
│   │ ✅ OK      │ ✅ OK    │ ✅ OK      │ ✅ OK       │
│                                                       │
└──────────────────────────────────────────────────────┘

[⚠️ Enviar a Revisión de Pagos (2)]
```

### **Validación Mientras Escribe**

```
User edita monto: "740087406734393" → "9600"
    ↓
Validación INMEDIATA:
  - Cédula: ✅ OK
  - Monto: ¿3 decimales? ¿> límite? ¿< 0?
  - Fecha: ✅ OK
  - Documento: ¿duplicado en Excel? ¿en BD?
    ↓
Si TODOS cumplen:
  - Fila se vuelve GRIS TENUO
  - Sistema auto-guarda INMEDIATAMENTE
  - INSERT INTO pagos
  - INSERT INTO cuotas (reglas negocio)
  - Fila desaparece de tabla
  - Encabezado: Guardados +1, A Revisar -1
    ↓
Si NO cumple:
  - Celda rojo permanente
  - Tipo error visible: ❌ MONTO (3 decimales)
  - User debe corregir
```

### **Tipos de Error por Línea**

```
❌ CEDULA (si no es V/E/J/Z + 6-11 dígitos)
❌ MONTO (si <= 0, > límite, o 3+ decimales)
❌ FECHA (si < 01-07-2024, > hoy, o formato inválido)
❌ DOCUMENTO (si duplicado en Excel o BD)

Mostrado:
- En interfaz: color rojo + tipo error
- En Excel descargado: columna "Observaciones"
  Ejemplo: "MONTO: 3 decimales; DOCUMENTO: duplicado en BD (ID: 123)"
```

### **Fase 3: Guardado Automático**

```
Fila cumple validadores
    ↓
Sistema AUTOMÁTICAMENTE:
  1. INSERT INTO pagos (cedula, monto, fecha, documento)
  2. SET conciliado = 'SI'
  3. INSERT INTO cuotas (desglose según préstamo)
  4. Aplica reglas de negocio (descuentos, intereses, etc.)
    ↓
Fila desaparece de tabla
Encabezado actualiza: ✅ +1
```

### **Fase 4: No Cumple - Enviar a Revisión**

```
Fila NO cumple (usuario NO corrigió)
    ↓
Click [⚠️ Enviar a Revisión de Pagos]
    ↓
Sistema:
  1. INSERT INTO pagos_con_errores (con observaciones)
  2. Observaciones = "TIPO_ERROR: descripción"
    ↓
Fila desaparece de tabla
Encabezado actualiza: A Revisar -1
```

### **Fase 5: Módulo Revisar Pagos**

```
GET /pagos_con_errores
    ↓
Muestra filas con error
    ↓
Click [📥 Descargar Excel]
    ↓
Sistema genera Excel:
  - Cédula, Monto, Fecha, Documento
  - Observaciones (automáticas):
    "CEDULA: inválida; MONTO: 3 decimales; DOCUMENTO: duplicado en BD (ID: 456)"
    ↓
DELETE FROM pagos_con_errores (automático)
    ↓
User descarga, corrige offline, re-sube
    ↓
Mismo flujo: Preview Editable
```

---

## 🏗️ **COMPONENTES A CREAR**

### **1. TablaEditablePagos.tsx (NUEVO)**
```typescript
export function TablaEditablePagos({
  rows: Array<RowData>,
  onCellChange: (rowId, field, value) => void,
  onRowStateChange: (rowId, state) => void,
  validaciones: Record<rowId, Record<field, ValidationResult>>,
})

Features:
- Edición inline (click en celda)
- Validación mientras escribe
- Mostrar tipo de error por línea
- Auto-guardar si cumple
- Desaparecer fila tras guardar
```

### **2. Validadores Mejorados**
```typescript
// utils/pagoExcelValidation.ts - ACTUALIZAR

validarCedula(cedula)
  → tipo: 'CEDULA' si falla

validarMonto(monto)
  → tipo: 'MONTO' si falla
  → descripción: "3 decimales", "> límite", "< 0"

validarFecha(fecha)
  → tipo: 'FECHA' si falla
  → descripción: "menor a 01-07-2024", "mayor a hoy"

validarDocumento(doc, allDocs, bdDocs)
  → tipo: 'DOCUMENTO' si falla
  → descripción: "duplicado en Excel", "duplicado en BD (ID: 123)"
  → NUNCA permitir guardar duplicado
```

### **3. Hook Actualizado**
```typescript
// hooks/useExcelUploadPagos.ts

- validarCelda(field, value, rowId): ValidationResult
  - type: 'CEDULA' | 'MONTO' | 'FECHA' | 'DOCUMENTO' | null
  - isValid: boolean
  - message: string
  
- onCellChange(rowId, field, value)
  - Validar inmediatamente
  - Si cumple TODAS las columnas → AUTO-guardar
  - Actualizar encabezado

- guardarFilaAutomatico(rowId)
  - INSERT INTO pagos
  - SET conciliado = 'SI'
  - INSERT INTO cuotas (aplicar reglas)
  - Remover de tabla
  - Actualizar contador

- enviarARevision(rowIds)
  - INSERT INTO pagos_con_errores
  - Con observaciones generadas automáticamente
```

### **4. Columna Observaciones (Excel)**
```typescript
generarObservaciones(row, errores): string
  → Listar solo los campos con error
  → Ejemplo: "CEDULA: inválida; MONTO: 3 decimales"
```

---

## 📊 **ENCABEZADO DINÁMICO**

```typescript
const stats = {
  cargados: 20,           // del Excel original
  guardados: 18,          // ya en pagos + cuotas
  duplicados: 0,          // documentos duplicados
  aRevisar: 2,            // en pagos_con_errores
}

<div>
  Cargados: {cargados} | ✅ Guardados: {guardados} | 🔄 Duplicados: {duplicados} | ⚠️ A Revisar: {aRevisar}
</div>
```

**Actualización**: Tiempo real (mientras user edita)

---

## 🔐 **REGLA CRÍTICA: DOCUMENTO DUPLICADO**

```
❌ NUNCA PERMITIR GUARDAR DOCUMENTO DUPLICADO
✅ SIEMPRE DEBE SER DISTINTO

Validar contra:
  1. Documentos en el MISMO lote (Excel actual)
  2. Documentos en tabla pagos (BD)
  3. Documentos en pagos_con_errores (errores previos)

Si detecta duplicado:
  - Celda ROJO permanente
  - Tipo error: "DOCUMENTO: duplicado en BD (ID: 123)"
  - Bloquear guardar
  - User DEBE cambiar documento o descartar fila

Esto PROTEGE contra FRAUDE
```

---

## 🎬 **CASO DE USO: USER EDITA Y CUMPLE**

```
1. User abre Preview
   - Fila 3 tiene error: Monto = 740087406734393 (3 decimales)
   - Rojo: "MONTO: 3 decimales"

2. User edita celda Monto
   - Escribe: "9600"

3. Validación INMEDIATA:
   - Cédula: ✅ OK
   - Monto: ✅ OK (ahora 2 decimales)
   - Fecha: ✅ OK
   - Documento: ❌ Duplicado en BD (ID: 456)

4. User edita Documento
   - Escribe: "VE/999999"

5. Validación INMEDIATA:
   - Cédula: ✅ OK
   - Monto: ✅ OK
   - Fecha: ✅ OK
   - Documento: ✅ OK (no duplicado)

6. AUTOMÁTICAMENTE (sin click):
   - Fila se vuelve GRIS TENUO
   - Sistema guarda:
     - INSERT INTO pagos (fila 3)
     - SET conciliado = 'SI'
     - INSERT INTO cuotas
   - Fila DESAPARECE de tabla
   - Encabezado actualiza: Guardados 19, A Revisar 1
```

---

## ⏱️ **TIMELINE REALISTA**

- **Tabla editable**: 3-4h
- **Validadores con tipos de error**: 2-3h
- **Auto-guardar + Cuotas**: 2-3h
- **Descarga Excel + Observaciones**: 2h
- **Testing + Fixes**: 2-3h

**Total: 12-16 horas (puede ser 2 días de dev intenso)**

---

## 🚀 **IMPLEMENTACIÓN INICIADA**

Comenzando ahora con:
1. Tabla editable
2. Validadores mejorados
3. Auto-guardar
4. Integración cuotas

Preguntas de clarificación:
- ¿Trabajamos en paralelo con otra persona o solo yo?
- ¿Deadline para terminar?
- ¿Acceso a BD real o staging?
