# Auditoría: por qué no se asigna automáticamente el número de crédito

**Fecha:** 2026-02-27  
**Alcance:** Flujo completo desde la carga del Excel hasta la asignación de `prestamo_id` por cédula (auto-asignación de crédito) en la carga masiva de pagos.

---

## 1. Resumen ejecutivo

La asignación automática de crédito solo ocurre cuando se cumplen **todas** estas condiciones:

1. La fila tiene una **cédula válida** (formato `[VEJZ]` + 6–11 dígitos o 8 dígitos solos normalizados a `V`+8).
2. Esa cédula está incluida en la petición **batch** al backend.
3. El backend devuelve **al menos un préstamo** para esa cédula.
4. Tras filtrar por estado, queda **exactamente un** préstamo **activo** (APROBADO o DESEMBOLSADO).
5. La fila no tiene ya un `prestamo_id` válido.
6. La **clave de lookup** (cedula normalizada) coincide con alguna clave del mapa `prestamosPorCedula` en el frontend.

Si falla cualquiera de estos pasos, el crédito no se asigna y el usuario debe elegirlo en el desplegable (o ver “Buscar crédito” si no hay datos para esa cédula).

---

## 2. Flujo técnico (cadena de datos)

### 2.1 Lectura del Excel (frontend)

| Paso | Archivo | Qué hace |
|------|---------|----------|
| Columnas | `useExcelUploadPagos.ts` ~L591–603 | Se detectan columnas por cabecera: `cedula` (cedula, cédula), `documento`, `prestamo`/`credito`, etc. |
| Cédula por fila | ~L610 | `cedula = String(row[cols.cedula]).trim()` — valor **tal cual** en la celda (puede venir como número en Excel). |
| Crédito por fila | ~L619–626 | Si la columna Crédito tiene valor numérico, se parsea; si es &lt; 1 o &gt; 2 147 483 647 se fuerza `prestamo_id = null` (evita usar número de documento como ID). |
| Cédulas únicas (en `processExcelFile`) | ~L662–673 | Para cada fila se obtienen `cedulaParaLookup(cedula)`, `cedulaParaLookup(numero_documento)` y `cedulaLookupParaFila(cedula, numero_documento)`. Solo se añaden a `uniqueCedulasSet` las que pasan `looksLikeCedula` (regex `[VEJZ]\d{6,11}`) y luego se normalizan sin guión. |

**Riesgo 1 – Cédula como número en Excel**  
Si la celda tiene solo dígitos (ej. `23107415`), el valor leído es `"23107415"`. Sin normalización no cumple `looksLikeCedula` y **no se incluiría** en la búsqueda batch.  
**Mitigación actual:** En `cedulaParaLookup` (`pagoExcelValidation.ts`) se normaliza **solo** cuando son **exactamente 8 dígitos** a `"V" + dígitos`. Cédulas de 9–11 dígitos sin letra no se normalizan y quedan fuera del batch.

**Riesgo 2 – Columna Crédito/Conciliación**  
Si la columna “Préstamo”/“Crédito” se interpreta como Conciliación (valores SI/NO/1/0), `isConciliacionCol4` es true y `prestamoId` se fuerza a `null`. No afecta a la asignación automática (que se hace por cédula), pero la columna no debe confundirse con Conciliación.

---

### 2.2 Normalización de cédula (frontend)

| Función | Archivo | Comportamiento |
|--------|---------|----------------|
| `cedulaParaLookup(val)` | `pagoExcelValidation.ts` ~L72–84 | Quita guiones y espacios; si cumple `[VEJZ]\d{6,11}` devuelve eso; si hay match parcial devuelve el trozo; **si son exactamente 8 dígitos** devuelve `"V" + dígitos`; si no, devuelve el string original. |
| `cedulaLookupParaFila(cedula, numero_documento)` | ~L90–97 | Usa `cedulaParaLookup` de cédula y de documento; prioriza cédula; devuelve el primero que cumpla `LOOKS_LIKE_CEDULA`. |
| `looksLikeCedula(c)` (hook) | `useExcelUploadPagos.ts` ~L84 | ` /^[VEJZ]\d{6,11}$/i.test((c||'').replace(/-/g,'').trim()) `. Solo estas cédulas entran en `cedulasUnicas` y en el batch. |

**Conclusión:** Cédulas con 9, 10 u 11 dígitos sin letra (ej. `123456789`) no se normalizan a `V`+dígitos y no se incluyen en el batch; para esas filas nunca habrá auto-asignación a menos que se amplíe la normalización (con cuidado de no confundir con números de documento).

---

### 2.3 Petición batch (frontend → backend)

| Paso | Archivo | Qué hace |
|------|---------|----------|
| Quién llama | `useExcelUploadPagos.ts` | 1) Dentro de `processExcelFile` (~L712–714) con `uniqueCedulas` del Excel recién leído. 2) En un `useEffect` (~L141–207) cuando `showPreview && cedulasUnicas.length > 0` (dependencia `cedulasUnicas.join(',')`). Pueden existir **dos** peticiones batch casi simultáneas. |
| Servicio | `prestamoService.ts` ~L107–124 | `getPrestamosByCedulasBatch(cedulas)`: normaliza con `trim` y `replace(/-/g,'')`, sin mayúsculas; envía `POST /api/v1/prestamos/cedula/batch` con `{ cedulas: cedulasNorm }`; espera `response.prestamos` como `Record<string, any[]>`; construye `result[ced] = prestamos[ced]` (claves = las mismas que se enviaron). |
| Claves | - | Las claves del mapa en frontend son las **mismas** que las enviadas (`cedulasNorm` / `cedulasUnicas`). El backend devuelve las claves tal cual las recibe (`cedulas_clean`). No hay normalización a mayúsculas en el envío, por lo que coincidencia depende de que frontend y backend usen el mismo formato (p. ej. `V23107415`). |

**Riesgo 3 – Doble batch**  
Dos orígenes (processExcelFile y useEffect) pueden disparar dos batches. Ambos actualizan `prestamosPorCedula` y `excelData` con la misma lógica; no se pierde asignación, pero es redundante y puede generar más carga.

---

### 2.4 Backend: endpoint batch

| Paso | Archivo | Qué hace |
|------|---------|----------|
| Entrada | `prestamos.py` ~L375–383 | `cedulas_clean = [(c or "").strip() for c in body.cedulas if (c or "").strip()]` (sin duplicados, orden preservado). Claves del resultado = `cedulas_clean`. |
| Normalización interna | ~L362–366 | `_normalizar_cedula_para_busqueda(c)`: `strip().upper().replace("-","").replace(" ","")`. Solo se usa para **matchear** filas de la BD con la cédula pedida; **no** para nombrar las claves del JSON. |
| Consulta | ~L400–406 | Préstamos con join a Cliente; filtro por `cedula` (exacta o normalizada) en Cliente y Prestamo. **No** se filtra por estado; se devuelven todos los préstamos que coincidan por cédula. |
| Agrupación | ~L421–435 | Para cada fila devuelta se toma `cedula_cliente` (o `p.cedula`), se normaliza y se asigna a `resultado[ced_clean]` si `ced_norm == cedula_norm` o `ced_clean == cedula_cli`. Las claves de `resultado` son exactamente las recibidas en `body.cedulas`. |
| Respuesta | ~L437 | `return {"prestamos": resultado}` — claves = cédulas tal cual enviadas (ej. `"V23107415"`). |

**Conclusión:** El backend no filtra por estado; el filtro “solo activos” es solo en frontend (APROBADO/DESEMBOLSADO). Si en BD el préstamo está en otro estado, el frontend lo descarta y puede quedar 0 activos → no hay auto-asignación.

---

### 2.5 Construcción del mapa y asignación (frontend)

| Paso | Archivo | Qué hace |
|------|---------|----------|
| Filtro por estado | `useExcelUploadPagos.ts` ~L154–156 (useEffect) y ~L698–701 (processExcelFile) | Solo se consideran préstamos con `(p.estado || '').toUpperCase()` en `ESTADOS_PRESTAMO_ACTIVO` = `['APROBADO','DESEMBOLSADO']`. |
| Claves del mapa | ~L158–163, ~L703–708 | Para cada cédula se guarda el array en: `map[cedula]`, `map[cedulaSinGuion]`, `map[cedula.toUpperCase()]`, `map[cedula.toLowerCase()]`. Así el lookup por fila puede usar cualquier variante. |
| Lookup por fila | ~L176–184 (useEffect), ~L723–731 (processExcelFile) | `cedulaLookup = cedulaLookupParaFila(r.cedula, r.numero_documento)`; se busca `map[cedulaLookup]`, `map[cedulaSinGuion]`, variantes upper/lower; si hay `cedulaColNorm` se prueba también; si hay una sola clave en el mapa (`fallbackKey`) se usa esa. |
| Condición de asignación | ~L184, ~L731 | `if (prestamos.length === 1 && prestamoIdVacio(r.prestamo_id)) return { ...r, prestamo_id: prestamos[0].id }`. |

**Riesgo 4 – Lookup vacío**  
Si `cedulaLookupParaFila` devuelve `""` (p. ej. cédula con 9 dígitos sin letra y documento sin cédula), no hay clave en el mapa y `prestamos` queda `[]` → no se asigna.

**Riesgo 5 – Más de un préstamo activo**  
Si la cédula tiene 2+ préstamos APROBADO/DESEMBOLSADO, `prestamos.length !== 1` y no se asigna automáticamente; el usuario debe elegir en el desplegable (comportamiento esperado).

---

### 2.6 Efecto de respaldo (segundo useEffect)

| Paso | Archivo | Qué hace |
|------|---------|----------|
| Trigger | ~L213–233 | Dependencias: `[showPreview, prestamosPorCedula, excelData.length]`. Cuando `prestamosPorCedula` se llena (p. ej. por el batch), vuelve a recorrer `excelData` y asigna `prestamo_id` cuando `prestamos.length === 1 && prestamoIdVacio(r.prestamo_id)`. |
| Cambio | ~L217 | `return changed ? next : prev` — solo actualiza si hubo algún cambio, para evitar ciclos. |

Si el primer flujo (useEffect del batch o processExcelFile) no asignó por alguna razón, este efecto puede corregirlo cuando `prestamosPorCedula` esté ya poblado. Depender de `excelData.length` (y no del contenido) está bien para no re-ejecutar por cambios de otro campo; el mapa se lee en cada ejecución.

---

### 2.7 UI: desplegable de crédito

| Paso | Archivo | Qué hace |
|------|---------|----------|
| Opciones | `ExcelUploaderPagosUI.tsx` ~L263–274 | `prestamosActivos` = lookup en `prestamosPorCedula` con `cedulaLookup`, `cedulaSinGuion`, upper/lower; si no hay, se prueba `cedulaColNorm` y, si solo hay una clave en el mapa, esa. `valorCredito = prestamoIdElegido ?? (prestamosActivos.length === 1 ? String(prestamosActivos[0].id) : 'none')`. |
| Sin créditos | ~L268–271, ~L338–347 | Si `prestamosActivos.length === 0` se muestra “Buscar crédito” (y loader si `cedulasBuscando.has(cedulaLookup)`). Si la cédula no está en el mapa, el usuario puede pulsar “Buscar” para `fetchSingleCedula`. |

Si el mapa no tiene esa cédula (por no haber entrado en el batch o por fallo de clave), la fila muestra “Buscar crédito” y no se auto-asigna.

---

## 3. Matriz de causas por las que no se asigna automáticamente

| # | Causa | Dónde | Comprobación / solución |
|---|--------|--------|-------------------------|
| 1 | Cédula en Excel sin letra y con 9–11 dígitos | `cedulaParaLookup` solo normaliza 8 dígitos a `V`+dígitos | Revisar valor en celda; ampliar normalización a 9–11 dígitos con cuidado (riesgo de confundir con documento). |
| 2 | Cédula vacía o no reconocible (espacios, formato raro) | Lectura Excel + `cedulaParaLookup` / `looksLikeCedula` | Asegurar columna Cédula con formato `V12345678` o al menos 8 dígitos; quitar espacios/guiones ya está en `cedulaParaLookup`. |
| 3 | La cédula no entra en `cedulasUnicas` | `looksLikeCedula` rechaza el valor | Solo pasan `[VEJZ]\d{6,11}` (y la normalización de 8 dígitos). Ver 1 y 2. |
| 4 | Backend no devuelve préstamos para esa cédula | BD: no hay préstamos con esa cédula (Cliente/Prestamo) | Comprobar en BD que exista préstamo con esa cédula; que coincida con la normalización del backend (sin guión, mayúsculas). |
| 5 | Préstamos devueltos no están APROBADO/DESEMBOLSADO | Filtro en frontend `ESTADOS_PRESTAMO_ACTIVO` | Si el único préstamo está PAGADO/CANCELADO/etc., se filtra y queda 0 activos → no se asigna. Revisar estado en BD. |
| 6 | Hay 2+ préstamos activos para la misma cédula | Lógica “solo si length === 1” | Comportamiento esperado: no auto-asignar; usuario debe elegir en el desplegable. |
| 7 | Clave de lookup no coincide con clave del mapa | `cedulaLookupParaFila` vs claves con las que se construye el mapa | El mapa se rellena con `cedula`, `cedulaSinGuion`, `toUpperCase()`, `toLowerCase()`. Lookup usa el mismo `cedulaLookup`. Si cedula viene normalizada (ej. `V23107415`) debería coincidir. Si en algún sitio se guardara con otra normalización, podría fallar. |
| 8 | Batch falla (red, 5xx, timeout) | `getPrestamosByCedulasBatch` | En catch se hace `setPrestamosPorCedula({})`; no hay reintento. Revisar red y logs del backend. |
| 9 | Respuesta del backend con formato distinto | `(response as any)?.prestamos` | Si el API devolviera otra estructura (ej. `data` en vez de `prestamos`), el mapa quedaría vacío. Verificar contrato del endpoint. |
| 10 | Fila ya tiene `prestamo_id` válido | `prestamoIdVacio(r.prestamo_id)` | No se sobrescribe; es intencionado. |

---

## 4. Recomendaciones

1. **Normalización de cédula (9–11 dígitos)**  
   Valorar en `cedulaParaLookup` tratar también 9 dígitos (y si aplica 10–11) como cédula venezolana con prefijo `V` cuando sea seguro (p. ej. solo si la columna se llama “Cédula” o “Cedula” y no “Documento”), para no confundir con referencias de pago.

2. **Un solo origen de batch**  
   Evitar doble petición: o bien asignar solo en `processExcelFile` cuando llegue el batch, o bien solo en el `useEffect`; no mantener ambos con la misma lógica en paralelo para simplificar y evitar posibles carreras.

3. **Logging de diagnóstico (solo desarrollo)**  
   Opcional: en desarrollo, loguear `cedulasUnicas`, las claves del mapa tras el batch, y por fila `cedulaLookup` y `prestamos.length`, para ver en qué paso se pierde la asignación.

4. **Estados considerados “activos”**  
   Si el negocio considera otros estados como “activos” para asignar pago, añadirlos a `ESTADOS_PRESTAMO_ACTIVO` en el frontend (y documentar).

5. **Mensaje cuando hay 0 créditos**  
   Ya existe aviso: “No hay créditos activos para [cédula]. Se guardará sin préstamo asociado.” Asegurar que el usuario vea que la causa puede ser estado del préstamo o cédula no encontrada.

---

## 5. Archivos implicados

| Área | Archivo |
|------|---------|
| Normalización cédula / lookup | `frontend/src/utils/pagoExcelValidation.ts` |
| Hook carga masiva | `frontend/src/hooks/useExcelUploadPagos.ts` |
| Servicio préstamos | `frontend/src/services/prestamoService.ts` |
| UI tabla / desplegable | `frontend/src/components/pagos/ExcelUploaderPagosUI.tsx` |
| API batch | `backend/app/api/v1/endpoints/prestamos.py` (listar_prestamos_por_cedulas_batch, _normalizar_cedula_para_busqueda) |

---

## 6. Checklist rápida para “no asigna crédito”

- [ ] Cédula en Excel: ¿tiene letra (V/E/J) o solo 8 dígitos? (9+ dígitos sin letra no se normalizan.)
- [ ] Columna Cédula: ¿sin espacios/guiones raros? ¿cabecera reconocida (cedula/cédula)?
- [ ] En BD: ¿existe préstamo con esa cédula (Cliente.cedula o Prestamo.cedula)?
- [ ] En BD: ¿estado del préstamo es APROBADO o DESEMBOLSADO?
- [ ] ¿Hay más de un préstamo activo para la misma cédula? (entonces debe elegir en el desplegable.)
- [ ] Red: ¿el POST a `/api/v1/prestamos/cedula/batch` responde 200 y `prestamos` con claves esperadas?
- [ ] En el navegador: ¿aparece “Buscar crédito” o el desplegable con opciones? (Si “Buscar crédito”, el mapa no tiene esa cédula o hay 0 activos.)

Con esta auditoría se cubre de forma integral por qué no se asigna automáticamente el número de crédito y qué revisar o ajustar en cada eslabón del flujo.
