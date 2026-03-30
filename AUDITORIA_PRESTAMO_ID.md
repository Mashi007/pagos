# Auditoría Integral: Auto-Llenar prestamo_id en Carga Masiva

## Problema Reportado

En https://rapicredit.onrender.com/pagos/pagos, la carga masiva **NO auto-llena el ID de préstamo** para todas las filas, incluso cuando hay un único crédito activo.

Imagen adjunta muestra:
- Filas con cédulas válidas pero SIN crédito auto-llenado (mostrando "Sin crédito")
- Filas con cédulas válidas CON crédito auto-llenado (2801, 3147)
- Filas con cédulas que NO existen en la BD (error rojo)

## Análisis del Flujo

### 1. **Ingreso de Datos (Excel)**

**Archivo:** `frontend/src/hooks/useExcelUploadPagos.ts` (línea ~1908-2440)

Proceso:
1. Se carga el Excel con cédulas en la columna "Cédula"
2. Se parsean los datos en `processExcelFile()`
3. Se **construyen cédulas únicas** (línea 266-289)

**PROBLEMA #1: Cédulas no se normalizan correctamente**

```typescript
// Línea 266-289
const cedulasUnicas = useMemo(() => {
  const candidates = new Set<string>()
  excelData.forEach(r => {
    const fromCedula = cedulaParaLookup(r.cedula)       // ← Usa LOOKS_LIKE_CEDULA solo VEJZ
    const fromDoc = cedulaParaLookup(r.numero_documento) // ← Usa LOOKS_LIKE_CEDULA solo VEJZ
    const lookup = cedulaLookupParaFila(r.cedula || '', r.numero_documento || '')
    
    ;[fromCedula, fromDoc, lookup].forEach(c => {
      if (c && c.length >= 5 && looksLikeCedula(c)) candidates.add(c)  // ← Aquí SÍ acepta números planos
    })
  })
  
  return [...candidates]
    .map(c => (c || '').trim().replace(/-/g, ''))
    .filter(c => c.length >= 5 && looksLikeCedula(c))  // ← Pero aquí lo filtra con números planos
}, [excelData])
```

**Inconsistencia detectada:**

1. **`cedulaParaLookup()`** (en `pagoExcelValidation.ts` línea 147-165):
   - Usa `LOOKS_LIKE_CEDULA = /^[VEJZ]\d{6,11}$/i` (SOLO VEJZ + dígitos)
   - Si recibe "123947215", devuelve como está (sin el prefijo V/E/J/Z)
   - Pero luego falla la validación porque no match con LOOKS_LIKE_CEDULA

2. **`looksLikeCedula()`** (en `useExcelUploadPagos.ts` línea 260-264):
   - Acepta: `[VEJZ]\d{6,11}` O `\d{6,11}` (números planos)
   - Mucho más permisivo

**Resultado:** Los números planos (123947215) pasan por `looksLikeCedula()` pero NO por `cedulaParaLookup()`, creando una inconsistencia.

---

### 2. **Búsqueda de Préstamos en Backend**

**Archivo:** `frontend/src/services/prestamoService.ts` (línea 414-450)

```typescript
async getPrestamosByCedulasBatch(cedulas: string[]): Promise<Record<string, Prestamo[]>> {
  const cedulasNorm = [
    ...new Set(
      (cedulas || [])
        .map(c => (c || '').trim().replace(/-/g, ''))
        .filter(c => c.length >= 5)
    ),
  ]
  
  // Se envía al backend: POST /api/v1/prestamos/cedula/batch
  const response = await apiClient.post<{ prestamos: Record<string, any[]> }>(
    `${this.baseUrl}/cedula/batch`,
    { cedulas: cedulasNorm },
    { timeout: 60000 }
  )
  
  const prestamos = (response as any)?.prestamos || {}
  // ...
}
```

**Pregunta crítica:** ¿El backend acepta números planos (123947215) o requiere prefijo (V123947215)?

**Flujo en backend para búsqueda:**
- Si recibe "123947215", ¿normaliza a "V123947215" automáticamente?
- ¿O requiere que el frontend envíe "V123947215"?

---

### 3. **Mapeo de Préstamos en Frontend**

**Archivo:** `frontend/src/hooks/useExcelUploadPagos.ts` (línea 385-418)

```typescript
prestamoService
  .getPrestamosByCedulasBatch(cedulasUnicas)
  .then(batch => {
    const map: Record<string, Array<{ id: number; estado: string }>> = {}
    
    cedulasUnicas.forEach(cedula => {
      const prestamos = (
        batch[cedula] ||                          // ← Busca con cédula tal como está
        batch[cedula.replace(/-/g, '')] ||       // ← O sin guiones
        []
      ).filter(...)
      
      map[cedula] = arr
      map[cedula.replace(/-/g, '')] = arr         // ← Agrega variación sin guiones
      map[cedula.toUpperCase()] = arr             // ← Agrega variación mayúscula
      map[cedula.toLowerCase()] = arr             // ← Agrega variación minúscula
    })
    
    return map
  })
```

**PROBLEMA #2: El mapa no contiene todas las variaciones**

Si el backend busca con "V123947215" pero el frontend envía "123947215":
- El mapa tendrá key: "123947215"
- El backend devuelve: key: "V123947215"
- **No coinciden** → Sin créditos encontrados

---

### 4. **Renderización en Tabla**

**Archivo:** `frontend/src/components/pagos/TablaEditablePagos.tsx` (línea 247-357)

```typescript
function CreditoCell({ row, prestamosPorCedula, onUpdateCell }) {
  const lookup = cedulaLookupParaFila(row.cedula || '', row.numero_documento || '')
  const sinGuion = lookup.replace(/-/g, '')
  
  const prestamos =
    prestamosPorCedula[lookup] ||
    prestamosPorCedula[sinGuion] ||
    prestamosPorCedula[lookup?.toUpperCase()] ||
    prestamosPorCedula[lookup?.toLowerCase()] ||
    []
  
  // Si no hay prestamos, muestra "Sin crédito"
  if (prestamos.length === 0) {
    return <span className="text-xs italic text-gray-500">Sin crédito</span>
  }
}
```

**PROBLEMA #3: Búsqueda en mapa con claves inconsistentes**

Si `cedulaLookupParaFila()` devuelve "V123947215" pero el mapa tiene "123947215", no encuentra nada.

---

## Root Causes Identificados

### Causa #1: Doble Validación de Cédulas Inconsistente

- `LOOKS_LIKE_CEDULA` en `pagoExcelValidation.ts` → VEJZ + dígitos
- `looksLikeCedula()` en `useExcelUploadPagos.ts` → VEJZ + dígitos O números planos

**Impacto:** Números planos se aceptan en `looksLikeCedula()` pero falla en `cedulaParaLookup()`.

### Causa #2: Backend envía respuestas con claves diferentes

Si el backend normaliza "123947215" → "V123947215" pero el frontend esperaba la clave original, no coinciden.

### Causa #3: Mapa de búsqueda no es exhaustivo

El mapa construido en línea 385-418 no cubre todas las variaciones posibles que podría devolver el backend.

---

## Soluciones Propuestas

### Solución 1: Uniformizar la validación de cédulas

**Opción A: Aceptar números planos en `cedulaParaLookup()`**

```typescript
// En pagoExcelValidation.ts, línea 145
// CAMBIAR de:
const LOOKS_LIKE_CEDULA = /^[VEJZ]\d{6,11}$/i

// A:
const LOOKS_LIKE_CEDULA = /^[VEJZ]\d{6,11}$/i
const LOOKS_LIKE_CEDULA_LOOSE = /^(\d{6,11}|[VEJZ]\d{6,11})$/i  // Incluye números planos

// Y actualizar cedulaParaLookup():
export function cedulaParaLookup(val: unknown): string {
  const sinGuion = s.replace(/-/g, '').replace(/\s+/g, '')
  
  if (LOOKS_LIKE_CEDULA.test(sinGuion)) return sinGuion
  
  // SI es número plano, añadir V automáticamente
  if (/^\d{8,11}$/.test(sinGuion) && !sinGuion.startsWith('V')) {
    return 'V' + sinGuion  // Normalizar a V+dígitos
  }
  
  return sinGuion
}
```

**Impacto:** Todas las cédulas se normalizan a "V+dígitos", asegurando consistencia.

### Solución 2: Aumentar cobertura del mapa de búsqueda

```typescript
// En useExcelUploadPagos.ts línea 385-418
// Después de construir el mapa, agregar más claves:

cedulasUnicas.forEach(cedula => {
  // ... lógica existente ...
  
  // AGREGAR: si la cédula es V+dígitos, también guardar sin V
  if (cedula.startsWith('V') || cedula.startsWith('v')) {
    const sinV = cedula.slice(1)
    map[sinV] = arr
  }
})
```

**Impacto:** El mapa será más forgiving con variaciones de entrada.

### Solución 3: Sincronizar normalizaciones en backend y frontend

**Validar con backend:**
- ¿Cómo normaliza el backend las cédulas?
- ¿Devuelve siempre "V+dígitos" o puede devolver "números planos"?
- ¿Requiere siempre "V+dígitos" o acepta "números planos"?

---

## Pasos Recomendados

1. **INMEDIATO:** Implementar Solución 1 (uniformizar validación)
2. **INMEDIATO:** Implementar Solución 2 (aumentar cobertura del mapa)
3. **VALIDATION:** Confirmar cómo el backend normaliza cédulas
4. **TEST:** Cargar Excel con números planos y verificar auto-llenar

---

## Archivos Afectados

- `frontend/src/utils/pagoExcelValidation.ts` (línea 145, función `cedulaParaLookup`)
- `frontend/src/hooks/useExcelUploadPagos.ts` (línea 260-264, función `looksLikeCedula`; línea 385-418, construcción del mapa)
- `frontend/src/components/pagos/TablaEditablePagos.tsx` (línea 247-357, búsqueda en mapa)

---

## Estado: EN INVESTIGACIÓN

Se requiere confirmación del comportamiento del backend antes de implementar soluciones.
