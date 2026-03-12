# Auditoría integral: /pagos/configuracion?tab=plantillas

**URL auditada:** https://rapicredit.onrender.com/pagos/configuracion?tab=plantillas  
**Alcance:** Flujo completo frontend + backend que sirve la pestaña «Plantillas» dentro de Configuración.  
**Revisión:** Línea a línea de componentes, servicios, endpoints y modelos implicados.

---

## 1. Flujo de la URL y enrutado

| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `frontend/src/App.tsx` | 238 | Ruta `path="configuracion"` renderiza `<Configuracion />`. |
| `frontend/src/App.tsx` | 216-219 | Redirecciones: `notificaciones/plantillas` y `herramientas/plantillas` → `/configuracion?tab=plantillas`. |
| `frontend/src/pages/Configuracion.tsx` | 63-66 | `useEffect` sincroniza `seccionActiva` con `searchParams.get('tab')`. |
| `frontend/src/pages/Configuracion.tsx` | 32-51 | `tabToSeccion`: `tab=plantillas` → `seccionActiva = 'plantillas'`. |
| `frontend/src/pages/Configuracion.tsx` | 76-97 | `renderContenidoSeccion()`: `case 'plantillas': return <ConfigPlantillasTab />`. |
| `frontend/src/constants/configuracionSecciones.ts` | 51-52 | Sección `plantillas` en Herramientas, sin `href`; id `plantillas`. |

**Conclusión:** La URL `?tab=plantillas` activa correctamente la sección y muestra el contenido del tab Plantillas.

---

## 2. ConfigPlantillasTab y página Plantillas

| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `frontend/src/components/configuracion/tabs/ConfigPlantillasTab.tsx` | 1-5 | Solo reexporta: `return <Plantillas />`. Toda la lógica está en la página. |
| `frontend/src/pages/Plantillas.tsx` | 14-24 | Estado: `plantillaAEditar`, `resumenAbierto`, `activeTab`. Subtabs: `cuerpo-email`, `anexo-pdf`, `documentos-pdf`. |
| `Plantillas.tsx` | 25-40 | Sincronización de `activeTab` con query `subtab` (lectura y escritura con `setSearchParams`). |
| `Plantillas.tsx` | 46-86 | Cabecera: título, descripción, acordeón «Resumen de configuración», botón «Otras secciones de Configuración». |
| `Plantillas.tsx` | 88-124 | `<Tabs>` con 3 pestañas: Plantilla cuerpo email, Plantilla anexo PDF, Documentos PDF anexos. |

**Hallazgos:**

- **Accesibilidad:** El botón del acordeón tiene `aria-expanded={resumenAbierto}` (línea 57). Correcto.
- **Navegación:** «Otras secciones» hace `navigate('/configuracion')` sin preservar otro `tab`; si se entra por un deep link podría ser preferible mantener `?tab=...` según contexto.
- **Tipado:** `plantillaAEditar` está tipado como `any` (línea 17). Conviene usar `NotificacionPlantilla | null`.

---

## 3. Pestaña «Plantilla cuerpo email» – PlantillasNotificaciones

Componente: `frontend/src/components/notificaciones/PlantillasNotificaciones.tsx`.

### 3.1 Estado y datos

- Listado: `plantillas`, `plantillasFiltradas`, `loading`, `selected`, filtros `busqueda`, `filtroTipo`, `filtroActiva`.
- Formulario: `nombre`, `tipo`, `tiposSeleccionados`, `activa`, `asunto`, `encabezado`, `cuerpo`, `firma`, `variable`, `focus`, `variablesConfiguradas`, etc.
- Refs para inserción en cursor: `asuntoRef`, `encRef`, `cuerpoRef`, `firmaRef`.
- `cuerpoFinal`: `useMemo` que concatena encabezado + cuerpo + firma y aplica `replaceBase64ImagesWithLogoUrl`.

### 3.2 Carga y efectos

- `cargar()` llama a `notificacionService.listarPlantillas(undefined, false)` (todas, no solo activas) y actualiza lista y filtradas.
- `cargarVariables()` combina variables de API con variables precargadas generadas por `generarVariablesPrecargadas()`; si la API falla, usa solo precargadas.
- `useEffect` sin dependencia de `tabSeccionActiva` en el array pero que usa `tabSeccionActiva === 'plantillas'` para recargar variables: dependencia correcta en el array evita warnings y garantiza recarga al volver al tab.

### 3.3 Validación

- `validarObligatorias(tipo)`: define variables requeridas por tipo (incl. COBRANZA). En línea 424 hay `if (false) return ...`: la validación de variables obligatorias está **desactivada**. Las variables requeridas se calculan pero nunca se muestran como error. **Bug:** o se elimina el `if (false)` y se activa la validación, o se elimina el bloque si ya no se desea.

### 3.4 Guardar / actualizar

- Al editar (`selected?.id`): valida, actualiza una plantilla y opcionalmente crea copias para otros tipos en `tiposSeleccionados`. Si falla una de las copias, muestra toast de error pero no revierte la actualización principal.
- Al crear: crea una plantilla por cada tipo en `tiposSeleccionados`; nombres generados como `"${nombre} - ${label}"`.

### 3.5 UI y textos

- Líneas 641, 673, 681, 559, 562, 563: caracteres/emojis corruptos o placeholders (`?`, `?`, `đ?`, `â`, etc.) en títulos de categorías y en descripciones. **Bug de encoding:** revisar UTF-8 en origen y en bundler.
- Tabs internos: solo «Armar plantilla» y «Resumen» tienen `TabsTrigger` en el `TabsList` (líneas 609-616). Existe un `TabsContent value="html-editor"` (líneas 884-886) que renderiza `<EditorPlantillaHTML />` pero **no hay pestaña** que permita seleccionarlo. **Bug:** el editor HTML está inaccesible desde la UI actual (tab huérfano).

### 3.6 Seguridad / sanitización

- Contenido de asunto/cuerpo se envía al backend y se persiste; el backend sustituye variables al enviar. No se ve sanitización HTML en frontend; el riesgo de XSS se mitiga si el correo se muestra solo en clientes de correo que no ejecutan script. Valorar sanitización o lista blanca de etiquetas si el HTML se muestra en otra parte de la app.
- `handleImportFile`: `JSON.parse(text)` sin try/catch adicional (hay try general); mensaje de error genérico. Aceptable; podría mejorarse el mensaje para JSON inválido.

### 3.7 Vista previa

- `handleVistaPreviaHtml`: sustituye variables por datos de ejemplo y reemplaza el bloque `{{#CUOTAS.VENCIMIENTOS}}...{{/CUOTAS.VENCIMIENTOS}}` con HTML fijo; abre resultado en nueva ventana. Coherente con uso de plantillas tipo cobranza.

---

## 4. Pestaña «Plantilla anexo PDF» – PlantillaAnexoPdf

Componente: `frontend/src/components/notificaciones/PlantillaAnexoPdf.tsx`.

### 4.1 Estado y API

- Carga con `notificacionService.getPlantillaPdfCobranza()`; parsea `cuerpo_principal` usando `SEPARATOR = '{{ENCABEZADO_END}}'` para dividir encabezado y cuerpo.
- Guardado con `updatePlantillaPdfCobranza({ ciudad_default, cuerpo_principal, clausula_septima })`.

### 4.2 Variables del PDF

- Formato en backend y en `carta_cobranza_pdf.py`: `{monto_total_usd}`, `{num_cuotas}`, `{fechas_str}` (una llave). En el componente, `insertarVariable` usa `{${key}}`, coherente con ese formato.

### 4.3 Campo «Ciudad por defecto»

- **Bug:** `ciudadDefault` existe en estado (línea 32), se carga desde la API (línea 48) y se envía en `handleSave` (línea 131), pero **no hay ningún control en el JSX** (input/select) para que el usuario edite la ciudad. La plantilla PDF en backend usa `ciudad_default` (p. ej. en `carta_cobranza_pdf.py`). **Recomendación:** Añadir un campo «Ciudad por defecto» en el formulario de Plantilla anexo PDF.

### 4.4 Vista previa

- `getPlantillaPdfCobranzaPreview()` devuelve un blob PDF; se abre en nueva pestaña. Correcto.

---

## 5. Pestaña «Documentos PDF anexos» – DocumentosPdfAnexos

Componente: `frontend/src/components/notificaciones/DocumentosPdfAnexos.tsx`.

### 5.1 Flujo

- `getAdjuntosFijosCobranza()` devuelve `Record<string, AdjuntoItem[]>` (por caso: dias_5, dias_3, etc.).
- Subida: `uploadAdjuntoFijoCobranza(file, tipoCasoSeleccionado)` con validación de extensión `.pdf` y tipo.
- Eliminación: `deleteAdjuntoFijoCobranza(id)`.

### 5.2 Tipos de caso

- `TIPOS_CASO`: `dias_5`, `dias_3`, `dias_1`, `hoy`, `mora_90`. Debe coincidir con `TIPOS_CASO_VALIDOS` del backend (notificaciones.py ~617); coincide.

### 5.3 UX

- Botón eliminar con `aria-label={"Eliminar " + doc.nombre_archivo}`. Correcto para accesibilidad.
- Estado `eliminandoId` evita doble clic mientras se elimina.

---

## 6. Servicios (notificacionService)

Archivo: `frontend/src/services/notificacionService.ts`.

- **Plantillas:** `listarPlantillas`, `obtenerPlantilla`, `crearPlantilla`, `actualizarPlantilla`, `eliminarPlantilla`, `exportarPlantilla`, `enviarConPlantilla`. Rutas bajo `/api/v1/notificaciones/plantillas...`. Correcto.
- **PDF cobranza:** `getPlantillaPdfCobranza`, `updatePlantillaPdfCobranza`, `getPlantillaPdfCobranzaPreview`. Correcto.
- **Adjuntos fijos:** `getAdjuntosFijosCobranza` (lista por caso), `uploadAdjuntoFijoCobranza`, `deleteAdjuntoFijoCobranza`. Tipos de retorno coherentes con el uso en DocumentosPdfAnexos.
- **Variables:** `listarVariables(activa?)` usado en PlantillasNotificaciones para el banco de variables.

---

## 7. Backend – Endpoints y lógica

Archivo: `backend/app/api/v1/endpoints/notificaciones.py`.

### 7.1 Plantillas (tabla plantillas_notificacion)

- **GET /plantillas**: filtros `tipo`, `solo_activas`; devuelve lista serializada con `_plantilla_to_dict`. Uso de `db.get`/select; excepciones logueadas y HTTP 500.
- **GET /plantillas/{id}**, **POST /plantillas**, **PUT /plantillas/{id}**, **DELETE /plantillas/{id}**: CRUD estándar con validación de existencia y commit/rollback.
- **GET /plantillas/{id}/export**: mismo payload que GET por id.
- **POST /plantillas/{id}/enviar**: envía correo de prueba al cliente; usa `_sustituir_variables`; comprueba email válido y que el envío de notificaciones esté activo.

### 7.2 Plantilla PDF cobranza (configuracion)

- **GET /plantilla-pdf-cobranza**: lee clave `plantilla_pdf_cobranza`; JSON con `ciudad_default`, `cuerpo_principal`, `clausula_septima`.
- **PUT /plantilla-pdf-cobranza**: valida longitudes máximas (50_000 por campo); actualiza o crea fila en `configuracion`.
- **GET /plantilla-pdf-cobranza/preview**: genera PDF con contexto de ejemplo vía `generar_carta_cobranza_pdf`.

### 7.3 Adjuntos fijos por caso

- **GET /adjuntos-fijos-cobranza**: devuelve estructura por caso (dias_5, etc.).
- **POST /adjuntos-fijos-cobranza/upload**: valida `tipo_caso`, content-type y magic bytes PDF; guarda archivo y actualiza config; en error elimina el archivo creado.
- **DELETE /adjuntos-fijos-cobranza/{doc_id}**: elimina entrada y archivo en disco; comprueba path dentro de base_dir (evita path traversal).

### 7.4 Seguridad

- Router con `dependencies=[Depends(get_current_user)]`: todos los endpoints requieren autenticación.
- Límites de longitud en plantilla PDF y en adjunto fijo (nombre, ruta) y validación de path en nombre/ruta reducen riesgo de abuso.

### 7.5 Modelo PlantillaNotificacion

- `backend/app/models/plantilla_notificacion.py`: campos id, nombre, descripcion, tipo, asunto, cuerpo, variables_disponibles, activa, zona_horaria, fechas. Coherente con `_plantilla_to_dict` y con el tipo `NotificacionPlantilla` del frontend.

---

## 8. Utilidades

- **plantillaHtmlLogo.ts:** `replaceBase64ImagesWithLogoUrl` reemplaza `data:image/...` largos (≥400 caracteres) por `src="{{LOGO_URL}}"`. Uso consistente en PlantillasNotificaciones y EditorPlantillaHTML. Correcto.

---

## 9. Resumen de hallazgos

### Críticos / Bugs

1. **Validación de variables obligatorias desactivada** (`PlantillasNotificaciones.tsx` ~424): `if (false) return ...` hace que nunca se muestre error por variables obligatorias faltantes. Activar validación o eliminar código muerto.
2. **Campo «Ciudad por defecto» no editable en UI** (`PlantillaAnexoPdf.tsx`): Se guarda y se usa en backend, pero no hay input; el usuario no puede cambiarlo desde la pestaña Plantilla anexo PDF.
3. **Tab «Editor HTML» inaccesible** (`PlantillasNotificaciones.tsx`): Existe `TabsContent value="html-editor"` con `EditorPlantillaHTML` pero no hay `TabsTrigger` para ese valor; la pestaña no se puede seleccionar.

### Mejoras

4. **Encoding / textos:** Varios títulos y descripciones con caracteres corruptos (emojis/acentos) en `PlantillasNotificaciones.tsx`. Revisar codificación y fuentes.
5. **Tipado:** Sustituir `plantillaAEditar: any` por `NotificacionPlantilla | null` en `Plantillas.tsx`.
6. **Navegación:** Valorar mantener `?tab=...` al usar «Otras secciones de Configuración» cuando proceda.

### Positivos

- Enrutado y estado de la pestaña plantillas correctos.
- Uso de datos reales (API/BD) en listados y guardado; sin stubs en los flujos auditados.
- Backend con límites de tamaño, validación de PDF y path seguro en adjuntos.
- Autenticación requerida en todos los endpoints de plantillas.
- Accesibilidad parcial (aria-expanded, aria-label en acciones destructivas).
- Sincronización de subtab con query string en Plantillas.

---

## 10. Recomendaciones de acción (implementadas)

1. ✅ En `PlantillasNotificaciones.tsx`: se activó la validación de variables obligatorias (`if (faltantes.length > 0) return ...`).
2. ✅ En `PlantillaAnexoPdf.tsx`: se añadió un campo "Ciudad por defecto" (Input) enlazado a `ciudadDefault` y al guardado.
3. ✅ En `PlantillasNotificaciones.tsx`: se añadió `TabsTrigger value="html-editor"` ("Editor HTML") para hacer accesible el editor HTML.
4. ✅ Se corrigieron textos con caracteres corruptos (acentos, pestaña, Notificación, días, etc.) en `PlantillasNotificaciones.tsx`.
5. ✅ En `Plantillas.tsx`: se tipó `plantillaAEditar` como `NotificacionPlantilla | null` y se importó el tipo desde el servicio.
