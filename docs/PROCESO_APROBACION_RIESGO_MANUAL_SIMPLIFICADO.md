# Proceso simplificado: Aprobación de riesgo manual

**Objetivo:** Sustituir el flujo actual (Evaluación 7 criterios + Aplicar condiciones + Asignar fecha) por un **único paso manual**: el aprobador ingresa fechas, acepta una declaración de cumplimiento de políticas y riesgo, y el sistema guarda registrando quién aprobó.

---

## 1. Proceso simplificado propuesto

### Flujo en una sola pantalla

1. **Desde la lista de Préstamos:** para préstamos en estado **DRAFT** o **EN_REVISION**, el botón pasa a ser **"Aprobar préstamo"** (o **"Aprobar riesgo"**). Un solo clic abre el flujo (sin formulario de 7 criterios).

2. **Modal / pantalla "Aprobar préstamo (riesgo manual)":**
   - **Fecha de aprobación** (obligatoria): fecha en que se aprueba el préstamo.
   - **Fecha desde la cual se calcula la tabla de amortización** (obligatoria): fecha base para generar las cuotas (puede ser la misma que la de aprobación o la fecha del primer pago).
   - **Declaración:**  
     Texto fijo (o configurable) con checkbox obligatorio:
     > "Al aprobar, usted asegura que el cliente cumple las políticas de RapiCredit y que su riesgo está dentro de parámetros normales."
   - **Botón "Guardar y aprobar"** (habilitado solo si las dos fechas están completas y el checkbox está marcado).

3. **Al guardar (backend):**
   - Actualizar préstamo: `estado = 'APROBADO'` (o `'DESEMBOLSADO'` si se prefiere un solo estado final).
   - `fecha_aprobacion` = fecha de aprobación ingresada.
   - `fecha_base_calculo` = fecha para amortización.
   - `usuario_aprobador` = email (o id) del usuario actual (desde el token).
   - Generar tabla de amortización (cuotas) a partir de `fecha_base_calculo`, `numero_cuotas`, `total_financiamiento`, `modalidad_pago`.
   - Opcional: registrar en tabla de auditoría (módulo préstamos, acción "Aprobación manual", registro_id = prestamo_id, usuario, fecha).

4. **Qué se retira o se oculta:**
   - Formulario largo de **Evaluación de riesgo** (7 criterios).
   - Paso **"Aplicar condiciones de aprobación"** (tasa, plazo, etc.) como paso separado; si se desea, esos valores pueden quedar por defecto en el préstamo (ej. tasa/plazo ya cargados al crear).
   - Modal **"Asignar fecha de aprobación"** como flujo independiente; su lógica se integra en este único paso.

---

## 2. Preguntas para definir bien el proceso

1. **Estado final del préstamo**  
   Tras esta aprobación manual, ¿el préstamo debe quedar en **APROBADO** (y luego en otro momento alguien “desembolsa” y pasa a DESEMBOLSADO) o debe pasar **directamente a DESEMBOLSADO** (aprobación = listo para desembolso)?  
   - Si es **solo APROBADO:** se mantiene la posibilidad de un segundo paso “Desembolsar” más adelante.  
   - Si es **DESEMBOLSADO:** con este único paso el préstamo queda listo y con cuotas generadas.

2. **¿Una o dos fechas?**  
   Hoy pides:
   - Fecha de aprobación  
   - Fecha desde la cual se calcula la tabla de amortización  
   ¿Siempre serán distintas o a veces la misma?  
   - Si suelen ser la misma: se puede ofrecer **una sola fecha** “Fecha de aprobación y base para amortización” y rellenar ambas en backend.  
   - Si a menudo son distintas: mantener **dos campos** como planteas.

3. **Texto de la declaración**  
   ¿El texto debe ser **fijo** en frontend (“Usted aprueba por lo que asegura que el cliente cumple las políticas de RapiCredit y que su riesgo está dentro de parámetros normales”) o debe poder **configurarse** (ej. desde Configuración o BD) para cambiar el mensaje sin desplegar código?

4. **Quién puede aprobar**  
   ¿Solo **administradores** (como hoy la evaluación de riesgo) o también otros roles (ej. “operaciones”, “supervisor”)? Esto define si el botón y el endpoint siguen protegidos por rol admin o no.

5. **Datos del préstamo para la tabla de amortización**  
   La generación de cuotas usa: `numero_cuotas`, `total_financiamiento`, `modalidad_pago`, `fecha_base_calculo`. ¿Estos datos ya estarán siempre cargados al momento de aprobar (creación del préstamo) o puede haber casos en que el aprobador deba poder **editar** número de cuotas o monto en esta misma pantalla?  
   - Si no: el flujo solo pide fechas + declaración.  
   - Si sí: habría que añadir campos editables (número de cuotas, etc.) en el modal de aprobación.

6. **Historial / auditoría**  
   ¿Basta con guardar en el préstamo `usuario_aprobador` y `fecha_aprobacion` o se exige además **registro en tabla de auditoría** (quién aprobó, cuándo, desde qué IP, etc.)? Si ya usan una tabla de auditoría, conviene registrar ahí este evento.

---

## 3. Sugerencias

### Backend

- **Un solo endpoint**, por ejemplo:  
  `POST /api/v1/prestamos/{prestamo_id}/aprobar-manual`  
  Body:
  - `fecha_aprobacion` (date, obligatorio)
  - `fecha_base_calculo` (date, obligatorio) — o derivar de `fecha_aprobacion` si se elige una sola fecha
  - `acepta_declaracion` (boolean, obligatorio; el frontend solo envía true cuando el usuario marcó el checkbox)
- Lógica del endpoint:
  - Validar que el préstamo exista y esté en DRAFT o EN_REVISION.
  - Validar `acepta_declaracion === true`.
  - Obtener usuario actual (token) y guardar en `usuario_aprobador`.
  - Actualizar `fecha_aprobacion`, `fecha_base_calculo`, `estado` (APROBADO o DESEMBOLSADO según decisión de la pregunta 1).
  - Generar cuotas (reutilizar la lógica actual de generación de amortización).
  - Opcional: insertar en tabla de auditoría.
- **Deprecar o eliminar** (según lo que decidas):
  - `POST .../evaluar-riesgo`
  - `POST .../aplicar-condiciones-aprobacion`
  - `POST .../asignar-fecha-aprobacion`  
  O dejarlos solo para compatibilidad y que la nueva UI no los use.

### Frontend

- **Un solo componente/modal:** p. ej. `AprobarPrestamoManualModal` con:
  - Dos inputs tipo date (o uno si se unifican fechas).
  - Checkbox + texto de la declaración.
  - Botón “Guardar y aprobar” (deshabilitado hasta que fechas y checkbox estén válidos).
- En la **lista de préstamos**, para DRAFT y EN_REVISION:
  - Reemplazar el botón “Evaluar riesgo” (calculadora) por **“Aprobar préstamo”** que abre este modal.
  - Ocultar o eliminar el flujo que abre `EvaluacionRiesgoForm`, `FormularioAprobacionCondiciones` y `AsignarFechaAprobacionModal`.
- Mostrar en detalle del préstamo (o en lista) **quién aprobó** y **cuándo** (`usuario_aprobador`, `fecha_aprobacion`) para trazabilidad.

### Seguridad y trazabilidad

- Registrar siempre **usuario_aprobador** (email o id del usuario logueado).
- Si existe módulo de auditoría, registrar evento “Aprobación manual” con prestamo_id, usuario, fecha e IP si la tienen.
- El texto de la declaración deja claro que el aprobador asume la responsabilidad de que el cliente cumple políticas y riesgo dentro de parámetros.

---

## 4. Resumen del proceso simplificado sugerido

| Paso | Acción |
|------|--------|
| 1 | Usuario con permiso abre “Aprobar préstamo” desde la fila del préstamo (DRAFT o EN_REVISION). |
| 2 | Modal: ingresa **fecha de aprobación**, **fecha base para amortización**, marca **“Acepto que el cliente cumple políticas de RapiCredit y su riesgo está dentro de parámetros normales”**. |
| 3 | “Guardar y aprobar” → Backend actualiza préstamo (estado, fechas, usuario_aprobador), genera cuotas y opcionalmente registra en auditoría. |
| 4 | Se retira (o se oculta) el flujo de evaluación de riesgo por 7 criterios y los pasos separados de condiciones y asignación de fecha. |

Con las respuestas a las **preguntas** (estado final, una o dos fechas, texto fijo o configurable, roles, edición de cuotas/monto al aprobar, uso de auditoría), se puede bajar esto a cambios concretos en backend y frontend (endpoints, modelos y pantallas).
