# Auditoría integral: Formulario Nuevo Préstamo

**Componente:** `CrearPrestamoForm.tsx`  
**Ruta UI:** Préstamos → "Nuevo Préstamo"  
**Alcance:** Flujo de datos, validación, alineación backend, UX, accesibilidad y regla de datos reales.  
**Fecha:** 2025-02-05.

---

## 1. Resumen ejecutivo

El formulario **Nuevo Préstamo** organiza bien la búsqueda de cliente y los datos del préstamo (valor activo, anticipo 30%, total financiamiento calculado, modalidad, cuotas), usa datos reales de configuración (concesionarios, analistas, modelos desde la API) y valida obligatorios antes de enviar. La auditoría detecta **dos fallos críticos**: (1) el payload de creación **no incluye `cliente_id`**, que es obligatorio en el backend, por lo que la creación falla con 422; (2) el **Valor Activo** es solo lectura y se rellena desde `modelo.precio`, que la API de modelos devuelve siempre como `null`, dejando valor activo y total financiamiento en 0. Además se identifican mejoras en UX (confirmación de creación, encoding, logs) y coherencia con el backend.

---

## 2. Estructura del formulario (según UI)

| Sección | Campos | Origen datos |
|--------|--------|--------------|
| **Búsqueda de Cliente** | Modelo de Vehículo *, Cédula * | Modelos: `/api/v1/modelos-vehiculos/activos`. Cliente: búsqueda por cédula (debounce 500 ms). |
| **Datos del Préstamo** | Valor Activo (manual), Anticipo (30 %), Total Financiamiento (calculado), Modalidad de Pago *, Número de Cuotas *, Cuota por Período (calculado), Fecha de Requerimiento * | Cálculos locales; Concesionario / Analista desde API. |

\* Obligatorios en frontend.

---

## 3. Hallazgos críticos

### 3.1 Payload de creación sin `cliente_id`

- **Backend:** `POST /api/v1/prestamos` espera un body `PrestamoCreate`, que en `PrestamoBase` exige **`cliente_id: int`** (y opcionales como `total_financiamiento`, `estado`, `concesionario`, `modelo`, `analista`, etc.). El backend obtiene `cedula` y `nombres` del cliente a partir de `cliente_id` y no acepta `cedula` en el body para crear.
- **Frontend:** En `crearOActualizarPrestamo` se arma `prestamoData` desde `formData` (cedula, total_financiamiento, modalidad_pago, analista, concesionario, modelo_vehiculo, etc.) y se llama a `createPrestamo.mutateAsync(prestamoData)`. **En ningún punto se asigna `cliente_id`**. El cliente buscado por cédula está en `clienteData` (con `clienteData.id`), pero ese `id` no se envía.
- **Consecuencia:** La API responde **422 Unprocessable Entity** (validación Pydantic: falta `cliente_id`). El préstamo no se crea.
- **Recomendación:** Para creación (no edición), incluir en el payload `cliente_id: clienteData.id` y, si se desea mantener compatibilidad con el backend actual, no enviar `cedula` como campo de creación (el backend la rellena desde el cliente).

### 3.2 Valor Activo y “precio por modelo”

- **Backend:** En `modelos_vehiculos.py`, la lista de modelos se construye con `distinct Prestamo.modelo_vehiculo`. Cada ítem devuelve **`"precio": None`** (no existe tabla ni columna de precio por modelo).
- **Frontend:** El campo **Valor Activo (USD)** es `readOnly` y se actualiza solo cuando, al elegir un modelo, `modeloSel.precio != null`. Como la API siempre devuelve `precio: null`, `valorActivo` permanece en 0. El **Total de Financiamiento** se calcula como `valorActivo - anticipo`, por lo que también queda 0. El texto “Seleccione el modelo para cargar automáticamente el precio del activo” no se cumple.
- **Consecuencia:** El usuario no puede indicar un valor activo ni un total financiamiento > 0 desde la UI actual; la creación, si llegara a enviarse, sería con montos nulos/ceros.
- **Recomendación:** (a) Permitir introducir **Valor Activo** de forma manual (quitar `readOnly` y opcionalmente mantener auto-relleno cuando en el futuro la API exponga precio por modelo), o (b) que el backend exponga un precio por modelo (tabla/catálogo) y el frontend lo use para rellenar Valor Activo.

---

## 4. Validaciones y reglas de negocio

| Regla | Implementación | Observación |
|-------|----------------|-------------|
| Cédula obligatoria | Sí (submit) | OK. |
| Cliente existente y ACTIVO | Sí: `!clienteData` → error | OK. Búsqueda ya filtra por estado ACTIVO. |
| Valor Activo > 0 | Sí | OK; pero en la práctica siempre 0 por el punto 3.2. |
| Anticipo ≥ 30 % valor activo | Sí (submit + onBlur) | OK. |
| Número de cuotas 1–12 | Sí (input min/max + validación) | OK. Backend usa default 12 si no se envía. |
| Total financiamiento > 0 | Sí | OK. |
| Modalidad y fecha requerimiento | Sí | OK. |
| Concesionario y analista | Sí (obligatorios + `uiErrors`) | OK. |
| Modelo de vehículo | Sí | OK. |
| Préstamos existentes con mora | Modal de validación + justificación | Solo si `total_cuotas_mora > 0`. OK. |

---

## 5. Flujo de datos y API

- **Concesionarios / Analistas / Modelos:** Se obtienen con `useConcesionariosActivos`, `useAnalistasActivos`, `useModelosVehiculosActivos` (datos reales desde BD vía API). Coherente con la regla de datos reales.
- **Búsqueda de cliente:** `useSearchClientes(debouncedCedula)` → `clienteService.searchClientes` con filtro `estado: 'ACTIVO'`. Devuelve array de clientes; se usa el primero como `clienteData`. Correcto para “un cliente por cédula” en el flujo actual.
- **Creación:** `prestamoService.createPrestamo(prestamoData)` → `POST /api/v1/prestamos` con body que **no incluye `cliente_id`**. Incorrecto (ver 3.1).
- **Edición:** `updatePrestamo.mutateAsync({ id: prestamo.id, data })`. El backend espera `PrestamoUpdate` (todos los campos opcionales); no requiere `cliente_id` en cada PUT. El formulario no envía `cliente_id` en edición; si el backend lo permite, es consistente; si en el futuro se exige, habría que añadirlo.

---

## 6. UX y accesibilidad

- **Confirmación antes de crear:** Se usa `window.confirm(...)`. Funciona pero no es accesible (lectores de pantalla, teclado). Recomendación: sustituir por un modal (por ejemplo el mismo `Dialog` que en la lista de préstamos) con título, mensaje y botones “Cancelar” / “Continuar”.
- **Mensaje de confirmación:** Dice “no podrá editarlo después”; en la app sí existe flujo de edición para ciertos estados. Conviene alinear el texto con la política real (p. ej. “podrá editarlo solo en estado X” o “no podrá editarlo una vez aprobado/desembolsado”).
- **Campos deshabilitados:** Valor Activo con `disabled={isReadOnly || !formData.modelo_vehiculo}`: si no hay modelo, el usuario no puede escribir. Con precio siempre null, nunca puede completar valor activo sin permitir edición manual.
- **Scroll al error:** Tras validación se hace `formEl?.scrollIntoView({ behavior: 'smooth', block: 'start' })`. Útil; podría complementarse desplazando al primer campo con error.
- **Loading:** Se muestra “Buscando cliente...” mientras `isLoadingCliente`. OK.
- **Estados cliente:** Cliente encontrado (verde), no encontrado (rojo). OK.

---

## 7. Código y mantenimiento

- **Encoding:** En la concatenación de observaciones aparece **`PRÃ‰STAMO`** (debería ser “PRÉSTAMO”). En el bloque “Fecha de Desembolso” hay un carácter corrupto tipo emoji (**`ðŸ"…`**). Recomendación: guardar archivos en UTF-8 y sustituir por el texto/caracteres correctos.
- **Logs:** `console.warn` al cargar concesionarios/analistas/modelos; `console.error` al verificar préstamos existentes y al guardar. En producción es preferible usar un logger condicionado por entorno o eliminar warns innecesarios.
- **Botones Aprobar/Rechazar (edición):** Hay `// TODO: Implementar aprobación/rechazo` y `console.log(...)`. Esos botones no ejecutan ninguna acción útil; conviene implementar la llamada al backend (p. ej. evaluar riesgo / aprobar condiciones) o ocultarlos hasta que exista el flujo.

---

## 8. Seguridad

- No se detectan problemas de inyección en los campos enviados; el backend valida tipos y existencia de `cliente_id` (y en futuro de cliente). La creación está protegida por autenticación (Bearer) en el router de préstamos.
- La justificación para nuevo préstamo con mora se concatena en observaciones; asegurar que el backend no exponga esos textos de forma indebida (p. ej. en listados públicos).

---

## 9. Recomendaciones prioritarias

### Críticas (bloquean creación correcta)

1. **Incluir `cliente_id` en el payload de creación**  
   Al construir `prestamoData` para `!prestamo`, añadir `cliente_id: clienteData.id` (y asegurar que `clienteData` esté definido por las validaciones previas).

2. **Permitir introducir Valor Activo manualmente**  
   - Quitar `readOnly` del input Valor Activo y permitir `onChange` para que el usuario pueda escribir el monto (o mantener un valor por defecto cuando en el futuro la API envíe `precio` por modelo).  
   - Ajustar el texto de ayuda para no prometer “carga automática” del precio hasta que el backend lo soporte.

### Altas

3. Sustituir `window.confirm` de la creación por un **modal de confirmación** accesible (Dialog con título, mensaje y botones).
4. Corregir **encoding** en el archivo (PRÉSTAMO, título “Fecha de Desembolso”) y eliminar o condicionar **console.warn/error** en producción.
5. Revisar el mensaje “no podrá editarlo después” para que refleje la **política real de edición** del préstamo.

### Medias

6. Implementar o ocultar los **botones Aprobar/Rechazar** del bloque de edición (EN_REVISION) según exista o no el flujo en backend.
7. (Opcional) Cuando el backend exponga **precio por modelo**, mantener la carga automática de Valor Activo al seleccionar modelo y, si se desea, seguir permitiendo override manual.

---

## 10. Verificación rápida

- **Crear préstamo (sin correcciones):** Al enviar el formulario, la petición `POST /api/v1/prestamos` debería devolver **422** con detalle de validación indicando falta de `cliente_id`. Con Valor Activo en 0, aunque se añadiera `cliente_id`, el `total_financiamiento` sería 0.
- **Tras incluir `cliente_id` y permitir Valor Activo manual:** Crear un préstamo con cliente buscado por cédula, valor activo y anticipo válidos, y comprobar que la respuesta sea 201 y que el préstamo aparezca en el listado con los datos correctos.

---

## 11. Conclusión

El formulario **Nuevo Préstamo** tiene una estructura clara, usa datos reales para concesionarios, analistas y modelos, y valida bien en frontend; pero **la creación falla en backend** porque no se envía `cliente_id`, y **el Valor Activo no puede completarse** porque es solo lectura y el precio por modelo no existe en la API. Corregir el envío de `cliente_id` y permitir Valor Activo manual (o implementar precio por modelo en backend) desbloquea el flujo de alta de préstamos y alinea el formulario con la API y con la regla de datos reales.
