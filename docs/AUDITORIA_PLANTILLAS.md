# Auditoría integral: Configuración Plantillas

**URL:** `/pagos/configuracion?tab=plantillas`  
**Fecha de auditoría:** 2025

## 1. Estructura actual

La página tiene **tres pestañas**:

| Pestaña | Contenido |
|--------|-----------|
| **Plantillas** | Plantilla email (asunto/cuerpo) con variables; banco por caso; armar/editar/export/import. |
| **PDF Cobranza** | (1) Anexo PDF con variables (carta cobranza), (2) Carga PDF fijo (ruta en servidor). |
| **Variables** | CRUD de variables personalizadas (tabla, campo BD, nombre_variable). |

Backend: `GET/PUT /plantilla-pdf-cobranza`, `GET/PUT /adjunto-fijo-cobranza`, CRUD plantillas y variables en `/notificaciones`.

---

## 2. Hallazgos y estado

### 2.1 Seguridad

| Hallazgo | Severidad | Estado |
|----------|-----------|--------|
| Ruta del adjunto fijo sin validación de longitud ni de path traversal en nombre | Media | **Corregido:** límites 255 (nombre) y 2048 (ruta); nombre no puede contener `/` ni `\`. |
| Ruta en servidor: solo el proceso que ejecuta la API puede leer el archivo; no se expone la ruta al cliente | Baja | Aceptable. |
| Endpoints bajo `get_current_user` | - | Correcto. |

### 2.2 UX / Errores

| Hallazgo | Severidad | Estado |
|----------|-----------|--------|
| Si falla la carga de PDF Cobranza o adjunto fijo, el usuario no ve feedback | Media | **Corregido:** toast de error al fallar la carga. |
| Resumen de configuración muy largo en móvil | Baja | Resumen en bloque colapsable o texto más corto; opcional. |
| Mezcla de librerías de toast (react-hot-toast en PlantillasNotificaciones, sonner en el resto) | Baja | Sin cambio; ambas funcionan. |

### 2.3 Accesibilidad

| Hallazgo | Severidad | Estado |
|----------|-----------|--------|
| Inputs en PDF Cobranza sin `id` / `htmlFor` asociado | Media | **Corregido:** labels con `htmlFor` e `id` en inputs; `aria-describedby` donde aplica. |
| Tabs con valor accesible (aria) | - | Componente Tabs de UI ya suele manejarlo. |

### 2.4 Consistencia y código

| Hallazgo | Severidad | Estado |
|----------|-----------|--------|
| Encoding corrupto "â†'" en textos de PlantillasNotificaciones | Baja | **Corregido:** "→". |
| Validación en backend de plantilla PDF (tamaño máximo de cuerpo/cláusula) | Baja | No implementado; límite por BD (TEXT). |

### 2.5 Funcionalidad

| Aspecto | Estado |
|---------|--------|
| Guardar plantilla email (crear/actualizar) | OK |
| Guardar plantilla PDF cobranza (ciudad, cuerpo, cláusula) | OK |
| Guardar adjunto fijo (nombre + ruta) | OK |
| Envío de correo cobranza con ambos adjuntos | OK (backend anexa carta + PDF fijo si existe). |
| Variables personalizadas usadas en plantillas | OK |

---

## 3. Mejoras implementadas en esta auditoría

1. **Backend – Adjunto fijo**
   - Límite de 255 caracteres para `nombre_archivo`.
   - Límite de 2048 caracteres para `ruta`.
   - Rechazo si el nombre contiene `/` o `\` (solo nombre de archivo).

2. **Frontend – PlantillaPdfCobranza**
   - Toast de error cuando falla la carga de configuración (PDF + adjunto fijo).
   - Labels asociados a inputs (`htmlFor`/`id`) y `aria-describedby` en cuerpo principal.

3. **Frontend – PlantillasNotificaciones**
   - Sustitución de "â†'" por "→" en los textos que mencionan "Notificaciones → Configuración".

---

## 4. Mejoras recomendadas (opcionales)

1. **Resumen de configuración (Plantillas.tsx)**  
   Hacer el resumen colapsable o acortar el texto en vista móvil para evitar scroll largo.

2. **Unificar toasts**  
   Migrar PlantillasNotificaciones (y ResumenPlantillas, GeneraVariables) a `sonner` para un solo sistema de notificaciones.

3. **Adjunto fijo: directorio base**  
   Implementado: variable de entorno `ADJUNTO_FIJO_COBRANZA_BASE_DIR`. Si está definida, la ruta en BD se resuelve dentro de ese directorio (solo rutas relativas, sin `..`).

4. **Vista previa del PDF de cobranza**  
   Implementado: `GET /plantilla-pdf-cobranza/preview` devuelve el PDF con datos de ejemplo; en la UI, botón "Vista previa (datos de ejemplo)" que abre el PDF en una nueva pestaña.

5. **Validación de existencia del archivo (adjunto fijo)**  
   Implementado: `GET /adjunto-fijo-cobranza/verificar` devuelve `{ existe, mensaje }`; en la UI, badge "Archivo encontrado" / "Archivo no encontrado" y botón "Comprobar ruta".

6. **Límites en plantilla PDF**  
   Implementado: en el PUT de `plantilla-pdf-cobranza`, cuerpo_principal y clausula_septima tienen un máximo de 50.000 caracteres cada uno; si se supera, se devuelve 400 con mensaje claro.

---

## 5. Resumen

- **Estructura:** Los tres apartados (plantilla email con variables, anexo PDF con variables, carga PDF fijo) están claros y operativos.
- **Seguridad:** Se añadieron validaciones y límites en el adjunto fijo.
- **UX y accesibilidad:** Se mejoró el feedback de error en carga y la asociación label/input en PDF Cobranza.
- **Código:** Se corrigió el carácter de encoding en textos de Notificaciones.

La configuración de plantillas queda auditada y con mejoras aplicadas en los puntos críticos; el resto son mejoras opcionales para siguientes iteraciones.
