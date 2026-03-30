# Debugging: Auto-Llenar prestamo_id - Guía de Investigación

## Aclaración del Problema

**Lo que reportaste:**
- **Cédula:** `V2648006` (válida)
- **Documento:** `*2394725` (número de documento)
- **Crédito:** No se auto-llena (muestra "Sin crédito")

**Aclaración importante:** `123947215` es el DOCUMENTO, no la cédula. El sistema debe buscar por CÉDULA, no por documento.

---

## Posibles Causas Investigadas

### Causa A: La cédula NO se incluye en `cedulasUnicas`
- Si `V2648006` falla el filtro `looksLikeCedula()`, NO se buscaría en el backend
- Status: POCO PROBABLE (regex `/^[VEJZ]\d{6,11}$/i` debería aceptarla)

### Causa B: El backend NO devuelve préstamos para esa cédula
- El backend recibe `V2648006` pero no tiene préstamos activos para ella
- O el cliente no existe en la BD
- Status: POSIBLE (backend issue)

### Causa C: El mapa NO se llena correctamente
- El mapa se construye pero NO contiene la clave `V2648006`
- Status: POSIBLE (lógica de mapa)

### Causa D: El mapa se llena pero búsqueda NO encuentra la clave
- El mapa tiene `V2648006` pero `cedulaLookupParaFila()` devuelve algo diferente
- Status: POSIBLE (función lookup)

---

## Cómo Debuggear (Browser Console)

He agregado **logging automático** a la aplicación. Sigue estos pasos:

### Paso 1: Abrir Console del Navegador
1. Ve a https://rapicredit.onrender.com/pagos/pagos
2. Presiona **F12** o **Ctrl+Shift+I**
3. Selecciona la pestaña **Console**

### Paso 2: Cargar Excel con tu Data

Carga un archivo Excel que contenga:
- Cédula: `V2648006`
- Documento: `*2394725`
- Otros datos: banco, fecha, monto, etc.

### Paso 3: Revisar Logs - PASO A PASO

#### Log 1: Cédulas siendo buscadas
```
[ExcelUpload] Cédulas únicas para búsqueda: ['V2648006', ...]
```

**Si ves esto:** ✅ La cédula se incluyó correctamente
**Si NO ves esto:** ❌ La cédula fue rechazada por el filtro

---

#### Log 2: Respuesta del backend
```
[ExcelUpload] Cédula V2648006: 2 préstamo(s) encontrado(s)
[ExcelUpload] Cédula V2648006: 0 préstamo(s) encontrado(s)
```

**Si dice "2 préstamos":** ✅ Backend encontró créditos activos
**Si dice "0 préstamos":** ❌ Backend NO encontró créditos activos

---

#### Log 3: Claves en el mapa
```
[ExcelUpload] Mapa construido con claves: ['V2648006', 'v2648006', '2648006', ...]
```

**Si ves V2648006:** ✅ Mapa se llenó correctamente
**Si NO ves V2648006:** ❌ Mapa no se llenó

---

#### Log 4: Búsqueda en tabla
```
[TablaEditable] No encontrado para cédula "V2648006". Claves en mapa: ['V1234567', 'V8901234', ...]
```

**Si ves esto:** ❌ Cédula NO está en mapa (Causa A, B, o C)
**Si NO ves esto:** ✅ Cédula está en mapa y se auto-llena

---

## Árbol de Diagnóstico

```
¿Aparece Log 1 (Cédulas únicas)?
├─ NO → Error en construcción de cedulasUnicas
│  └─ Revisar: looksLikeCedula() filtro muy estricto
│
└─ SÍ ¿Aparece Log 2 (Respuesta backend)?
   ├─ "0 préstamos" → Backend no tiene créditos para esa cédula
   │  └─ Posible: Cliente sin créditos activos, o BD issue
   │
   └─ "N préstamos" ¿Aparece Log 3 (Mapa)?
      ├─ NO V2648006 → Mapa no se llenó correctamente
      │  └─ Revisar: Lógica de buildMap()
      │
      └─ SÍ V2648006 ¿Aparece Log 4?
         ├─ SÍ → Cédula NO encontrada en búsqueda de tabla
         │  └─ Revisar: cedulaLookupParaFila() devuelve formato diferente
         │
         └─ NO → Auto-llenar funciona (sin log = OK)
```

---

## Acciones Según Resultado

### Escenario 1: "0 préstamos encontrados"
**Causa:** Backend no devuelve créditos activos

**Solución:**
1. Verificar en BD: `SELECT * FROM prestamos WHERE cedula LIKE '%2648006%' AND estado IN ('APROBADO', 'DESEMBOLSADO')`
2. Si hay resultados: Backend issue (filtro de estado)
3. Si NO hay: Cliente realmente no tiene créditos activos

### Escenario 2: "Cédula NO encontrada" en Log 4
**Causa:** Mapa tiene clave diferente

**Posible:**
- Mapa tiene `V2648006` pero búsqueda usa `2648006`
- Mapa tiene `v2648006` pero búsqueda usa `V2648006`

**Solución:**
- Ver claves en Log 3
- Ver qué devuelve `cedulaLookupParaFila()` comparando con Log 3

### Escenario 3: NO aparece ningún log
**Causa:** Excel nunca se procesa

**Solución:**
1. Verificar que el archivo esté en formato correcto
2. Asegurarse de que tiene al menos 1 fila de datos + 1 de encabezados
3. Revisar pestaña Network para ver si hay errores en upload

---

## Información a Proporcionar

Una vez que ejecutes los pasos, comparte:

```
1. ¿Qué logs aparecen en Console?
2. ¿Qué valores exactos ves?
3. ¿En qué fila del árbol de diagnóstico te detiene?
4. La cédula V2648006: ¿Tiene créditos activos?
5. ¿Qué valores devuelve cedulaLookupParaFila() vs qué claves hay en mapa?
```

---

## Código de Debugging Agregado

He añadido 3 puntos de logging:

1. **`useExcelUploadPagos.ts` línea 289:** Log de cédulas únicas
2. **`useExcelUploadPagos.ts` línea 409:** Log de respuesta backend por cédula + mapa
3. **`TablaEditablePagos.tsx` línea 548:** Log de búsqueda fallida en mapa

Estos logs son **temporales** y se removerán cuando se confirme la causa.

---

## Commit

Commit con logging: `9eb28ad5`

Para remover logs después: Revertir este commit o eliminarlos manualmente.

---

**Próximo paso:** Proporciona los logs que ves en la console y seguimos investigando.
